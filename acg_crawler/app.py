"""ACG资源聚合爬取工具 - 主程序"""
import json
import os
import threading
import requests as req_lib
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, Response

from config import load_config
from database import init_db, get_posts, get_post_count, delete_post, get_tasks, delete_task, get_conn, get_crawl_batches, get_posts_by_crawl_id, get_batch_post_count, recover_interrupted_tasks
from crawler import CrawlerEngine
from generator import export_posts

app = Flask(__name__)
config = load_config()
init_db()
recovered_tasks = recover_interrupted_tasks()

IMAGES_DIR = Path(__file__).parent / "images"

engine = CrawlerEngine(config)

# 日志和进度存储
log_store = {"logs": []}
progress_store = {"current": 0, "total": 0, "success": 0, "skipped": 0, "error": 0}

def log_callback(site, msg, level="info"):
    import time
    timestamp = time.strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] [{site}] {msg}"
    log_store["logs"].append({"text": log_entry, "level": level})
    if len(log_store["logs"]) > 500:
        log_store["logs"] = log_store["logs"][-300:]

def progress_callback(current, total, success, skipped, error):
    progress_store["current"] = current
    progress_store["total"] = total
    progress_store["success"] = success
    progress_store["skipped"] = skipped
    progress_store["error"] = error

engine.log_callback = log_callback
engine.progress_callback = progress_callback

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/images/<path:subpath>")
def serve_image(subpath):
    """提供本地下载的图片：/images/{post_id}/{filename}"""
    import re as _re
    # 安全校验：只允许数字目录名和合法文件名
    if ".." in subpath or not _re.fullmatch(r"[A-Za-z0-9_\-]+/[A-Za-z0-9_\-]+\.\w+", subpath):
        return "", 400
    img_path = IMAGES_DIR / subpath
    if img_path.exists():
        resp = send_file(str(img_path))
        resp.headers["Cache-Control"] = "public, max-age=86400"
        return resp
    return "", 404

import ipaddress
import socket
from urllib.parse import urlparse

@app.route("/api/proxy_image")
def api_proxy_image():
    """图片代理：服务端下载图片后转发给浏览器，解决防盗链问题（含SSRF防护）"""
    url = request.args.get("url", "")
    if not url:
        return "", 400

    # SSRF防护：只允许http/https，拒绝环回/私有/保留地址
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return "", 400
        hostname = parsed.hostname
        if not hostname:
            return "", 400
        addr_infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
        for addr_info in addr_infos:
            ip = ipaddress.ip_address(addr_info[4][0])
            if (ip.is_loopback or ip.is_private or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                return "", 400
    except (ValueError, socket.gaierror):
        return "", 400

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    }
    proxy = None
    if config.get("proxy", {}).get("enabled"):
        proxy = config["proxy"]["http"]

    # 尝试方式1: 通过代理
    if proxy:
        try:
            proxies = {"http": proxy, "https": proxy}
            resp = req_lib.get(url, headers={**headers, "Referer": url},
                               proxies=proxies, timeout=15, stream=True, verify=False)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            return Response(resp.iter_content(8192), content_type=content_type)
        except Exception:
            pass

    # 尝试方式2: 直连（无代理）
    try:
        resp = req_lib.get(url, headers=headers, timeout=15, stream=True, verify=False)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "image/jpeg")
        return Response(resp.iter_content(8192), content_type=content_type)
    except Exception:
        return "", 404

@app.route("/api/posts")
def api_posts():
    platform = request.args.get("platform", "all")
    source = request.args.get("source", "all")
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    posts = get_posts(platform=platform, source=source, limit=limit, offset=offset)
    total = get_post_count(platform=platform, source=source)
    return jsonify({"posts": posts, "total": total})

@app.route("/api/posts_grouped")
def api_posts_grouped():
    """按爬取时间分组返回帖子"""
    platform = request.args.get("platform", "all")
    source = request.args.get("source", "all")
    with get_conn() as conn:
        query = "SELECT *, strftime('%Y-%m-%d %H:%M', crawled_at) as crawl_date FROM posts WHERE 1=1"
        params = []
        if platform and platform != "all":
            if platform == "pc":
                query += " AND (platform = 'pc' OR platform = 'unknown')"
            elif platform == "pc_android":
                # pc_android包含原来的android
                query += " AND (platform = 'pc_android' OR platform = 'android')"
        if source and source != "all":
            query += " AND source = ?"
            params.append(source)
        query += """ ORDER BY
            (CASE WHEN baidu_link IS NOT NULL AND mobile_link IS NOT NULL THEN 0 ELSE 1 END),
            likes DESC"""
        rows = conn.execute(query, params).fetchall()

        # 按平台分组（只分PC/PC+安卓，安卓归入PC+安卓）
        groups = {}
        for row in rows:
            d = dict(row)
            platform = d.get("platform", "unknown")
            # android全部归入PC+安卓
            if platform == "android":
                platform = "pc_android"
            plat_label = {"pc": "PC", "pc_android": "PC+安卓"}.get(platform, "其他")
            if plat_label not in groups:
                groups[plat_label] = {"label": plat_label, "platform": plat_label, "posts": [], "total": 0}
            groups[plat_label]["posts"].append(d)
            groups[plat_label]["total"] += 1

        plat_order = {"PC": 0, "PC+安卓": 1, "其他": 3}
        final = sorted(groups.values(), key=lambda g: plat_order.get(g["platform"], 9))
        return jsonify({"groups": final})

@app.route("/api/start_crawl", methods=["POST"])
def api_start_crawl():
    if engine.running:
        return jsonify({"status": "error", "message": "已有任务在运行"})

    data = request.json
    mode = data.get("mode", "by_page")
    sites = data.get("sites", ["acgyxj", "acgrx", "acgll", "acgjlb"])
    speed_name = data.get("speed", "balanced")

    # 速度档位白名单校验
    actual_speed = engine.set_speed(speed_name)

    log_store["logs"] = []
    progress_store.update({"current": 0, "total": 0, "success": 0, "skipped": 0, "error": 0})

    def run():
        if mode == "by_page":
            start_page = data.get("start_page", 1)
            end_page = data.get("end_page", 10)
            engine.crawl_by_page(sites, start_page, end_page, speed_name=actual_speed)
        elif mode == "by_date":
            start_date = data.get("start_date", "")
            end_date = data.get("end_date", "")
            engine.crawl_by_date(sites, start_date, end_date, speed_name=actual_speed)
        elif mode == "incremental":
            engine.crawl_incremental(sites, speed_name=actual_speed)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return jsonify({"status": "ok", "speed": actual_speed})

@app.route("/api/stop_crawl", methods=["POST"])
def api_stop_crawl():
    engine.cancel()
    return jsonify({"status": "ok"})

@app.route("/api/progress")
def api_progress():
    # 站点独立状态（四站窗口）
    site_states = {}
    with engine._lock:
        for site_key, state in engine.site_states.items():
            site_states[site_key] = dict(state)
    # 每站最近日志：把站点名键转回site_key，与前端面板对齐
    name_to_key = engine._get_name_to_key()
    site_logs = {}
    with engine._lock:
        for site_key, logs in engine.site_logs.items():
            normalized_key = name_to_key.get(site_key, site_key)
            if normalized_key not in site_logs:
                site_logs[normalized_key] = []
            site_logs[normalized_key].extend(logs[-20:])
    return jsonify({
        "running": engine.running,
        "speed": engine.speed_name,
        **progress_store,
        "site_states": site_states,
        "site_logs": site_logs,
        "recent_logs": log_store["logs"][-50:],
    })

@app.route("/api/tasks")
def api_tasks():
    tasks = get_tasks()
    status_label = {
        "completed": "完成",
        "running": "运行中",
        "cancelled": "已取消",
        "failed": "失败",
        "interrupted": "已中断",
        "pending": "等待中",
    }
    for task in tasks:
        if task.get("status") in status_label:
            task["status_label"] = status_label[task["status"]]
        else:
            task["status_label"] = task.get("status", "")
    return jsonify(tasks)

@app.route("/api/delete_post", methods=["POST"])
def api_delete_post():
    data = request.json
    post_id = data.get("id")
    if post_id:
        delete_post(post_id)
    return jsonify({"status": "ok"})

@app.route("/api/delete_task", methods=["POST"])
def api_delete_task():
    data = request.json
    task_id = data.get("id")
    if task_id:
        delete_task(task_id)
    return jsonify({"status": "ok"})

@app.route("/api/batch_delete", methods=["POST"])
def api_batch_delete():
    data = request.json
    ids = data.get("ids", [])
    if ids:
        with get_conn() as conn:
            placeholders = ",".join("?" * len(ids))
            conn.execute(f"DELETE FROM posts WHERE id IN ({placeholders})", ids)
    return jsonify({"status": "ok"})

@app.route("/api/redownload_images", methods=["POST"])
def api_redownload_images():
    """批量重新下载图片：将远程URL转换为本地路径"""
    import json as _json
    from parser.image_handler import download_images
    from database import get_conn

    def run():
        with get_conn() as conn:
            rows = conn.execute("SELECT id, source_id, images FROM posts").fetchall()
            total = len(rows)
            updated = 0
            for i, row in enumerate(rows):
                post_id = row["id"]
                source_id = row["source_id"]
                images_str = row["images"] or "[]"
                try:
                    images = _json.loads(images_str)
                except:
                    images = []

                if not images:
                    continue

                # 检查是否需要重新下载
                needs_download = any(img.startswith("http") for img in images)
                if not needs_download:
                    continue

                # 获取代理配置
                proxy = None
                if config.get("proxy", {}).get("enabled"):
                    proxy = config["proxy"]["http"]

                local_images = download_images(images, source_id, proxy=proxy)
                if local_images and any(img.startswith("images/") for img in local_images):
                    new_images = _json.dumps(local_images)
                    conn.execute("UPDATE posts SET images = ? WHERE id = ?", (new_images, post_id))
                    updated += 1

                if (i + 1) % 50 == 0:
                    engine._log("系统", f"重新下载进度: {i+1}/{total}, 已更新: {updated}")

            conn.commit()
            engine._log("系统", f"重新下载完成: 共 {total} 条, 更新 {updated} 条")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return jsonify({"status": "ok"})

@app.route("/api/export")
def api_export():
    posts = get_posts(limit=10000)
    result = export_posts(posts)
    return jsonify({"status": "ok", "files": result})

@app.route("/api/export_counts")
def api_export_counts():
    """返回各平台导出数量"""
    pc = get_post_count(platform="pc")
    mixed = get_post_count(platform="pc_android") + get_post_count(platform="android")
    return jsonify({"pc": pc, "mixed": mixed})

@app.route("/api/crawl_batches")
def api_crawl_batches():
    """获取所有爬取批次"""
    batches = get_crawl_batches()
    return jsonify({"batches": batches})

@app.route("/api/export_batch")
def api_export_batch():
    """按批次导出"""
    crawl_id = request.args.get("crawl_id", type=int)
    platform = request.args.get("platform", "all")
    
    if not crawl_id:
        return jsonify({"status": "error", "message": "缺少crawl_id"})
    
    posts = get_posts_by_crawl_id(crawl_id, platform)
    if not posts:
        return jsonify({"status": "error", "message": "该批次无数据"})
    
    result = export_posts(posts)
    
    # 根据平台选择文件
    if platform == "pc":
        filepath = result.get("pc", "")
    elif platform == "pc_android":
        filepath = result.get("mixed", "")
    else:
        filepath = result.get("mixed", "")
    
    if filepath:
        import os
        filename = os.path.basename(filepath)
        return send_file(filepath, as_attachment=True, download_name=filename)
    
    return jsonify({"status": "error", "message": "导出失败"})

@app.route("/api/export_download")
def api_export_download():
    export_type = request.args.get("type", "all")
    selected_ids = request.args.get("ids", "")

    if export_type == "selected" and selected_ids:
        id_list = [int(i) for i in selected_ids.split(",") if i.strip()]
        with get_conn() as conn:
            placeholders = ",".join("?" * len(id_list))
            rows = conn.execute(
                f"SELECT * FROM posts WHERE id IN ({placeholders}) ORDER BY id",
                id_list
            ).fetchall()
            posts = [dict(row) for row in rows]
    else:
        if export_type == "pc":
            posts = get_posts(platform="pc", limit=10000)
        elif export_type == "mixed":
            # android全部归入pc_android
            posts = get_posts(platform="pc_android", limit=10000)
            posts += get_posts(platform="android", limit=10000)
        else:
            posts = get_posts(limit=10000)

    result = export_posts(posts)

    if export_type == "pc":
        filepath = result.get("pc", "")
    elif export_type == "mixed":
        filepath = result.get("mixed", "")
    else:
        filepath = result.get("mixed", "")

    if filepath:
        import os
        filename = os.path.basename(filepath)
        return send_file(filepath, as_attachment=True, download_name=filename)

    return jsonify({"status": "error", "message": "无数据可导出"})

if __name__ == "__main__":
    flask_config = config.get("flask", {})
    app.run(
        host=flask_config.get("host", "127.0.0.1"),
        port=flask_config.get("port", 5000),
        debug=flask_config.get("debug", False),
        use_reloader=flask_config.get("debug", False),
    )

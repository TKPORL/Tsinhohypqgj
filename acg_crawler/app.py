"""ACG资源聚合爬取工具 - 主程序"""
import json
import os
import threading
import requests as req_lib
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, Response

from config import load_config
from database import init_db, get_posts, get_post_count, delete_post, get_tasks, delete_task, get_conn
from crawler import CrawlerEngine
from generator import export_posts

app = Flask(__name__)
config = load_config()
init_db()

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

@app.route("/images/<path:source>/<path:filename>")
def serve_image(source, filename):
    """提供本地下载的图片（兼容hash目录和旧中文目录）"""
    img_path = IMAGES_DIR / source / filename
    if img_path.exists():
        return send_file(str(img_path))
    # 兼容旧路径：遍历images下所有子目录查找
    for d in IMAGES_DIR.iterdir():
        if d.is_dir():
            candidate = d / filename
            if candidate.exists():
                return send_file(str(candidate))
    return "", 404

@app.route("/api/proxy_image")
def api_proxy_image():
    """图片代理：服务端下载图片后转发给浏览器，解决防盗链问题"""
    url = request.args.get("url", "")
    if not url:
        return "", 400
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": url,
        }
        proxy = None
        if config.get("proxy", {}).get("enabled"):
            proxy = config["proxy"]["http"]
        proxies = {"http": proxy, "https": proxy} if proxy else None
        resp = req_lib.get(url, headers=headers, proxies=proxies, timeout=15, stream=True)
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
        query = "SELECT *, DATE(crawled_at) as crawl_date FROM posts WHERE 1=1"
        params = []
        if platform and platform != "all":
            if platform == "pc":
                query += " AND (platform = 'pc' OR platform = 'unknown')"
            elif platform == "pc_android":
                query += " AND platform = 'pc_android'"
            elif platform == "android":
                query += " AND platform = 'android'"
        if source and source != "all":
            query += " AND source = ?"
            params.append(source)
        query += """ ORDER BY
            (CASE WHEN baidu_link IS NOT NULL AND mobile_link IS NOT NULL THEN 0 ELSE 1 END),
            (CASE source
                WHEN 'ACG游戏姬' THEN 1
                WHEN 'ACG图书馆' THEN 2
                WHEN 'ACG俱乐部' THEN 3
                WHEN '萌幻ACG' THEN 4
                ELSE 5
            END),
            likes DESC"""
        rows = conn.execute(query, params).fetchall()

        groups = {}
        for row in rows:
            d = dict(row)
            crawl_date = d.get("crawl_date") or "未知日期"
            if crawl_date not in groups:
                groups[crawl_date] = {"date": crawl_date, "posts": [], "total": 0}
            groups[crawl_date]["posts"].append(d)
            groups[crawl_date]["total"] += 1

        # 按日期倒序排列
        sorted_groups = sorted(groups.values(), key=lambda g: g["date"], reverse=True)
        return jsonify({"groups": sorted_groups})

@app.route("/api/start_crawl", methods=["POST"])
def api_start_crawl():
    if engine.running:
        return jsonify({"status": "error", "message": "已有任务在运行"})

    data = request.json
    mode = data.get("mode", "by_page")
    sites = data.get("sites", ["acgyxj", "acgrx", "acgll", "acgjlb"])

    log_store["logs"] = []
    progress_store.update({"current": 0, "total": 0, "success": 0, "skipped": 0, "error": 0})

    def run():
        if mode == "by_page":
            start_page = data.get("start_page", 1)
            end_page = data.get("end_page", 10)
            engine.crawl_by_page(sites, start_page, end_page)
        elif mode == "by_date":
            start_date = data.get("start_date", "")
            end_date = data.get("end_date", "")
            engine.crawl_by_date(sites, start_date, end_date)
        elif mode == "incremental":
            engine.crawl_incremental(sites)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return jsonify({"status": "ok"})

@app.route("/api/stop_crawl", methods=["POST"])
def api_stop_crawl():
    engine.cancel()
    return jsonify({"status": "ok"})

@app.route("/api/progress")
def api_progress():
    return jsonify({
        "running": engine.running,
        **progress_store,
        "recent_logs": log_store["logs"][-50:],
    })

@app.route("/api/tasks")
def api_tasks():
    return jsonify(get_tasks())

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

@app.route("/api/export")
def api_export():
    posts = get_posts(limit=10000)
    result = export_posts(posts)
    return jsonify({"status": "ok", "files": result})

@app.route("/api/export_counts")
def api_export_counts():
    """返回各平台导出数量"""
    pc = get_post_count(platform="pc")
    android = get_post_count(platform="android")
    mixed = get_post_count(platform="pc_android")
    return jsonify({"pc": pc, "android": android, "mixed": mixed})

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
        platform_filter = request.args.get("platform", "")
    if export_type == "pc":
        posts = get_posts(platform="pc", limit=10000)
    elif export_type == "android":
        posts = get_posts(platform="android", limit=10000)
    elif export_type == "mixed":
        posts = get_posts(platform="pc_android", limit=10000)
        pc_posts = get_posts(platform="pc", limit=10000)
        android_posts = get_posts(platform="android", limit=10000)
        posts = pc_posts + android_posts + posts
    else:
        posts = get_posts(limit=10000)

    result = export_posts(posts)

    if export_type == "pc":
        filepath = result.get("pc", "")
    elif export_type == "android":
        filepath = result.get("android", "")
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
        debug=flask_config.get("debug", True),
    )

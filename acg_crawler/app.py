"""ACG资源聚合爬取工具 - 主程序"""
import json
import threading
from flask import Flask, render_template, request, jsonify

from config import load_config
from database import init_db, get_posts, get_post_count, delete_post, get_tasks
from crawler import CrawlerEngine
from generator import export_posts

app = Flask(__name__)
config = load_config()
init_db()

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

@app.route("/api/posts")
def api_posts():
    platform = request.args.get("platform", "all")
    source = request.args.get("source", "all")
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    posts = get_posts(platform=platform, source=source, limit=limit, offset=offset)
    total = get_post_count(platform=platform, source=source)
    return jsonify({"posts": posts, "total": total})

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

@app.route("/api/export", methods=["POST"])
def api_export():
    posts = get_posts(limit=10000)
    result = export_posts(posts)
    return jsonify({"status": "ok", "files": result})

if __name__ == "__main__":
    flask_config = config.get("flask", {})
    app.run(
        host=flask_config.get("host", "127.0.0.1"),
        port=flask_config.get("port", 5000),
        debug=flask_config.get("debug", True),
    )

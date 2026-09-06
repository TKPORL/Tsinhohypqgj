"""ACG资源聚合爬取工具 - Demo版本（模拟数据）"""
from flask import Flask, render_template, jsonify
import random
import time

app = Flask(__name__)

MOCK_POSTS = [
    {
        "id": 1,
        "title": "【PC+安卓/汉化/SLG】 elfinithoot ～エルフニクスと死書の魔導書～ v1.0 汉化版",
        "source": "ACG游戏姬",
        "platform": "pc_android",
        "date": "2026-09-05",
        "likes": 342,
        "comments": 89,
        "views": 12400,
        "images": [
            "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/12345/capsule_616x353.jpg",
            "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/12345/ss_1.jpg",
        ],
        "baidu_link": "https://pan.baidu.com/s/1xxxxxxx",
        "baidu_code": "acgx",
        "mobile_link": "https://yun.139.com/xxx",
        "mobile_code": "",
        "unzip_code": "acgyxj.xyz",
        "cheat_code": "F1=无敌 F2=无限金钱",
        "source_url": "https://www.acgyxjvip.com/43546.html",
    },
    {
        "id": 2,
        "title": "【PC/汉化/RPG】 Alice's Spooky Adventure v1.0 汉化版",
        "source": "萌幻ACG",
        "platform": "pc",
        "date": "2026-09-04",
        "likes": 156,
        "comments": 42,
        "views": 5600,
        "images": [
            "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/23456/capsule_616x353.jpg",
        ],
        "baidu_link": "https://pan.baidu.com/s/2yyyyyyy",
        "baidu_code": "acgrx",
        "mobile_link": "",
        "mobile_code": "",
        "unzip_code": "acgrx.com",
        "cheat_code": "",
        "source_url": "https://bbs.acgrx.com/game/38622.html",
    },
    {
        "id": 3,
        "title": "【PC/官中/SLG】 王国之心4 v2.5 全DLC",
        "source": "ACG图书馆",
        "platform": "pc",
        "date": "2026-09-03",
        "likes": 567,
        "comments": 123,
        "views": 23100,
        "images": [
            "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/34567/capsule_616x353.jpg",
            "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/34567/ss_1.jpg",
            "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/34567/ss_2.jpg",
        ],
        "baidu_link": "https://pan.baidu.com/s/3zzzzzz",
        "baidu_code": "",
        "mobile_link": "https://yun.139.com/yyy",
        "mobile_code": "1234",
        "unzip_code": "acgll.xyz",
        "cheat_code": "",
        "source_url": "https://acgll.xyz/kingdom-hearts-4",
    },
    {
        "id": 4,
        "title": "【安卓/汉化/AVG】 校园日记 ～被禁止的梦～ v1.2 安卓版",
        "source": "ACG游戏姬",
        "platform": "android",
        "date": "2026-09-02",
        "likes": 89,
        "comments": 15,
        "views": 3200,
        "images": [
            "https://i.img114514.icu/xxx.jpg",
        ],
        "baidu_link": "https://pan.baidu.com/s/4aaaaaaa",
        "baidu_code": "game",
        "mobile_link": "https://yun.139.com/zzz",
        "mobile_code": "",
        "unzip_code": "acgyxj.top",
        "cheat_code": "",
        "source_url": "https://www.acgyxjvip.com/43500.html",
    },
    {
        "id": 5,
        "title": "【PC/安卓/汉化/动态】 少女领域Special v3.0 多平台版",
        "source": "萌幻ACG",
        "platform": "pc_android",
        "date": "2026-09-01",
        "likes": 445,
        "comments": 78,
        "views": 18900,
        "images": [
            "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/56789/capsule_616x353.jpg",
            "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/56789/ss_1.jpg",
        ],
        "baidu_link": "https://pan.baidu.com/s/5bbbbbbb",
        "baidu_code": "xbly",
        "mobile_link": "https://yun.139.com/www",
        "mobile_code": "5678",
        "unzip_code": "bbs.acgrx.com",
        "cheat_code": "Ctrl+G=调试模式",
        "source_url": "https://bbs.acgrx.com/game/38600.html",
    },
    {
        "id": 6,
        "title": "【PC/官中/NTR】 黑暗之魂:永恒 v1.5 完全版",
        "source": "ACG图书馆",
        "platform": "pc",
        "date": "2026-08-30",
        "likes": 234,
        "comments": 56,
        "views": 9800,
        "images": [
            "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/67890/capsule_616x353.jpg",
        ],
        "baidu_link": "https://pan.baidu.com/s/6ccccccc",
        "baidu_code": "hzsh",
        "mobile_link": "",
        "mobile_code": "",
        "unzip_code": "acgll.xyz",
        "cheat_code": "",
        "source_url": "https://acgll.xyz/dark-souls-eternal",
    },
]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/posts")
def get_posts():
    platform = __import__("flask").request.args.get("platform", "all")
    posts = MOCK_POSTS
    if platform == "pc":
        posts = [p for p in posts if p["platform"] in ("pc", "unknown")]
    elif platform == "pc_android":
        posts = [p for p in posts if p["platform"] == "pc_android"]
    elif platform == "android":
        posts = [p for p in posts if p["platform"] == "android"]
    posts.sort(key=lambda x: (x["likes"] + x["comments"]), reverse=True)
    return jsonify(posts)


@app.route("/api/start_crawl", methods=["POST"])
def start_crawl():
    return jsonify({"status": "ok", "task_id": 1})


@app.route("/api/progress")
def progress():
    return jsonify({
        "status": "running",
        "current": random.randint(1, 50),
        "total": 50,
        "log": [
            f"[{time.strftime('%H:%M:%S')}] 正在爬取第 {random.randint(1,50)} 页...",
            f"[{time.strftime('%H:%M:%S')}] 发现 {random.randint(5,20)} 个帖子",
            f"[{time.strftime('%H:%M:%S')}] 跳过 {random.randint(0,5)} 个(无网盘链接)",
        ],
    })


@app.route("/api/tasks")
def tasks():
    return jsonify([
        {"id": 1, "type": "by_page", "site": "ACG游戏姬", "pages": "1-10", "status": "completed", "total": 150, "success": 89, "time": "2026-09-05 14:30"},
        {"id": 2, "type": "by_date", "site": "萌幻ACG", "date": "2026-09-04", "status": "completed", "total": 45, "success": 23, "time": "2026-09-04 10:15"},
    ])


if __name__ == "__main__":
    app.run(debug=True, port=5000)

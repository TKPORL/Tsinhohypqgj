"""HTML生成器"""
import json
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #0a0a0f; color: #e0e0e0; }}
.header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 24px; text-align: center; border-bottom: 1px solid #2a2a3e; }}
.header h1 {{ font-size: 24px; color: #4fc3f7; margin-bottom: 8px; }}
.header .meta {{ color: #888; font-size: 14px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; padding: 24px; max-width: 1400px; margin: 0 auto; }}
.card {{ background: #181825; border-radius: 12px; overflow: hidden; border: 1px solid #2a2a3e; transition: transform 0.2s; }}
.card:hover {{ transform: translateY(-3px); box-shadow: 0 12px 32px rgba(0,0,0,0.4); }}
.card-img {{ width: 100%; height: 200px; object-fit: cover; }}
.card-body {{ padding: 16px; }}
.card-title {{ font-size: 14px; font-weight: 500; line-height: 1.6; margin-bottom: 12px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
.card-meta {{ display: flex; gap: 16px; font-size: 12px; color: #888; margin-bottom: 12px; }}
.card-links {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.link-btn {{ padding: 6px 14px; border-radius: 6px; font-size: 12px; text-decoration: none; color: #fff; }}
.link-baidu {{ background: linear-gradient(135deg, #2196F3, #1565c0); }}
.link-mobile {{ background: linear-gradient(135deg, #4CAF50, #2e7d32); }}
.link-source {{ background: #1e1e2e; color: #e0e0e0; border: 1px solid #2a2a3e; }}
.card-footer {{ padding: 10px 16px; background: rgba(0,0,0,0.25); font-size: 12px; color: #888; border-top: 1px solid #2a2a3e; }}
.copy-text {{ cursor: pointer; padding: 2px 6px; background: rgba(79,195,247,0.1); border-radius: 3px; font-family: monospace; }}
.copy-text:hover {{ background: rgba(79,195,247,0.2); }}
.tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }}
.tag-pc {{ background: rgba(79,195,247,0.15); color: #4fc3f7; }}
.tag-android {{ background: rgba(102,187,106,0.15); color: #66bb6a; }}
.tag-source {{ background: rgba(255,167,38,0.15); color: #ffa726; }}
</style>
</head>
<body>
<div class="header">
<h1>{title}</h1>
<div class="meta">生成时间: {gen_time} | 共 {count} 条资源</div>
</div>
<div class="grid">
{cards}
</div>
<script>
function copyText(el) {{
    navigator.clipboard.writeText(el.textContent).then(function() {{
        el.style.background = "rgba(102,187,106,0.3)";
        setTimeout(function() {{ el.style.background = ""; }}, 500);
    }});
}}
</script>
</body>
</html>"""

CARD_TEMPLATE = """
<div class="card">
<img class="card-img" src="{image}" alt="" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 400 200%22><rect fill=%22%23181825%22 width=%22400%22 height=%22200%22/><text fill=%22%23555%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22>No Image</text></svg>'">
<div class="card-body">
<div class="card-title">{title}</div>
<div class="card-meta">
<span>{platform_tag}</span>
<span class="tag tag-source">{source}</span>
<span>{date}</span>
<span>❤ {likes}</span>
<span>💬 {comments}</span>
</div>
<div class="card-links">
{links}
</div>
</div>
{footer}
</div>"""

def generate_html(posts, title, filename):
    """生成HTML文件"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cards_html = ""
    for post in posts:
        # 图片
        images = []
        try:
            images = json.loads(post.get("images", "[]"))
        except:
            pass
        image = images[0] if images else ""

        # 平台标签
        platform = post.get("platform", "unknown")
        platform_tags = {
            "pc": '<span class="tag tag-pc">PC</span>',
            "android": '<span class="tag tag-android">安卓</span>',
            "pc_android": '<span class="tag tag-pc">PC</span> <span class="tag tag-android">安卓</span>',
            "unknown": '<span class="tag tag-pc">未知</span>',
        }
        platform_tag = platform_tags.get(platform, platform_tags["unknown"])

        # 链接
        links = []
        if post.get("baidu_link"):
            code = post.get("baidu_code", "")
            links.append(f'<a href="{post["baidu_link"]}" class="link-btn link-baidu" target="_blank">百度网盘{(" ("+code+")") if code else ""}</a>')
        if post.get("mobile_link"):
            code = post.get("mobile_code", "")
            links.append(f'<a href="{post["mobile_link"]}" class="link-btn link-mobile" target="_blank">移动云盘{(" ("+code+")") if code else ""}</a>')
        links.append(f'<a href="{post.get("source_url", "#")}" class="link-btn link-source" target="_blank">原帖</a>')
        links_html = "\n".join(links)

        # 底部
        footer = ""
        parts = []
        if post.get("unzip_code"):
            parts.append(f'解压码: <span class="copy-text" onclick="copyText(this)">{post["unzip_code"]}</span>')
        if post.get("cheat_code"):
            parts.append(f'作弊码: <span class="copy-text" onclick="copyText(this)">{post["cheat_code"]}</span>')
        if parts:
            footer = f'<div class="card-footer">{"&nbsp;&nbsp;|&nbsp;&nbsp;".join(parts)}</div>'

        card = CARD_TEMPLATE.format(
            image=image,
            title=post.get("title", ""),
            platform_tag=platform_tag,
            source=post.get("source", ""),
            date=post.get("post_date", ""),
            likes=post.get("likes", 0),
            comments=post.get("comments", 0),
            links=links_html,
            footer=footer,
        )
        cards_html += card + "\n"

    html = HTML_TEMPLATE.format(
        title=title,
        gen_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        count=len(posts),
        cards=cards_html,
    )

    filepath = OUTPUT_DIR / filename
    filepath.write_text(html, encoding="utf-8")
    return str(filepath)

def export_posts(posts):
    """导出帖子为HTML"""
    pc_posts = [p for p in posts if p.get("platform") in ("pc",)]
    android_posts = [p for p in posts if p.get("platform") in ("android",)]
    mixed_posts = [p for p in posts if p.get("platform") in ("pc", "pc_android", "android")]

    pc_file = generate_html(pc_posts, "ACG游戏资源 - PC下载", "PC下载.html")
    android_file = generate_html(android_posts, "ACG游戏资源 - 仅安卓", "仅安卓.html")
    mixed_file = generate_html(mixed_posts, "ACG游戏资源 - PC+安卓下载", "PC+安卓下载.html")

    return {"pc": pc_file, "android": android_file, "mixed": mixed_file}

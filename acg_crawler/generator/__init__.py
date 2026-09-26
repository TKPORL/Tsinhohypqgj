"""HTML生成器"""
import html as html_lib
import json
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from database import sort_posts
from parser import game_name_from_title, bare_name_from_title

OUTPUT_DIR = Path(__file__).parent.parent / "output"
IMAGES_DIR = Path(__file__).parent.parent / "images"


def _copy_image_to_output(img_path, output_images_dir):
    """将图片复制到output/images目录，返回相对路径"""
    if not img_path or img_path.startswith("http"):
        return img_path
    # 处理 images/xxx/file.jpg 路径
    full = IMAGES_DIR.parent / img_path
    if not full.exists():
        return ""
    # 用post_id/filename作为目标路径
    rel_path = img_path.replace("images/", "")
    dest = output_images_dir / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(str(full), str(dest))
    return f"images/{rel_path}"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
/* 深色 · 粉紫 —— 与主界面同一套视觉（2026-09-26） */
:root {{
    --bg-deep: #0b0a10;
    --bg-canvas: #121119;
    --bg-card: #1a1824;
    --bg-card-hover: #221f2e;
    --bg-inset: #0b0a10;
    --text-primary: #f2eff7;
    --text-muted: #a9a3b8;
    --text-dim: #756f86;
    --accent: #e056a0;
    --accent-hover: #ef6fb1;
    --accent-soft: rgba(224, 86, 160, 0.14);
    --accent-line: rgba(224, 86, 160, 0.45);
    --on-accent: #1a0f16;
    --plat-pc: #8b5cf6;
    --plat-mixed: #e056a0;
    --plat-android: #f2765c;
    --border: rgba(255, 255, 255, 0.07);
    --border-strong: rgba(255, 255, 255, 0.14);
    --hairline: rgba(255, 255, 255, 0.10);
    --chip-bg: rgba(255, 255, 255, 0.06);
    --chip-border: rgba(255, 255, 255, 0.10);
    --font-ui: system-ui, -apple-system, 'Segoe UI', 'PingFang SC', 'HarmonyOS Sans SC', 'Microsoft YaHei', 'Noto Sans SC', sans-serif;
    --font-num: ui-monospace, 'SF Mono', 'Cascadia Mono', 'JetBrains Mono', Consolas, 'Courier New', monospace;
    --radius-btn: 10px;
    --radius-card: 14px;
    --radius-input: 10px;
    --radius-pill: 9999px;
    --ease: 0.18s ease;
    /* 兼容旧变量名 */
    --fog: var(--text-dim);
    --ash: var(--text-muted);
    --cloud: var(--text-primary);
    --pure: var(--text-primary);
    --void: var(--bg-deep);
    --abyss: var(--bg-deep);
    --obsidian: var(--bg-canvas);
    --graphite: var(--bg-card);
    --steel: var(--bg-card-hover);
    --cyan: var(--accent);
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ overflow-x: clip; }}
body {{
    background: var(--bg-canvas);
    color: var(--text-primary);
    font-family: var(--font-ui);
    font-size: 14px;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
    padding-bottom: 80px;
}}
.header {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 40px 32px 20px;
    border-bottom: 1px solid var(--hairline);
}}
.header h1 {{
    font-size: 26px;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--text-primary);
}}
.meta {{
    margin-top: 10px;
    font-size: 13px;
    color: var(--text-dim);
    font-variant-numeric: tabular-nums;
}}
.grid {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px 32px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
    gap: 16px;
}}
.card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-card);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: background var(--ease), border-color var(--ease);
}}
.card:hover {{ background: var(--bg-card-hover); border-color: var(--border-strong); }}
.card-imgs {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 1px;
    background: rgba(255, 255, 255, 0.06);
    overflow: hidden;
    max-height: 250px;
}}
.card-imgs img {{ width: 100%; height: 100%; min-height: 108px; object-fit: cover; display: block; background: var(--bg-deep); cursor: zoom-in; }}
.card-imgs:has(img:nth-child(1):last-child) img {{ height: 280px; min-height: 280px; }}
.no-img {{
    height: 160px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-deep);
    font-size: 13px;
    color: var(--text-dim);
}}
.card-body {{ padding: 16px; display: flex; flex-direction: column; flex: 1; }}
.card-title {{
    font-size: 14px;
    line-height: 1.5;
    color: var(--text-primary);
    margin-bottom: 12px;
    overflow-wrap: anywhere;
    cursor: pointer;
    transition: color var(--ease);
}}
.card-title:hover {{ color: var(--accent); }}
.card-meta {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-bottom: 12px;
    font-size: 12px;
    color: var(--text-dim);
}}
.tag {{
    display: inline-flex;
    align-items: center;
    font-size: 12px;
    padding: 2px 10px;
    background: var(--chip-bg);
    border: 1px solid var(--chip-border);
    border-radius: var(--radius-pill);
    color: var(--text-muted);
    white-space: nowrap;
}}
.tag-pc {{ color: var(--plat-pc); border-color: rgba(139, 92, 246, 0.35); }}
.tag-android {{ color: var(--plat-android); border-color: rgba(242, 118, 92, 0.35); }}
.tag-source {{ color: var(--text-muted); }}
.card-links {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.link-btn {{
    padding: 0 14px;
    min-height: 34px;
    display: inline-flex;
    align-items: center;
    border: 1px solid var(--accent-line);
    border-radius: var(--radius-btn);
    background: transparent;
    color: var(--accent);
    font-size: 12px;
    text-decoration: none;
    transition: background var(--ease), color var(--ease), border-color var(--ease);
}}
.link-btn:hover {{ background: var(--accent); border-color: var(--accent); color: var(--on-accent); }}
.link-source {{ border-color: var(--border); color: var(--text-muted); }}
.link-source:hover {{ background: var(--bg-card-hover); border-color: var(--border-strong); color: var(--text-primary); }}
/* 解压码 / 作弊码按钮：跟链接按钮同一行，虚线边框表示"这是可复制的码" */
.btn-code {{
    cursor: pointer;
    font-family: var(--font-ui);
    background: var(--chip-bg);
    border: 1px dashed var(--accent-line);
    color: var(--accent);
}}
.btn-code:hover {{ background: var(--accent); border-color: var(--accent); border-style: solid; color: var(--on-accent); }}
.btn-code.copied {{ background: var(--accent); border-color: var(--accent); border-style: solid; color: var(--on-accent); }}
/* 游戏名按钮：实心强调色，点一下复制（= 网盘里的游戏名），比其它按钮更醒目 */
.btn-game {{
    cursor: pointer;
    font-family: var(--font-ui);
    background: var(--accent-soft);
    border: 1px solid var(--accent-line);
    color: var(--accent);
    font-weight: 600;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.btn-game:hover {{ background: var(--accent); border-color: var(--accent); color: var(--on-accent); }}
.btn-game.copied {{ background: var(--accent); border-color: var(--accent); color: var(--on-accent); }}
/* 复制名称按钮：纯游戏名（发帖表单「游戏名称」栏用），描边款和游戏名按钮区分 */
.btn-bare {{
    cursor: pointer;
    font-family: var(--font-ui);
    background: transparent;
    border: 1px dashed var(--accent-line);
    color: var(--accent);
    font-weight: 600;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.btn-bare:hover {{ background: var(--accent-soft); border-style: solid; }}
.btn-bare.copied {{ background: var(--accent); border-color: var(--accent); border-style: solid; color: var(--on-accent); }}
.card-footer {{
    margin-top: auto;
    padding: 10px 16px;
    background: var(--bg-inset);
    border-top: 1px solid var(--border);
}}
.copy-text {{
    cursor: pointer;
    padding: 0 12px;
    min-height: 30px;
    background: var(--chip-bg);
    border: 1px solid var(--chip-border);
    border-radius: var(--radius-pill);
    color: var(--text-primary);
    font-family: var(--font-ui);
    font-size: 12px;
    transition: background var(--ease), border-color var(--ease), color var(--ease);
}}
.copy-text:hover {{ background: var(--accent-soft); border-color: var(--accent-line); color: var(--accent); }}
.copy-text:active {{ transform: translateY(1px); }}
.copy-text.copied {{ background: var(--accent-soft); border-color: var(--accent-line); color: var(--accent); }}
.card-note {{
    margin-top: 12px;
    padding: 12px;
    background: var(--bg-inset);
    border: 1px solid var(--border);
    border-radius: var(--radius-input);
    transition: border-color var(--ease), background var(--ease);
}}
.card-note:hover {{ border-color: var(--border-strong); }}
.card-note.copied-note {{ border-color: var(--accent-line); background: var(--accent-soft); }}
.note-head {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 12px;
    color: var(--text-dim);
    margin-bottom: 8px;
}}
.note-copy-hint {{ font-size: 12px; color: var(--text-dim); transition: color var(--ease); }}
.card-note:hover .note-copy-hint {{ color: var(--text-muted); }}
.note-body {{
    font-size: 12px;
    line-height: 1.7;
    color: var(--text-muted);
    white-space: pre-wrap;
    word-break: break-word;
    overflow: hidden;
    cursor: pointer;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
}}
.note-body:hover {{ color: var(--text-primary); }}
.note-body.expanded {{ -webkit-line-clamp: unset; display: block; }}
.note-toggle {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-top: 8px;
    padding: 2px 4px;
    background: none;
    border: 0;
    border-radius: 4px;
    color: var(--text-muted);
    font-family: var(--font-ui);
    font-size: 12px;
    cursor: pointer;
    transition: color var(--ease);
}}
.note-toggle:hover {{ color: var(--accent); }}
.note-toggle:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.note-arrow {{ display: inline-block; font-size: 11px; transition: transform 0.22s ease; }}
.note-toggle[aria-expanded="true"] .note-arrow {{ transform: rotate(180deg); }}
.note-toggle[hidden] {{ display: none; }}
.lightbox-overlay {{
    position: fixed;
    inset: 0;
    background: rgba(11, 10, 16, 0.96);
    z-index: 2000;
    display: flex;
    align-items: center;
    justify-content: center;
}}
.lightbox-img {{ max-width: 92vw; max-height: 88vh; border-radius: var(--radius-btn); border: 1px solid var(--border); }}
.lightbox-close, .lightbox-nav {{
    background: rgba(255, 255, 255, 0.10);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-pill);
    color: var(--text-primary);
    cursor: pointer;
    transition: background var(--ease);
}}
.lightbox-close {{ position: absolute; top: 24px; right: 24px; width: 44px; height: 44px; font-size: 18px; }}
.lightbox-nav {{ position: absolute; top: 50%; transform: translateY(-50%); width: 44px; height: 44px; font-size: 18px; }}
.lightbox-close:hover, .lightbox-nav:hover {{ background: rgba(255, 255, 255, 0.20); }}
.lightbox-prev {{ left: 24px; }}
.lightbox-next {{ right: 24px; }}
.lightbox-counter {{
    position: absolute;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 12px;
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
}}
@media (max-width: 640px) {{
    .header {{ padding: 28px 16px 16px; }}
    .header h1 {{ font-size: 20px; }}
    .grid {{ padding: 16px; grid-template-columns: 1fr; }}
}}
@media (prefers-reduced-motion: reduce) {{
    * {{ transition: none !important; }}
}}
</style>
</head>
<body>
<div class="header">
<h1>{title}</h1>
<div class="meta">生成时间 {gen_time} · 共 {count} 条资源</div>
</div>
<div class="grid">
{cards}
</div>
<script>
function copyText(el) {{
    var text = el.dataset.copy || el.textContent;
    navigator.clipboard.writeText(text).then(function() {{
        el.classList.add("copied");
        var orig = el.textContent;
        el.textContent = "已复制!";
        setTimeout(function() {{ el.classList.remove("copied"); el.textContent = orig; }}, 900);
    }});
}}
// 备注整块点击复制（复制完整备注，不是被折叠截断的那段）
function copyNote(el) {{
    var text = el.dataset.copy || el.textContent;
    navigator.clipboard.writeText(text).then(function() {{
        var box = el.closest(".card-note") || el;
        box.classList.add("copied-note");
        var hint = box.querySelector(".note-copy-hint");
        var orig = hint ? hint.textContent : "";
        if (hint) hint.textContent = "已复制!";
        setTimeout(function() {{
            box.classList.remove("copied-note");
            if (hint) hint.textContent = orig;
        }}, 900);
    }});
}}
function copyTitle(el) {{
    navigator.clipboard.writeText(el.textContent).then(function() {{
        var orig = el.textContent;
        el.textContent = "已复制!";
        setTimeout(function() {{ el.textContent = orig; }}, 800);
    }});
}}
// 备注折叠：量目标态真实高度后做高度动画，收尾清掉内联高度
function noteHeightWhen(body, expanded) {{
    var was = body.classList.contains("expanded");
    if (was !== expanded) body.classList.toggle("expanded", expanded);
    var h = body.offsetHeight;
    if (was !== expanded) body.classList.toggle("expanded", was);
    return h;
}}
function toggleNote(btn) {{
    var body = document.getElementById(btn.getAttribute("aria-controls"));
    if (!body) return;
    var next = btn.getAttribute("aria-expanded") !== "true";
    var start = body.offsetHeight;
    var target = noteHeightWhen(body, next);
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    body.style.transition = "none";
    body.style.maxHeight = start + "px";
    void body.offsetHeight;
    body.style.transition = reduce ? "none" : "max-height 0.22s ease";
    body.classList.toggle("expanded", next);
    body.style.maxHeight = target + "px";
    btn.setAttribute("aria-expanded", next ? "true" : "false");
    btn.setAttribute("aria-label", next ? "收起备注" : "展开备注");
    var t = btn.querySelector(".note-toggle-text");
    if (t) t.textContent = next ? "收起" : "展开";
    setTimeout(function() {{
        body.style.maxHeight = "";
        body.style.transition = "";
    }}, reduce ? 0 : 240);
}}
// 文字没超过折叠行数时不显示按钮
function initNotes() {{
    document.querySelectorAll(".card-note").forEach(function(box) {{
        var body = box.querySelector(".note-body");
        var btn = box.querySelector(".note-toggle");
        if (!body || !btn) return;
        var full = noteHeightWhen(body, true);
        var clamped = noteHeightWhen(body, false);
        btn.hidden = (full - clamped) <= 2;
    }});
}}
if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", initNotes);
}} else {{
    initNotes();
}}
var lbState = {{ imgs: [], idx: 0, overlay: null }};
function openLightbox(sources, start) {{
    lbState.imgs = sources || [];
    lbState.idx = start || 0;
    if (!lbState.imgs.length) return;
    var ov = document.createElement("div");
    ov.className = "lightbox-overlay";
    var counter = document.createElement("div");
    counter.className = "lightbox-counter";
    var img = document.createElement("img");
    img.className = "lightbox-img";
    var closeBtn = document.createElement("button");
    closeBtn.className = "lightbox-close";
    closeBtn.textContent = "×";
    var prevBtn = document.createElement("button");
    prevBtn.className = "lightbox-nav lightbox-prev";
    prevBtn.textContent = "‹";
    var nextBtn = document.createElement("button");
    nextBtn.className = "lightbox-nav lightbox-next";
    nextBtn.textContent = "›";
    ov.appendChild(counter); ov.appendChild(img); ov.appendChild(closeBtn);
    if (lbState.imgs.length > 1) {{ ov.appendChild(prevBtn); ov.appendChild(nextBtn); }}
    document.body.appendChild(ov);
    document.body.style.overflow = "hidden";
    lbState.overlay = ov;
    function render() {{
        img.src = lbState.imgs[lbState.idx];
        counter.textContent = (lbState.idx + 1) + " / " + lbState.imgs.length;
        var multi = lbState.imgs.length > 1;
        prevBtn.style.display = multi ? "" : "none";
        nextBtn.style.display = multi ? "" : "none";
    }}
    function close() {{
        if (lbState.overlay) {{
            document.body.removeChild(lbState.overlay);
            document.body.style.overflow = "";
            lbState.overlay = null;
        }}
    }}
    function step(d) {{
        var n = lbState.imgs.length;
        if (!n) return;
        lbState.idx = (lbState.idx + d + n) % n;
        render();
    }}
    ov.addEventListener("click", function(e) {{ if (e.target === ov || e.target === img) close(); }});
    closeBtn.addEventListener("click", close);
    prevBtn.addEventListener("click", function(e) {{ e.stopPropagation(); step(-1); }});
    nextBtn.addEventListener("click", function(e) {{ e.stopPropagation(); step(1); }});
    document.addEventListener("keydown", function(e) {{
        if (!lbState.overlay) return;
        if (e.key === "Escape") close();
        else if (e.key === "ArrowLeft") step(-1);
        else if (e.key === "ArrowRight") step(1);
    }});
    render();
}}
document.addEventListener("click", function(e) {{
    var img = e.target.closest(".card-imgs img");
    if (!img) return;
    var container = img.closest(".card-imgs");
    if (!container) return;
    var sources = [];
    container.querySelectorAll("img").forEach(function(im) {{ if (im.src) sources.push(im.src); }});
    var idx = Array.prototype.indexOf.call(container.querySelectorAll("img"), img);
    openLightbox(sources, idx);
}});
</script>
</body>
</html>"""

CARD_TEMPLATE = """
<div class="card">
<div class="card-imgs">{images_html}</div>
<div class="card-body">
<div class="card-title" onclick="copyTitle(this)" title="点击复制标题">{title}</div>
<div class="card-meta">
<span>{platform_tag}</span>
<span class="tag tag-source">{source}</span>
<span>{date}</span>
<span><span style="color:var(--fog)">LIKE</span> {likes}</span>
</div>
<div class="card-links">
{links}
</div>
{note}
</div>
{footer}
</div>"""

def generate_html(posts, title, filename):
    """生成HTML文件，图片单独存放在output/images/目录（每次导出前清空旧图片）"""
    output_dir = OUTPUT_DIR / filename.replace(".html", "")
    output_images_dir = output_dir / "images"
    # 清空旧图片目录，避免上次导出的残留图片混入本次zip
    if output_images_dir.exists():
        shutil.rmtree(output_images_dir)
    output_images_dir.mkdir(parents=True, exist_ok=True)

    cards_html = ""
    for post in posts:
        # 图片 - 复制到output/images，使用相对路径
        images = []
        try:
            images = json.loads(post.get("images", "[]"))
        except:
            pass
        imgs_html = ""
        for raw_img in images:
            local_path = _copy_image_to_output(raw_img, output_images_dir)
            if local_path:
                imgs_html += f'<img src="{local_path}" alt="" onerror="this.style.display=\'none\'">'
            elif raw_img.startswith("http"):
                # 远程URL保留引用（离线时不可用）
                imgs_html += f'<img src="{raw_img}" alt="" onerror="this.style.display=\'none\'">'
        if not imgs_html:
            imgs_html = '<div class="no-img">暂无图片</div>'

        # 平台标签
        platform = post.get("platform", "unknown")
        platform_tags = {
            "pc": '<span class="tag tag-pc">PC</span>',
            "android": '<span class="tag tag-android">安卓</span>',
            "pc_android": '<span class="tag tag-pc">PC</span> <span class="tag tag-android">安卓</span>',
            "unknown": '<span class="tag tag-pc">未知</span>',
        }
        platform_tag = platform_tags.get(platform, platform_tags["unknown"])

        # 链接：优先用 download_items_json 多链接渲染，单网盘回退兼容字段
        # 按钮顺序（用户 2026-09-26）：游戏名 → 百度网盘 → 原帖 → 解压码 → 作弊码
        links = []
        items = []
        raw_items = post.get("download_items_json")
        if raw_items:
            try:
                items = json.loads(raw_items) if isinstance(raw_items, str) else raw_items
            except Exception:
                items = []

        # 游戏名按钮：从标题抽「游戏名【平台 大小】」，点一下复制
        # （用户 2026-09-26：这就是网盘里的游戏名，方便去网盘里找）
        gname = game_name_from_title(post.get("title", ""))
        if gname:
            _gn = html_lib.escape(gname, quote=True)
            links.append(
                f'<button class="link-btn btn-game" data-copy="{_gn}" '
                f'title="点击复制网盘名：{_gn}" onclick="copyText(this)">游戏名</button>'
            )

        # 复制名称按钮：纯游戏名（不带平台/大小/编号），
        # 发帖表单第一栏「游戏名称」直接粘贴用（用户 2026-09-26）
        bname = bare_name_from_title(post.get("title", ""))
        if bname:
            _bn = html_lib.escape(bname, quote=True)
            links.append(
                f'<button class="link-btn btn-bare" data-copy="{_bn}" '
                f'title="点击复制：{_bn}" onclick="copyText(this)">复制名称</button>'
            )

        def _label_for(plat):
            if plat == "pc":
                return "PC"
            if plat == "android":
                return "安卓"
            if plat == "pc_android":
                return "PC+安卓"
            return ""

        def _code_suffix(code):
            return f" ({code})" if code else ""

        if items:
            # 按平台归类，单个网盘最多输出 2 个按钮（移动云盘 2026-09-24 起下线，只渲染百度）
            # 同 URL 只出一个按钮（用户 2026-09-24：一条链接不该拆成 PC/安卓 两个按钮），平台取并集
            for provider, label_zh in (("baidu", "百度网盘"),):
                plats = [it for it in items if it.get("provider") == provider]
                if not plats:
                    continue
                seen_urls = set()
                for it in plats:
                    url = it.get("url", "#")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    plat_set = {o.get("platform") or "unknown"
                                for o in plats if o.get("url", "#") == url}
                    if "pc_android" in plat_set or {"pc", "android"} <= plat_set:
                        plat = "pc_android"
                    elif "pc" in plat_set:
                        plat = "pc"
                    elif "android" in plat_set:
                        plat = "android"
                    else:
                        plat = "unknown"
                    suffix = _label_for(plat)
                    cls = "link-baidu" if provider == "baidu" else "link-mobile"
                    text = f"{label_zh}({suffix})" if suffix else label_zh
                    links.append(
                        f'<a href="{it.get("url", "#")}" class="link-btn {cls}" target="_blank">'
                        f'{text}{_code_suffix(it.get("code"))}</a>'
                    )
        else:
            # 兼容老数据：按 baidu_link 单条渲染（移动云盘已下线，不渲染 mobile_link）
            if post.get("baidu_link"):
                code = post.get("baidu_code", "")
                links.append(f'<a href="{post["baidu_link"]}" class="link-btn link-baidu" target="_blank">百度网盘{(" ("+code+")") if code else ""}</a>')
        links.append(f'<a href="{post.get("source_url", "#")}" class="link-btn link-source" target="_blank">原帖</a>')

        # 解压码 / 作弊码按钮：紧跟「百度网盘」「原帖」同一行，
        # 一眼能看到、顺手点（用户 2026-09-26：原来在卡片最底部不好找）
        if post.get("unzip_code"):
            # 解压码文本由爬虫端生成完整格式（如"解压码007721"），这里不再加前缀
            _uc = html_lib.escape(str(post["unzip_code"]), quote=True)
            links.append(f'<button class="link-btn btn-code" data-copy="{_uc}" title="{_uc}" onclick="copyText(this)">解压码</button>')
        if post.get("cheat_code"):
            _cc = html_lib.escape(str(post["cheat_code"]), quote=True)
            links.append(f'<button class="link-btn btn-code" data-copy="作弊码：{_cc}" title="作弊码：{_cc}" onclick="copyText(this)">作弊码</button>')
        links_html = "\n".join(links)

        # 底部（已无内容，保留结构位以便后续扩展）
        footer = ""

        # 备注（发布者说明）：折叠 3 行，超出才给展开按钮；整块点击复制
        # 仅鲲Galgame 需要（用户为主的站点才有发布者备注）；其余四站为管理员整理站，
        # 其 content 是游戏简介，不属于备注，卡片不展示（2026-09-23 用户确认恢复）
        note_html = ""
        note_text = (post.get("content") or "").strip()
        if note_text and post.get("source") == "鲲Galgame":
            shown = note_text[:2000] + "……" if len(note_text) > 2000 else note_text
            # 复制内容 = 完整备注但去掉开头"网盘大小"行（用户 2026-09-24：界面保留显示，复制不含）
            copy_text = re.sub(r"^网盘大小：[^\n]*\n+", "", note_text).strip()
            note_id = f"note-{post.get('id', 'x')}"
            note_html = (
                '<div class="card-note">'
                '<div class="note-head"><span>备注</span><span class="note-copy-hint">点击复制</span></div>'
                f'<div class="note-body" id="{note_id}" data-copy="{html_lib.escape(copy_text, quote=True)}" '
                f'title="点击复制备注" onclick="copyNote(this)">{html_lib.escape(shown)}</div>'
                f'<button class="note-toggle" type="button" aria-expanded="false" '
                f'aria-controls="{note_id}" aria-label="展开备注" onclick="toggleNote(this)">'
                '<span class="note-toggle-text">展开</span>'
                '<span class="note-arrow" aria-hidden="true">▾</span>'
                '</button>'
                '</div>'
            )

        card = CARD_TEMPLATE.format(
            images_html=imgs_html,
            title=html_lib.escape(post.get("title", ""), quote=False),
            platform_tag=platform_tag,
            source=post.get("source", ""),
            date=post.get("post_date", ""),
            likes=post.get("likes", 0),
            links=links_html,
            note=note_html,
            footer=footer,
        )
        cards_html += card + "\n"

    html = HTML_TEMPLATE.format(
        title=title,
        gen_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        count=len(posts),
        cards=cards_html,
    )

    filepath = output_dir / filename
    filepath.write_text(html, encoding="utf-8")
    return str(filepath)

def export_posts_filtered(posts, source="all"):
    """按筛选条件导出帖子为单个zip（含所有平台）。

    用于"导出当前筛选"按钮：用户在结果页按来源/平台/搜索条件筛选后，
    一键导出所有匹配帖子（不分平台），生成单个zip文件。
    """
    posts = sort_posts(posts)
    tag = source if source and source != "all" else "全部来源"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"筛选导出-{tag}-{ts}"
    title = f"ACG游戏资源 - {tag}筛选结果"
    html_file = generate_html(posts, title, f"{base}.html")
    zip_file = _zip_output(html_file, base)
    _cleanup_old_exports(keep=10)
    return {"filtered": zip_file}


def export_posts(posts, name_suffix=""):
    """导出为三个 zip：PC / PC+安卓 / 安卓。

    2026-09-23 起单安卓（platform='android'）不再并入 PC+安卓，三类互不重叠；
    unknown 归入 PC。某类无数据则该 zip 为 None（前端可据此禁用按钮）。
    """
    posts = sort_posts(posts)
    pc_posts = [p for p in posts if p.get("platform") in ("pc", "unknown")]
    pc_android_posts = [p for p in posts if p.get("platform") == "pc_android"]
    android_posts = [p for p in posts if p.get("platform") == "android"]

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    def _base(prefix):
        return f"{prefix}-{name_suffix}-{ts}" if name_suffix else f"{prefix}-{ts}"

    result = {}
    for key, title, group in (
        ("pc", "PC下载", pc_posts),
        ("pc_android", "PC+安卓下载", pc_android_posts),
        ("android", "安卓下载", android_posts),
    ):
        if not group:
            result[key] = ""
            continue
        base = _base(title)
        html_file = generate_html(group, f"ACG游戏资源 - {title}", f"{base}.html")
        result[key] = _zip_output(html_file, base)

    # 三个zip都完成后再清理旧导出，避免清理误删本次刚生成的临时目录
    _cleanup_old_exports(keep=10)
    result["mixed"] = result.get("pc_android") or ""   # 兼容旧前端/脚本
    return result


def _zip_output(html_path, zip_name):
    """将导出目录打包为zip，包含HTML和images"""
    if not html_path:
        return ""
    html_path = Path(html_path)
    output_dir = html_path.parent
    zip_path = OUTPUT_DIR / f"{zip_name}.zip"

    with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
        # 添加HTML文件
        zf.write(str(html_path), html_path.name)
        # 添加images目录
        images_dir = output_dir / "images"
        if images_dir.exists():
            for img_file in images_dir.rglob("*"):
                if img_file.is_file():
                    arcname = f"images/{img_file.relative_to(images_dir)}"
                    zf.write(str(img_file), arcname)

    return str(zip_path)


def _cleanup_old_exports(keep=10):
    """output/ 只保留最近 keep 个zip及其同名临时目录，其余删除。

    每次导出都会生成新时间戳文件，不清理会无限膨胀。
    删除失败（文件被占用等）仅跳过，不影响导出。
    """
    import shutil as _sh
    try:
        zips = sorted(
            (f for f in OUTPUT_DIR.glob("*.zip") if f.is_file()),
            key=lambda p: p.stat().st_mtime, reverse=True)
        for old_zip in zips[keep:]:
            try:
                old_zip.unlink()
            except Exception:
                pass
        # 与保留zip同名的临时目录保留，其余删除
        keep_stems = {p.stem for p in zips[:keep]}
        for d in OUTPUT_DIR.iterdir():
            if d.is_dir() and d.stem not in keep_stems:
                try:
                    _sh.rmtree(d)
                except Exception:
                    pass
    except Exception:
        pass  # 清理失败不影响导出主流程

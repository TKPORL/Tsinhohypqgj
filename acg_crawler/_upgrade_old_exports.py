# -*- coding: utf-8 -*-
"""把旧的导出 HTML 升级成新版卡片样式（2026-09-26）

用户需求：之前导出的 4 份 HTML 里，卡片要加上「游戏名」按钮、
按钮顺序改成「游戏名 → 百度网盘 → 原帖 → 解压码 → 作弊码」，
并把解压码从卡片底部 footer 挪到按钮行。

做法：
  1. 用 BeautifulSoup 解析旧 HTML 的每张 .card，抽出字段；
  2. 用 generator 里最新的 HTML_TEMPLATE / CARD_TEMPLATE 重新渲染；
  3. 图片仍引用原来的相对路径（images/xxx 不复制、不重下）；
  4. 原文件先备份成 *.bak-旧版.html。

用法：
    python _upgrade_old_exports.py            # 预演，只报数量
    python _upgrade_old_exports.py --apply    # 真改（自动备份）
"""
import re
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from bs4 import BeautifulSoup  # noqa: E402
from parser import game_name_from_title, bare_name_from_title  # noqa: E402
import generator  # noqa: E402

APPLY = "--apply" in sys.argv

TARGETS = [
    r"D:/下载目录/PC+安卓下载1/PC+安卓下载-ACG俱乐部-ACG图书馆-ACG游戏姬-萌幻ACG-鲲Galgame-20260925-082419.html",
    r"D:/下载目录/PC下载-鲲/PC下载-鲲Galgame-20260924-191648.html",
    r"D:/下载目录/PC+安卓下载-鲲/PC+安卓下载-鲲Galgame-20260924-191650.html",
    r"D:/下载目录/PC1/PC下载-ACG俱乐部-ACG图书馆-ACG游戏姬-萌幻ACG-鲲Galgame-20260925-082347.html",
]


def _txt(el):
    return el.get_text(strip=True) if el else ""


def parse_card(card):
    """从旧卡片的 soup 节点抽出渲染新卡片所需字段。"""
    title = _txt(card.select_one(".card-title"))
    if not title:
        return None
    # 平台
    tags_txt = card.select_one(".card-meta")
    platform = "unknown"
    meta_txt = _txt(tags_txt)
    has_pc = "PC" in meta_txt
    has_az = "安卓" in meta_txt
    if has_pc and has_az:
        platform = "pc_android"
    elif has_pc:
        platform = "pc"
    elif has_az:
        platform = "android"
    # 来源
    source = _txt(card.select_one(".tag-source"))
    # 日期（meta 里的 yyyy-mm-dd）
    m = re.search(r'\d{4}-\d{2}-\d{2}', meta_txt)
    post_date = m.group(0) if m else ""
    # likes
    m = re.search(r'LIKE\s*(\d+)', meta_txt)
    likes = int(m.group(1)) if m else 0
    # 网盘链接
    baidu_link = baidu_code = ""
    source_url = ""
    for a in card.select(".card-links a"):
        href = a.get("href", "")
        if "pan.baidu.com" in href:
            baidu_link = href
            cm = re.search(r'pwd=([A-Za-z0-9]+)', href)
            if cm:
                baidu_code = cm.group(1)
            # 也兼容文本里的 (xxxx) 提取码
            tm = re.search(r'\(([A-Za-z0-9]{4,})\)', _txt(a))
            if tm and not baidu_code:
                baidu_code = tm.group(1)
        elif a.get("class") and "link-source" in a.get("class"):
            source_url = href
    # 解压码 / 作弊码（可能在 footer 的 copy-text 按钮里）
    unzip_code = cheat_code = ""
    for btn in card.select("button.copy-text, button.btn-code"):
        dc = btn.get("data-copy", "")
        if dc.startswith("解压码") or "解压码" in dc:
            unzip_code = dc
        elif dc.startswith("作弊码") or "作弊码" in dc:
            cheat_code = dc
    # 备注
    note_body = card.select_one(".note-body")
    note_text = _txt(note_body)
    # 图片
    imgs = [im.get("src", "") for im in card.select(".card-imgs img")]

    return {
        "title": title,
        "platform": platform,
        "source": source,
        "post_date": post_date,
        "likes": likes,
        "baidu_link": baidu_link,
        "baidu_code": baidu_code,
        "source_url": source_url,
        "unzip_code": unzip_code,
        "cheat_code": cheat_code,
        "note": note_text,
        "imgs": imgs,
    }


def _norm_unzip(code):
    """解压码去冒号：'解压码:weslie' → '解压码weslie'"""
    if not code:
        return code
    return re.sub(r'(?<=解压码)\s*[:：]\s*', '', code)


def render_new_card(d):
    """用新版 CARD_TEMPLATE 渲染一张卡片（复用 generator 的样式类）。"""
    # 图片
    imgs_html = "".join(
        f'<img src="{im}" alt="" onerror="this.style.display=\'none\'">' for im in d["imgs"]
    ) or '<div class="no-img">暂无图片</div>'

    platform_tags = {
        "pc": '<span class="tag tag-pc">PC</span>',
        "android": '<span class="tag tag-android">安卓</span>',
        "pc_android": '<span class="tag tag-pc">PC</span> <span class="tag tag-android">安卓</span>',
        "unknown": '<span class="tag tag-pc">未知</span>',
    }
    platform_tag = platform_tags.get(d["platform"], platform_tags["unknown"])

    import html as html_lib
    links = []
    # 游戏名按钮（网盘名，带平台/大小）
    gname = game_name_from_title(d["title"])
    if gname:
        _gn = html_lib.escape(gname, quote=True)
        links.append(
            f'<button class="link-btn btn-game" data-copy="{_gn}" '
            f'title="点击复制网盘名：{_gn}" onclick="copyText(this)">游戏名</button>'
        )
    # 复制名称按钮（纯游戏名，发帖表单「游戏名称」栏用）
    bname = bare_name_from_title(d["title"])
    if bname:
        _bn = html_lib.escape(bname, quote=True)
        links.append(
            f'<button class="link-btn btn-bare" data-copy="{_bn}" '
            f'title="点击复制：{_bn}" onclick="copyText(this)">复制名称</button>'
        )
    # 百度网盘
    if d["baidu_link"]:
        code_suffix = f' ({d["baidu_code"]})' if d["baidu_code"] else ""
        links.append(
            f'<a href="{d["baidu_link"]}" class="link-btn link-baidu" target="_blank">'
            f'百度网盘{code_suffix}</a>'
        )
    # 原帖
    if d["source_url"]:
        links.append(
            f'<a href="{d["source_url"]}" class="link-btn link-source" target="_blank">原帖</a>'
        )
    # 解压码 / 作弊码
    if d["unzip_code"]:
        uc = _norm_unzip(d["unzip_code"])
        _uc = html_lib.escape(uc, quote=True)
        links.append(
            f'<button class="link-btn btn-code" data-copy="{_uc}" title="{_uc}" '
            f'onclick="copyText(this)">解压码</button>'
        )
    if d["cheat_code"]:
        cc = d["cheat_code"]
        _cc = html_lib.escape(cc, quote=True)
        links.append(
            f'<button class="link-btn btn-code" data-copy="{_cc}" title="{_cc}" '
            f'onclick="copyText(this)">作弊码</button>'
        )
    links_html = "\n".join(links)

    # 备注（原样保留，含 details 展开交互）
    note_html = ""
    if d["note"]:
        note_html = (
            '<div class="card-note">'
            '<div class="note-head"><span>备注</span><span class="note-copy-hint">点击复制</span></div>'
            f'<div class="note-body" data-copy="{html_lib.escape(d["note"], quote=True)}" '
            f'title="点击复制备注" onclick="copyNote(this)">{html_lib.escape(d["note"])}</div>'
            '</div>'
        )

    return generator.CARD_TEMPLATE.format(
        images_html=imgs_html,
        title=html_lib.escape(d["title"], quote=False),
        platform_tag=platform_tag,
        source=html_lib.escape(d["source"], quote=False),
        date=d["post_date"],
        likes=d["likes"],
        links=links_html,
        note=note_html,
        footer="",
    )


def convert(path):
    p = Path(path)
    if not p.exists():
        print(f"  跳过（不存在）: {p}")
        return 0
    soup = BeautifulSoup(p.read_text(encoding="utf-8"), "lxml")
    cards = soup.select("div.card")
    new_cards = []
    for c in cards:
        d = parse_card(c)
        if d:
            new_cards.append(render_new_card(d))
    print(f"  {p.name}: 解析 {len(cards)} 张，重建 {len(new_cards)} 张")
    if not APPLY:
        return len(new_cards)

    # 备份
    bak = p.with_suffix(".bak-旧版.html")
    if not bak.exists():
        shutil.copy2(str(p), str(bak))
        print(f"    已备份 → {bak.name}")

    # 整体重生成：用新版 HTML_TEMPLATE（含最新 CSS/JS），把卡片换掉
    orig = p.read_text(encoding="utf-8")
    # 标题、生成时间、总数从旧文件读
    ttl = soup.select_one(".header h1")
    title_txt = _txt(ttl) or "ACG游戏资源"
    meta_txt = _txt(soup.select_one(".header .meta"))
    gen_time = ""
    gm = re.search(r'生成时间:\s*([\d\- :]+)', meta_txt)
    if gm:
        gen_time = gm.group(1).strip()

    html = generator.HTML_TEMPLATE.format(
        title=title_txt,
        gen_time=gen_time or "",
        count=len(new_cards),
        cards="\n".join(new_cards),
    )
    p.write_text(html, encoding="utf-8")
    print(f"    已写入新卡片样式")
    return len(new_cards)


def main():
    total = 0
    for t in TARGETS:
        print(f"== {t}")
        total += convert(t)
    print(f"\n共处理 {total} 张卡片")
    if not APPLY:
        print(">>> 预演结束。确认无误后加 --apply 真改（自动备份 .bak-旧版.html）")


if __name__ == "__main__":
    main()

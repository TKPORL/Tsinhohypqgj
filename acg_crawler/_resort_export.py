"""把已导出的 HTML 按新排序规则原地重排（双网盘置顶 -> 点赞降序）。

不重新爬取、不重新生成，只调换已有卡片的顺序，图片/链接/样式全部原样保留。
排序键与 database.POST_ORDER_SQL 对齐：
    双网盘优先 -> 点赞降序 -> 原相对顺序（原文件已是 点赞降序, id倒序，稳定排序即等价于 id 倒序兜底）
"""
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

CARD_OPEN = '<div class="card">'
GRID_OPEN = '<div class="grid">'
GRID_BODY_END = '\n</div>\n<script>'

LIKES_RE = re.compile(r"<span>❤\s*(\d+)</span>")


def card_key(part):
    """(是否单网盘, 负点赞) —— 双网盘 0 排前，点赞高的排前"""
    is_dual = ('link-baidu' in part) and ('link-mobile' in part)
    m = LIKES_RE.search(part)
    likes = int(m.group(1)) if m else 0
    return (0 if is_dual else 1, -likes)


def reorder(path, dry=False):
    html = Path(path).read_text(encoding="utf-8")

    g = html.index(GRID_OPEN)
    head_end = g + len(GRID_OPEN)
    body_end = html.index(GRID_BODY_END, head_end)
    head = html[:head_end]
    body = html[head_end:body_end]
    tail = html[body_end:]

    if CARD_OPEN not in body:
        return {"file": path, "error": "未找到卡片"}

    chunks = body.split(CARD_OPEN)
    lead = chunks[0]
    cards = chunks[1:]

    before = [card_key(c) for c in cards]
    ordered = sorted(range(len(cards)), key=lambda i: before[i])  # 稳定排序
    new_cards = [cards[i] for i in ordered]
    after = [card_key(c) for c in new_cards]

    dual_n = sum(1 for k in after if k[0] == 0)
    single_n = len(after) - dual_n

    result = {
        "file": Path(path).name,
        "cards": len(cards),
        "dual": dual_n,
        "single": single_n,
        "already_ordered": before == after,
        "unchanged_multiset": sorted(before) == sorted(after),
    }

    # 顶部应全是双网盘；边界检查
    if dual_n and single_n:
        result["boundary_ok"] = (after[dual_n - 1][0] == 0 and after[dual_n][0] == 1)
        result["top5_dual"] = [k for k in after[:5]]
        if dual_n and single_n:
            result["dual_min_likes"] = -max(k[1] for k in after[:dual_n])
            result["single_max_likes"] = -min(k[1] for k in after[dual_n:])

    if dry:
        return result

    # 备份原件
    p = Path(path)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = p.with_name(p.stem + "_原始顺序备份" + p.suffix)
    if not backup.exists():
        shutil.copy2(p, backup)
    result["backup"] = backup.name

    new_html = head + lead + CARD_OPEN.join([""] + new_cards) + tail
    p.write_text(new_html, encoding="utf-8")
    result["bytes_before"] = len(html)
    result["bytes_after"] = len(new_html)
    return result


if __name__ == "__main__":
    targets = [
        r"D:\下载目录\PC下载-ACG图书馆-ACG游戏姬-萌幻ACG-20260920-095235\PC下载-ACG图书馆-ACG游戏姬-萌幻ACG-20260920-095235.html",
        r"D:\下载目录\PC+安卓下载-ACG俱乐部-ACG图书馆-ACG游戏姬-萌幻ACG-20260920-095333\PC+安卓下载-ACG俱乐部-ACG图书馆-ACG游戏姬-萌幻ACG-20260920-095333.html",
    ]
    dry = "--dry" in sys.argv
    for t in targets:
        if not Path(t).exists():
            print("跳过（不存在）:", t)
            continue
        r = reorder(t, dry=dry)
        print("----", r.get("file"))
        for k in ("cards", "dual", "single", "already_ordered", "unchanged_multiset",
                  "boundary_ok", "dual_min_likes", "single_max_likes", "backup",
                  "bytes_before", "bytes_after", "error"):
            if k in r:
                print("   %-20s %s" % (k, r[k]))

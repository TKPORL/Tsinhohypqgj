# -*- coding: utf-8 -*-
"""鲲Galgame 标题套娃括号拆平（2026-09-26）

现象：资源自带标题里已带【】，拼装时又包了一层，出现套娃：
    乐园的罗蕾莱 【PC+安卓】【【PC】简体中文】
拆平后：
    乐园的罗蕾莱 【PC+安卓】【PC】【简体中文】

只处理"平台括号之后紧跟 【【...】...】 套娃段"的标题，其它一律不动。

用法：
    python _migrate_kungal_flatten.py          # 预演
    python _migrate_kungal_flatten.py --apply  # 真改（自动备份）
"""
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "data" / "crawler.db"
sys.path.insert(0, str(BASE))

from crawler.kungal import _flatten_res_title  # noqa: E402

APPLY = "--apply" in sys.argv


def rebuild(old):
    """把 `游戏名 【平台】【【内层】尾巴】` 拆成 `游戏名 【平台】【内层】【尾巴】`。"""
    if not old:
        return old
    m = re.match(r'^(?P<name>.+?)\s*(?P<plat>【[^【】]+】)(?P<tail>.*)$', old)
    if not m:
        return old
    name = m.group("name").rstrip()
    plat = m.group("plat")
    tail = m.group("tail").strip()
    if not tail or not tail.startswith("【【"):
        return old
    extra = _flatten_res_title(tail)
    if not extra:
        return old
    return f"{name} {plat}" + "".join(f"【{x}】" for x in extra)


def main():
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, title FROM posts WHERE source = '鲲Galgame'").fetchall()
    print(f"鲲Galgame 共 {len(rows)} 条")

    changes = []
    for r in rows:
        n = rebuild(r["title"] or "")
        if n != r["title"]:
            changes.append((r["id"], r["title"], n))

    print(f"  套娃标题要改 {len(changes)} 条\n")
    for pid, old, new in changes[:12]:
        print(f"  旧: {old}")
        print(f"  新: {new}\n")

    if not APPLY:
        print(">>> 预演结束。确认无误后加 --apply 真改（会自动备份数据库）")
        return

    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = DB.parent / f"crawler.db.bak-kungal-flatten-{ts}"
    shutil.copy2(str(DB), str(bak))
    print(f"已备份: {bak}")

    cur = conn.cursor()
    for pid, old, new in changes:
        cur.execute("UPDATE posts SET title = ? WHERE id = ?", (new, pid))
    conn.commit()
    conn.close()
    print(f"完成：标题改 {len(changes)} 条")


if __name__ == "__main__":
    main()

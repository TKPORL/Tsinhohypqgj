# -*- coding: utf-8 -*-
"""旧数据迁移（2026-09-26 用户确认：直接批量改）

修三类历史数据：
1. unzip_code 统一成「解压码xxx」无冒号格式
     '007721'                → '解压码007721'
     '解压码:0721'           → '解压码0721'
     'PC解压码:A ｜ 安卓解压码:B' → 'PC解压码A ｜ 安卓解压码B'
     '百度网盘 xxx'          → '解压码xxx'（老多网盘时代残留）
2. title 走一遍 normalize_title：标签归拢、括号合并、数字位次、云名去前缀
3. 标题体积超过 10G 的，按用户口径**直接删除**（不再留在库里）

用法：
    python _migrate_20260926.py          # 预演，只打印改动，不写库
    python _migrate_20260926.py --apply  # 真改（自动先备份）
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

from parser import normalize_title, oversize_reason  # noqa: E402

APPLY = "--apply" in sys.argv


def fix_unzip(code):
    """把各种历史写法归一成「解压码xxx」无冒号。

    返回 (新值, 是否改变)。无法识别/本身已合规的返回原值。
    """
    if not code:
        return code, False
    s = str(code).strip()
    if not s:
        return code, False

    # 多条：PC解压码:X ｜ 安卓解压码:Y  → 去掉冒号
    if "｜" in s or "|" in s:
        parts = [p.strip() for p in re.split(r'[｜|]', s)]
        out = []
        for p in parts:
            if not p:
                continue
            p = re.sub(r'^(PC|安卓|百度网盘|移动云盘)?解压码\s*[:：]\s*', lambda m: (m.group(1) + "解压码") if m.group(1) else "解压码", p)
            if not p.startswith(("解压码", "PC解压码", "安卓解压码")):
                p = "解压码" + p
            out.append(p)
        new = " ｜ ".join(out)
        return (new, new != s)

    # 单条带冒号
    m = re.match(r'^(PC|安卓)?解压码\s*[:：]\s*(.+)$', s)
    if m:
        new = f"{m.group(1) or ''}解压码{m.group(2).strip()}"
        return (new, new != s)

    # 老多网盘前缀残留：'百度网盘 xxx' / '移动云盘 xxx'
    m = re.match(r'^(?:百度网盘|移动云盘|百度云|移动云)\s+(.+)$', s)
    if m:
        new = "解压码" + m.group(1).strip()
        return (new, new != s)

    # 已是合规格式
    if re.match(r'^(PC|安卓)?解压码\S', s):
        return (s, False)

    # 纯码 → 补前缀
    new = "解压码" + s
    return (new, True)


def main():
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, source, title, unzip_code FROM posts").fetchall()
    print(f"共 {len(rows)} 条帖子")

    unzip_changes = []
    title_changes = []
    delete_ids = []

    for r in rows:
        # 解压码
        new_unzip, changed = fix_unzip(r["unzip_code"])
        if changed:
            unzip_changes.append((r["id"], r["unzip_code"], new_unzip))

        # 标题
        old_title = r["title"] or ""
        new_title = normalize_title(old_title)
        if new_title != old_title:
            title_changes.append((r["id"], r["source"], old_title, new_title))

        # 超 10G 直接删
        if oversize_reason(new_title):
            delete_ids.append((r["id"], r["source"], new_title))

    print(f"  解压码要改 {len(unzip_changes)} 条")
    print(f"  标题要改 {len(title_changes)} 条")
    print(f"  体积超 10G 要删 {len(delete_ids)} 条")

    print("\n--- 解压码样例（最多8条）---")
    for pid, old, new in unzip_changes[:8]:
        print(f"  {old!r} → {new!r}")

    print("\n--- 标题样例（最多8条）---")
    for pid, src, old, new in title_changes[:8]:
        print(f"  [{src}]")
        print(f"    前: {old[:110]}")
        print(f"    后: {new[:110]}")

    print("\n--- 将删除（超10G，最多8条）---")
    for pid, src, t in delete_ids[:8]:
        print(f"  [{src}] {t[:110]}")

    if not APPLY:
        print("\n>>> 预演结束。确认无误后加 --apply 真改（会自动备份数据库）")
        return

    # 备份
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = DB.parent / f"crawler.db.bak-migrate-{ts}"
    shutil.copy2(str(DB), str(bak))
    print(f"\n已备份: {bak}")

    cur = conn.cursor()
    for pid, old, new in unzip_changes:
        cur.execute("UPDATE posts SET unzip_code = ? WHERE id = ?", (new, pid))
    for pid, src, old, new in title_changes:
        cur.execute("UPDATE posts SET title = ? WHERE id = ?", (new, pid))
    if delete_ids:
        ids = [d[0] for d in delete_ids]
        cur.executemany("DELETE FROM posts WHERE id = ?", [(i,) for i in ids])
    conn.commit()
    conn.close()
    print(f"完成：解压码改 {len(unzip_changes)}，标题改 {len(title_changes)}，删除 {len(delete_ids)}")


if __name__ == "__main__":
    main()

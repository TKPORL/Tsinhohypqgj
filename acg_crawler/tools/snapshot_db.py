#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库安全快照：把 crawler.db 复制到一个"不会被误删"的地方。

为什么需要它：
  两个备份系统（主仓库 D:/Tsinho文件夹/新Tsinho黄油爬取工具 和
  D:/my-backup）都在 .gitignore 里排除了 *.db，
  注释甚至写着 "NEVER back up live DB files"。
  结果是：crawler.db 在整个电脑上只存在过一份。
  2026-09-26 事故中它被 robocopy /MIR 删掉，只能靠"早期误提交过一次"的
  git 对象侥幸找回。不能依赖这种运气。

做法：
  1. 用 sqlite3 的 backup() API 生成一致性快照（即使 WAL 有未落盘内容也安全）
  2. **扩展名用 .dbbak**，故意避开 `**/*.db` 排除规则（万一将来要上 git 也能上）
  3. 快照存两处，**故意分在两个物理盘**（C 盘和 D 盘），一块盘坏了另一块还在：
     - D 盘项目内：acg_crawler/data/_safe_backup/
     - C 盘项目外：C:\\Tsinho_DB_Snapshots\\
  4. 每处只保留最近 KEEP 份，旧的自动删
     （只删本脚本自己生成的 crawler-YYYYmmdd-HHMMSS.dbbak，绝不动别的文件）

运行：C:/Python314/python.exe acg_crawler/tools/snapshot_db.py
"""
import os
import re
import sqlite3
import datetime

# ---- 路径（写死，不用通配符）----
PROJ = r"D:\Tsinho文件夹\新Tsinho黄油爬取工具"
SRC = os.path.join(PROJ, "acg_crawler", "data", "crawler.db")
SNAP_D = os.path.join(PROJ, "acg_crawler", "data", "_safe_backup")
SNAP_C = r"C:\Tsinho_DB_Snapshots"
DIRS = [SNAP_D, SNAP_C]
LOG = os.path.join(SNAP_D, "snapshot.log")
KEEP = 14  # 每处保留最近 N 份

# 扩展名故意用 .dbbak：避开备份系统 `**/*.db` 排除规则
NAME_RE = re.compile(r"^crawler-(\d{8}-\d{6})\.dbbak$")


def log(msg):
    """同时打印到屏幕并追加到日志文件（日志写失败不影响主流程）。"""
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def main():
    if not os.path.isfile(SRC):
        log(f"[错误] 找不到数据库: {SRC}")
        return 1

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    fname = f"crawler-{ts}.dbbak"

    # 用 backup API 做一致性快照
    # 临时文件用固定名，每轮复用覆盖（不用随机名，避免残留垃圾要清理）
    tmp = os.path.join(os.path.dirname(SRC), ".snap-tmp.dbbak")
    if os.path.exists(tmp):
        os.remove(tmp)
    src_conn = sqlite3.connect(SRC)
    dst_conn = sqlite3.connect(tmp)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()

    size_mb = os.path.getsize(tmp) / 1024 / 1024
    n_posts = sqlite3.connect(tmp).execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    log(f"[快照] {fname}  {size_mb:.1f} MB  {n_posts} 帖")

    for d in DIRS:
        os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, fname)
        with open(tmp, "rb") as fi, open(dst, "wb") as fo:
            fo.write(fi.read())
        log(f"  已存 -> {dst}")

        # 清理旧快照：只删本目录下匹配 crawler-YYYYmmdd-HHMMSS.dbbak 的
        snaps = sorted(
            f for f in os.listdir(d) if NAME_RE.match(f)
        )
        for old in snaps[:-KEEP]:
            p = os.path.join(d, old)
            os.remove(p)
            log(f"  清旧 -> {p}")

    # 临时文件不删，留在原地下轮覆盖（避免触碰删除逻辑）
    log("[完成]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

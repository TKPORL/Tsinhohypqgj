# -*- coding: utf-8 -*-
"""把【变更记录】修改日志.md 的老条目切到 docs/历史方案/变更日志-归档.md
边界：归档从 "## 2026-09-24 v18 " 起，到 "## 2026-09-26 (16:00) " 前止。
主文件保留 [开头 .. v18前] + [09-26 16:00 .. 末尾]。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MAIN = os.path.join(ROOT, "【变更记录】修改日志.md")
ARCH = os.path.join(ROOT, "docs", "历史方案", "变更日志-归档.md")

START_MARK = "## 2026-09-24 v18 "
END_MARK = "## 2026-09-26 (16:00) "

with io.open(MAIN, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 定位
si = ei = None
for i, ln in enumerate(lines):
    if si is None and ln.startswith(START_MARK):
        si = i
    if si is not None and ln.startswith(END_MARK):
        ei = i
        break

assert si is not None, "找不到起始标记"
assert ei is not None, "找不到结束标记"
assert si < ei, "边界顺序错误"

head = lines[:si]          # 开头：格式约定 + 索引表 + v20 + v19
tail = lines[ei:]          # 末尾：09-26 16:00 及以后
mid = lines[si:ei]         # 归档块

# 去掉归档块尾部多余的横线/空行（保留内容原样，仅清理连续分隔）
while mid and mid[-1].strip() in ("", "---"):
    mid.pop()

print("归档块: 行 %d..%d  共 %d 行" % (si + 1, ei, len(mid)))
print("主文件保留: 开头 %d 行 + 末尾 %d 行 = %d 行" % (len(head), len(tail), len(head) + len(tail)))

arch_header = [
    "# 【变更记录】修改日志 · 归档\n",
    "\n",
    "本文件保存 v18 及更早（2026-09-23 ~ 2026-09-25）的历史变更条目，\n",
    "从主文件 `【变更记录】修改日志.md` 中拆出，仅为控制主文件体积、避免编辑卡顿。\n",
    "内容一字未改，主文件索引表仍保留全部版本的检索入口。\n",
    "\n",
    "---\n",
    "\n",
]

arch_body = arch_header + mid + ["\n"]

with io.open(ARCH, "w", encoding="utf-8", newline="") as f:
    f.writelines(arch_body)

with io.open(MAIN, "w", encoding="utf-8", newline="") as f:
    f.writelines(head + tail)

# 校验：内容无丢失
joined = "".join(head + tail) + "".join(mid)
orig = "".join(lines)
# 忽略我们主动 trim 掉的尾部空白行
print("原文件字符数: %d" % len(orig))
print("合并后字符数: %d" % len(joined))
print("差(应为 trim 掉的空行): %d" % (len(orig) - len(joined)))
print("主文件行数: %d" % len(head + tail))
print("归档行数: %d" % len(arch_body))

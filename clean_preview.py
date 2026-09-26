# -*- coding: utf-8 -*-
import os, sys

BASE = r'D:\Tsinho 文件夹\新 Tsinho 黄油爬取工具'
sys.path.insert(0, os.path.join(BASE, 'acg_crawler'))

import generator
from database import get_posts

# 获取所有鲲 Galgame 帖子（从之前重爬的结果）
posts = get_posts(source="鲲 Galgame", platform="all", limit=100000)
print(f"总共 {len(posts)} 条鲲 Galgame")

# 过滤掉 NSFW 露点的游戏
clean = [p for p in posts if 
    'Role player' not in (p.get('title') or '') and 
    '小粥' not in (p.get('title') or '') and
    '山掛' not in (p.get('title') or '') and
    '伊仓' not in (p.get('title') or '')]

print(f"干净的游戏：{len(clean)} 条")

# 按点赞排序，选 8 条
clean.sort(key=lambda p: -(p.get('likes') or 0))
sel = clean[:8]

print("\n选择的 8 条:")
for i, p in enumerate(sel):
    print(f"{i+1}. {(p['title'] or '')[:60]}... | likes:{p.get('likes')} | plat:{p.get('platform')}")

# 生成
path = generator.generate_html(sel, "备注清洗效果 - 干净版", "预览 - 干净.html")
print(f"\n生成：{path}")

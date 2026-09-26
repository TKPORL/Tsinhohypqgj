# -*- coding: utf-8 -*-
"""生成干净的预览（去掉 Role player 那些露的游戏）"""
import os
import sys

# 用脚本自身位置定位，不再硬编码绝对路径
# （此前硬编码成带空格的错路径 "D:/Tsinho 文件夹/新 Tsinho ..."，是路径事故残留）
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)

import generator
from database import get_posts

# 获取所有鲲Galgame帖子（注意来源名无空格）
posts = get_posts(source="鲲Galgame", platform="all", limit=100000)
print(f"总共 {len(posts)} 条鲲Galgame数据")

# 过滤掉标题含敏感词的（NSFW 露点游戏）
clean_posts = [p for p in posts if 
    'Role player' not in (p.get('title') or '') and 
    '小粥' not in (p.get('title') or '') and
    '山掛' not in (p.get('title') or '') and
    '伊仓' not in (p.get('title') or '')]

print(f"干净的游戏：{len(clean_posts)} 条")

# 按点赞数排序，选前 8 条（包含不同平台的）
clean_posts.sort(key=lambda p: -(p.get('likes') or 0))
sel = clean_posts[:8]

print("\n选择的游戏：")
for i, p in enumerate(sel):
    tid = (p['title'] or '')[:50]
    likes = p.get('likes', 0)
    plat = p.get('platform', 'unknown')
    print(f"{i+1}. {tid}... | 点赞:{likes} | 平台:{plat}")

# 生成 HTML
path = generator.generate_html(sel, "备注清洗效果预览 - 干净版", "预览 - 干净.html")
print(f"\n已生成：output/预览 - 干净/预览 - 干净.html")
print(f"大小：{os.path.getsize(path)} 字节")

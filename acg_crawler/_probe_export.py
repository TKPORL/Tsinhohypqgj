# -*- coding: utf-8 -*-
"""临时探针：复现 /api/export_batch 的 500 错误，抓完整堆栈"""
import sys, traceback
sys.path.insert(0, '.')

import app as flask_app
from database import get_posts_by_crawl_id
from generator import export_posts

crawl_id, platform = 70, "all"
try:
    posts = get_posts_by_crawl_id(crawl_id, platform)
    print('posts:', len(posts) if posts else posts)
    if posts:
        sources = sorted({p.get("source", "") for p in posts if p.get("source")})
        tag = "-".join(sources) if sources else "batch%d" % crawl_id
        print('tag:', tag)
        result = export_posts(posts, name_suffix=tag)
        print('result keys:', {k: v for k, v in result.items()})
except Exception:
    traceback.print_exc()

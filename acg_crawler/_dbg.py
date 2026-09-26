import sys, io, os, shutil, urllib.parse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

shutil.copy('data/crawler.db', 'data/_t7.db')
import database
from pathlib import Path
database.DB_PATH = Path('data/_t7.db')
from database import init_db, get_posts_by_crawl_id
init_db()
posts = get_posts_by_crawl_id(42, 'pc_android')
print('批次42 pc_android 帖子数:', len(posts))
sources = sorted({p.get('source', '') for p in posts if p.get('source')})
print('来源集合:', sources)

from app import app
client = app.test_client()
r = client.get('/api/export_batch?crawl_id=42&platform=pc_android')
print('状态:', r.status_code)
print('完整Content-Disposition:', repr(r.headers.get('Content-Disposition', '')))
print('大小:', len(r.data)//1024, 'KB')
os.remove('data/_t7.db')

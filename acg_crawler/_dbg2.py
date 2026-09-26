import sys, io, os, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
shutil.copy('data/crawler.db', 'data/_t8.db')
import database
from pathlib import Path
database.DB_PATH = Path('data/_t8.db')
from database import init_db, get_posts_by_crawl_id
init_db()
for plat in ['pc_android', 'pc', 'all']:
    n = len(get_posts_by_crawl_id(42, plat))
    print(f'批次42 platform={plat}: {n} 条')
# 直接查platform分布
import sqlite3
conn = sqlite3.connect('data/_t8.db')
for r in conn.execute("SELECT platform, COUNT(*) FROM posts WHERE crawl_id=42 GROUP BY platform").fetchall():
    print('  ', r)
os.remove('data/_t8.db')

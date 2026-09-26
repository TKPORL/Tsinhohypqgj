import sys, io, sqlite3, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
conn = sqlite3.connect(r'data\crawler.db')
print('批次42平台分布:')
for r in conn.execute("SELECT platform, COUNT(*) FROM posts WHERE crawl_id=42 GROUP BY platform").fetchall():
    print('  ', r)
print()
print('各批次crawl_id:')
for r in conn.execute("SELECT crawl_id, COUNT(*) FROM posts GROUP BY crawl_id").fetchall():
    print('  ', r)
conn.close()
os.remove(r'data\_t8.db') if os.path.exists(r'data\_t8.db') else None

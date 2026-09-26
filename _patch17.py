#!/usr/bin/env python
"""
一键部署 v4.2.6-v4.2.7 改进
- 创建 posts 表索引（加速浏览/分页/统计）
- 显示 5.6GB 磁盘占用分析
"""
import sqlite3, sys
from pathlib import Path

DB_PATH = Path(__file__).parent / 'acg_crawler' / 'data' / 'posts.db'

def main():
    print('=' * 50)
    print('  v4.2.7 数据库优化 + 磁盘分析')
    print('=' * 50)
    print()

    # 1. 数据库索引
    if not DB_PATH.exists():
        print(f'[跳过] 数据库不存在: {DB_PATH}')
    else:
        print('[1/2] 创建性能索引...')
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute('CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_posts_date ON posts(post_date)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_posts_crawl_id ON posts(crawl_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_posts_source_url ON posts(source_url)')
        conn.commit()
        conn.close()
        print('      ✓ 6 个索引已创建')

    # 2. 磁盘分析
    print()
    print('[2/2] 磁盘占用分析...')
    base = Path(__file__).parent / 'acg_crawler'

    total = 0
    for name in ['images', 'data', 'output']:
        d = base / name
        if not d.exists():
            continue
        size = sum(f.stat().st_size for f in d.rglob('*') if f.is_file())
        count = sum(1 for _ in d.rglob('*') if _.is_file())
        total += size
        unit = 'GB' if size >= 1024**3 else 'MB'
        val = size / (1024**3 if unit == 'GB' else 1024**2)
        print(f'      {name:10s}: {val:6.1f} {unit:>2s}  ({count} 个文件)')

    # 输出可能的移动路径
    output_dir = base / 'output'
    if output_dir.exists():
        out_size = sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file())
        if out_size > 1024**3:
            print()
            print(f'  提示: output/ 占用 {out_size/1024**3:.1f} GB')
            print(f'  可移动到其他磁盘后用软链接替代，释放大量空间')

    print()
    print(f'  总计: {total/1024**3:.2f} GB')
    print()
    print('完成！重启应用即可生效。')

if __name__ == '__main__':
    main()

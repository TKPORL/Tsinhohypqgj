"""数据库模块"""
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / "data" / "crawler.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                source_url TEXT NOT NULL,
                title TEXT NOT NULL,
                platform TEXT DEFAULT 'unknown',
                content TEXT,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                unzip_code TEXT,
                cheat_code TEXT,
                baidu_link TEXT,
                baidu_code TEXT,
                mobile_link TEXT,
                mobile_code TEXT,
                images TEXT,
                original_images TEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                post_date TEXT,
                UNIQUE(source, source_id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                params TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                sites TEXT,
                total_posts INTEGER DEFAULT 0,
                success_posts INTEGER DEFAULT 0,
                skipped_posts INTEGER DEFAULT 0,
                error_posts INTEGER DEFAULT 0,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source);
            CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);
            CREATE INDEX IF NOT EXISTS idx_posts_date ON posts(post_date);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        """)

@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def insert_post(post_data):
    # 使用本地时间（UTC+8）
    local_now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO posts
            (source, source_id, source_url, title, platform, content,
             likes, comments, views, unzip_code, cheat_code,
             baidu_link, baidu_code, mobile_link, mobile_code,
             images, original_images, post_date, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post_data.get("source"),
            post_data.get("source_id"),
            post_data.get("source_url"),
            post_data.get("title"),
            post_data.get("platform", "unknown"),
            post_data.get("content"),
            post_data.get("likes", 0),
            post_data.get("comments", 0),
            post_data.get("views", 0),
            post_data.get("unzip_code"),
            post_data.get("cheat_code"),
            post_data.get("baidu_link"),
            post_data.get("baidu_code"),
            post_data.get("mobile_link"),
            post_data.get("mobile_code"),
            post_data.get("images"),
            post_data.get("original_images"),
            post_data.get("post_date"),
            local_now,
        ))

def get_posts(platform=None, source=None, limit=100, offset=0):
    with get_conn() as conn:
        query = "SELECT * FROM posts WHERE 1=1"
        params = []
        if platform and platform != "all":
            if platform == "pc":
                query += " AND (platform = 'pc' OR platform = 'unknown')"
            elif platform == "pc_android":
                query += " AND platform = 'pc_android'"
            elif platform == "android":
                query += " AND platform = 'android'"
            else:
                query += " AND platform = ?"
                params.append(platform)
        if source and source != "all":
            query += " AND source = ?"
            params.append(source)
        query += """ ORDER BY
            (CASE WHEN baidu_link IS NOT NULL AND mobile_link IS NOT NULL THEN 0 ELSE 1 END),
            (CASE source
                WHEN 'ACG游戏姬' THEN 1
                WHEN 'ACG图书馆' THEN 2
                WHEN 'ACG俱乐部' THEN 3
                WHEN '萌幻ACG' THEN 4
                ELSE 5
            END),
            likes DESC
            LIMIT ? OFFSET ?"""
        params.extend([limit, offset])
        return [dict(row) for row in conn.execute(query, params).fetchall()]

def get_post_count(platform=None, source=None):
    with get_conn() as conn:
        query = "SELECT COUNT(*) FROM posts WHERE 1=1"
        params = []
        if platform and platform != "all":
            if platform == "pc":
                query += " AND (platform = 'pc' OR platform = 'unknown')"
            elif platform == "pc_android":
                query += " AND platform = 'pc_android'"
            elif platform == "android":
                query += " AND platform = 'android'"
            else:
                query += " AND platform = ?"
                params.append(platform)
        if source and source != "all":
            query += " AND source = ?"
            params.append(source)
        return conn.execute(query, params).fetchone()[0]

def delete_post(post_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))

def delete_task(task_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

def create_task(task_type, params, sites):
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (task_type, params, sites) VALUES (?, ?, ?)",
            (task_type, params, sites)
        )
        return cursor.lastrowid

def update_task(task_id, **kwargs):
    with get_conn() as conn:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [task_id]
        conn.execute(f"UPDATE tasks SET {sets} WHERE id = ?", values)

def get_tasks(limit=20):
    with get_conn() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]

def get_task(task_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

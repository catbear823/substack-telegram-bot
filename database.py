import libsql_experimental as libsql
import json
from datetime import datetime
from typing import Optional

from config import TURSO_DATABASE_URL, TURSO_AUTH_TOKEN


_connection = None


def _get_connection():
    global _connection
    if _connection is None:
        if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
            _connection = libsql.connect(
                database=TURSO_DATABASE_URL,
                auth_token=TURSO_AUTH_TOKEN,
            )
        else:
            _connection = libsql.connect(database="bot_data.db")
    return _connection


async def init_db():
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            title TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, url)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_url TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            author TEXT,
            published_at TEXT,
            content TEXT,
            summary TEXT,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            chat_id INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            article_ids TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shared_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_chat_id INTEGER NOT NULL,
            share_code TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_chat ON articles(chat_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_feed ON articles(feed_url)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_content ON articles(title, content)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shared_code ON shared_feeds(share_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shared_owner ON shared_feeds(owner_chat_id)")
    conn.commit()


async def add_feed(chat_id: int, url: str, title: str = "") -> bool:
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO feeds (chat_id, url, title) VALUES (?, ?, ?)",
            (chat_id, url, title),
        )
        conn.commit()
        return True
    except Exception:
        return False


async def remove_feed(chat_id: int, url: str) -> bool:
    conn = _get_connection()
    cursor = conn.execute(
        "DELETE FROM feeds WHERE chat_id = ? AND url = ?", (chat_id, url)
    )
    conn.commit()
    return cursor.rowcount > 0


async def get_feeds(chat_id: int) -> list[dict]:
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT * FROM feeds WHERE chat_id = ? ORDER BY added_at DESC",
        (chat_id,),
    )
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    return [dict(zip(columns, row)) for row in rows]


async def add_article(
    chat_id: int,
    feed_url: str,
    title: str,
    url: str,
    author: str = "",
    published_at: str = "",
    content: str = "",
) -> Optional[int]:
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO articles
               (chat_id, feed_url, title, url, author, published_at, content)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (chat_id, feed_url, title, url, author, published_at, content),
        )
        conn.commit()
        return cursor.lastrowid
    except Exception:
        return None


async def update_article_summary(article_id: int, summary: str):
    conn = _get_connection()
    conn.execute(
        "UPDATE articles SET summary = ? WHERE id = ?", (summary, article_id)
    )
    conn.commit()


async def get_articles(
    chat_id: int, limit: int = 20, with_summary: bool = False
) -> list[dict]:
    conn = _get_connection()
    query = "SELECT * FROM articles WHERE chat_id = ?"
    if with_summary:
        query += " AND summary IS NOT NULL"
    query += " ORDER BY fetched_at DESC LIMIT ?"
    cursor = conn.execute(query, (chat_id, limit))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    return [dict(zip(columns, row)) for row in rows]


async def get_article_by_id(article_id: int) -> Optional[dict]:
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT * FROM articles WHERE id = ?", (article_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    return dict(zip(columns, row))


async def search_articles(chat_id: int, query: str, limit: int = 5) -> list[dict]:
    conn = _get_connection()
    search_term = f"%{query}%"
    cursor = conn.execute(
        """SELECT *, 
                  (CASE WHEN title LIKE ? THEN 10 ELSE 0 END) +
                  (CASE WHEN content LIKE ? THEN 5 ELSE 0 END) +
                  (CASE WHEN summary LIKE ? THEN 3 ELSE 0 END) AS relevance
           FROM articles
           WHERE chat_id = ? AND (title LIKE ? OR content LIKE ? OR summary LIKE ?)
           ORDER BY relevance DESC, fetched_at DESC
           LIMIT ?""",
        (
            search_term,
            search_term,
            search_term,
            chat_id,
            search_term,
            search_term,
            search_term,
            limit,
        ),
    )
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    return [dict(zip(columns, row)) for row in rows]


async def add_conversation(chat_id: int, role: str, message: str, article_ids: str = ""):
    conn = _get_connection()
    conn.execute(
        "INSERT INTO conversation_history (chat_id, role, message, article_ids) VALUES (?, ?, ?, ?)",
        (chat_id, role, message, article_ids),
    )
    conn.commit()


async def get_conversation_history(chat_id: int, limit: int = 10) -> list[dict]:
    conn = _get_connection()
    cursor = conn.execute(
        """SELECT * FROM conversation_history 
           WHERE chat_id = ? 
           ORDER BY timestamp DESC LIMIT ?""",
        (chat_id, limit),
    )
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    result = [dict(zip(columns, row)) for row in reversed(rows)]
    return result


async def article_exists(url: str) -> bool:
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT 1 FROM articles WHERE url = ?", (url,)
    )
    return cursor.fetchone() is not None


async def get_article_count(chat_id: int) -> int:
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE chat_id = ?", (chat_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else 0


async def get_articles_by_feed(chat_id: int, feed_url: str, limit: int = 20, offset: int = 0) -> list[dict]:
    conn = _get_connection()
    cursor = conn.execute(
        """SELECT * FROM articles 
           WHERE chat_id = ? AND feed_url = ? 
           ORDER BY published_at DESC LIMIT ? OFFSET ?""",
        (chat_id, feed_url, limit, offset),
    )
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    return [dict(zip(columns, row)) for row in rows]


async def get_articles_by_feed_count(chat_id: int, feed_url: str) -> int:
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE chat_id = ? AND feed_url = ?",
        (chat_id, feed_url),
    )
    row = cursor.fetchone()
    return row[0] if row else 0


async def get_feed_title(chat_id: int, feed_url: str) -> str:
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT title FROM feeds WHERE chat_id = ? AND url = ?",
        (chat_id, feed_url),
    )
    row = cursor.fetchone()
    return row[0] if row else feed_url.split("//")[-1].split(".")[0]


async def get_shared_feeds(owner_chat_id: int) -> Optional[dict]:
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT * FROM shared_feeds WHERE owner_chat_id = ?", (owner_chat_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    return dict(zip(columns, row))


async def create_shared_feed(owner_chat_id: int, share_code: str) -> bool:
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO shared_feeds (owner_chat_id, share_code) VALUES (?, ?)",
            (owner_chat_id, share_code),
        )
        conn.commit()
        return True
    except Exception:
        return False


async def get_owner_by_share_code(share_code: str) -> Optional[int]:
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT owner_chat_id FROM shared_feeds WHERE share_code = ?", (share_code,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


async def remove_shared_feed(owner_chat_id: int) -> bool:
    conn = _get_connection()
    cursor = conn.execute(
        "DELETE FROM shared_feeds WHERE owner_chat_id = ?", (owner_chat_id,)
    )
    conn.commit()
    return cursor.rowcount > 0

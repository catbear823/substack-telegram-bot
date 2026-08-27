import libsql_experimental as libsql
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
        CREATE TABLE IF NOT EXISTS shared_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_chat_id INTEGER NOT NULL,
            share_code TEXT UNIQUE NOT NULL,
            max_uses INTEGER DEFAULT 0,
            use_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_feeds_chat ON feeds(chat_id)")
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


async def create_shared_feed(owner_chat_id: int, share_code: str, max_uses: int = 0) -> bool:
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO shared_feeds (owner_chat_id, share_code, max_uses) VALUES (?, ?, ?)",
            (owner_chat_id, share_code, max_uses),
        )
        conn.commit()
        return True
    except Exception:
        return False


async def get_owner_by_share_code(share_code: str) -> Optional[int]:
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT owner_chat_id, max_uses, use_count FROM shared_feeds WHERE share_code = ?",
        (share_code,),
    )
    row = cursor.fetchone()
    if not row:
        return None

    owner_chat_id, max_uses, use_count = row

    if max_uses > 0 and use_count >= max_uses:
        return None

    conn.execute(
        "UPDATE shared_feeds SET use_count = use_count + 1 WHERE share_code = ?",
        (share_code,),
    )
    conn.commit()

    return owner_chat_id


async def remove_shared_feed(owner_chat_id: int) -> bool:
    conn = _get_connection()
    cursor = conn.execute(
        "DELETE FROM shared_feeds WHERE owner_chat_id = ?", (owner_chat_id,)
    )
    conn.commit()
    return cursor.rowcount > 0

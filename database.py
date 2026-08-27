import aiosqlite
import json
from datetime import datetime
from typing import Optional

from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, url)
            )
        """)
        await db.execute("""
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                article_ids TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_chat ON articles(chat_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_feed ON articles(feed_url)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_content ON articles(title, content)
        """)
        await db.commit()


async def add_feed(chat_id: int, url: str, title: str = "") -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO feeds (chat_id, url, title) VALUES (?, ?, ?)",
                (chat_id, url, title),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_feed(chat_id: int, url: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM feeds WHERE chat_id = ? AND url = ?", (chat_id, url)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_feeds(chat_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM feeds WHERE chat_id = ? ORDER BY added_at DESC",
            (chat_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def add_article(
    chat_id: int,
    feed_url: str,
    title: str,
    url: str,
    author: str = "",
    published_at: str = "",
    content: str = "",
) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            cursor = await db.execute(
                """INSERT OR IGNORE INTO articles
                   (chat_id, feed_url, title, url, author, published_at, content)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (chat_id, feed_url, title, url, author, published_at, content),
            )
            await db.commit()
            return cursor.lastrowid
        except Exception:
            return None


async def update_article_summary(article_id: int, summary: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE articles SET summary = ? WHERE id = ?", (summary, article_id)
        )
        await db.commit()


async def get_articles(
    chat_id: int, limit: int = 20, with_summary: bool = False
) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM articles WHERE chat_id = ?"
        if with_summary:
            query += " AND summary IS NOT NULL"
        query += " ORDER BY fetched_at DESC LIMIT ?"
        cursor = await db.execute(query, (chat_id, limit))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_article_by_id(article_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM articles WHERE id = ?", (article_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def search_articles(chat_id: int, query: str, limit: int = 5) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        search_term = f"%{query}%"
        cursor = await db.execute(
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
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def add_conversation(chat_id: int, role: str, message: str, article_ids: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO conversation_history (chat_id, role, message, article_ids) VALUES (?, ?, ?, ?)",
            (chat_id, role, message, article_ids),
        )
        await db.commit()


async def get_conversation_history(chat_id: int, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM conversation_history 
               WHERE chat_id = ? 
               ORDER BY timestamp DESC LIMIT ?""",
            (chat_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in reversed(rows)]


async def article_exists(url: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM articles WHERE url = ?", (url,)
        )
        return await cursor.fetchone() is not None


async def get_article_count(chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM articles WHERE chat_id = ?", (chat_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_articles_by_feed(chat_id: int, feed_url: str, limit: int = 20, offset: int = 0) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM articles 
               WHERE chat_id = ? AND feed_url = ? 
               ORDER BY published_at DESC LIMIT ? OFFSET ?""",
            (chat_id, feed_url, limit, offset),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_articles_by_feed_count(chat_id: int, feed_url: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM articles WHERE chat_id = ? AND feed_url = ?",
            (chat_id, feed_url),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_feed_title(chat_id: int, feed_url: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT title FROM feeds WHERE chat_id = ? AND url = ?",
            (chat_id, feed_url),
        )
        row = await cursor.fetchone()
        return row[0] if row else feed_url.split("//")[-1].split(".")[0]

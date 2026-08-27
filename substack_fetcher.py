import feedparser
import httpx
import re
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import database as db


@dataclass
class SubstackPost:
    title: str
    url: str
    author: str
    published_at: str
    content: str
    feed_url: str


def normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
    if ".substack.com" in url and "/feed" not in url:
        if not url.endswith("/feed"):
            url = url.rstrip("/") + "/feed"
    return url


def extract_post_url(entry) -> Optional[str]:
    if hasattr(entry, "link"):
        return entry.link
    if hasattr(entry, "id"):
        return entry.id
    return None


def clean_html(html_content: str) -> str:
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    for script in soup(["script", "style"]):
        script.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:15000]


async def fetch_feed(feed_url: str) -> Optional[dict]:
    normalized = normalize_url(feed_url)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                normalized,
                headers={"User-Agent": "SubstackBot/1.0"},
                follow_redirects=True,
            )
            response.raise_for_status()
            content = response.text
    except Exception as e:
        print(f"Error fetching {normalized}: {e}")
        return None

    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        print(f"Error parsing feed {normalized}: {feed.bozo_exception}")
        return None

    return {
        "title": feed.feed.get("title", ""),
        "url": normalized.replace("/feed", ""),
        "entries": feed.entries,
    }


async def fetch_recent_posts(
    feed_url: str, chat_id: int, limit: int = 10
) -> list[SubstackPost]:
    feed_data = await fetch_feed(feed_url)
    if not feed_data:
        return []

    posts = []
    for entry in feed_data["entries"][:limit]:
        post_url = extract_post_url(entry)
        if not post_url:
            continue

        if await db.article_exists(post_url):
            continue

        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6]).isoformat()
            except Exception:
                published = str(entry.published_parsed)

        content = ""
        if hasattr(entry, "content") and entry.content:
            content = clean_html(entry.content[0].get("value", ""))
        elif hasattr(entry, "summary"):
            content = clean_html(entry.summary)

        post = SubstackPost(
            title=entry.get("title", "Untitled"),
            url=post_url,
            author=entry.get("author", feed_data["title"]),
            published_at=published,
            content=content,
            feed_url=feed_data["url"],
        )
        posts.append(post)

    return posts


async def fetch_and_store(feed_url: str, chat_id: int) -> list[dict]:
    posts = await fetch_recent_posts(feed_url, chat_id)
    stored = []
    for post in posts:
        article_id = await db.add_article(
            chat_id=chat_id,
            feed_url=post.feed_url,
            title=post.title,
            url=post.url,
            author=post.author,
            published_at=post.published_at,
            content=post.content,
        )
        if article_id:
            stored.append(
                {
                    "id": article_id,
                    "title": post.title,
                    "url": post.url,
                    "author": post.author,
                    "published_at": post.published_at,
                }
            )
    return stored


async def fetch_all_feeds(chat_id: int) -> dict:
    feeds = await db.get_feeds(chat_id)
    results = {"total_new": 0, "articles": [], "errors": []}

    for feed in feeds:
        try:
            articles = await fetch_and_store(feed["url"], chat_id)
            results["total_new"] += len(articles)
            results["articles"].extend(articles)
        except Exception as e:
            results["errors"].append({"url": feed["url"], "error": str(e)})

    return results

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


async def fetch_feed(feed_url: str) -> list[dict]:
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
        return []

    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        print(f"Error parsing feed {normalized}: {feed.bozo_exception}")
        return []

    base_url = normalized.replace("/feed", "")
    posts = []
    for entry in feed.entries[:10]:
        post_url = extract_post_url(entry)
        if not post_url:
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

        post = {
            "title": entry.get("title", "Untitled"),
            "url": post_url,
            "author": entry.get("author", feed.feed.get("title", "Unknown")),
            "published_at": published,
            "content": content,
            "feed_url": base_url,
        }
        posts.append(post)

    return posts


async def fetch_all_feeds(chat_id: int) -> dict:
    feeds = await db.get_feeds(chat_id)
    results = {"articles": [], "errors": []}

    for feed in feeds:
        try:
            articles = await fetch_feed(feed["url"])
            for article in articles:
                article["feed_title"] = feed.get("title") or feed["url"].split("//")[-1].split(".")[0]
            results["articles"].extend(articles)
        except Exception as e:
            results["errors"].append({"url": feed["url"], "error": str(e)})

    return results

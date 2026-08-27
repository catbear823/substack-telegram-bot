from aiogram import Router, types
from aiogram.filters import Command
import re

import database as db

router = Router()

URL_PATTERN = re.compile(r"https?://[^\s]+\.substack\.com[/feed]*")


@router.message(Command("add"))
async def cmd_add(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "請提供 Substack 網址\n"
            "格式：/add https://example.substack.com"
        )
        return

    url = args[1].strip()
    if not URL_PATTERN.search(url):
        await message.answer("⚠️ 請提供有效的 Substack 網址（以 .substack.com 結尾）")
        return

    if not url.startswith("http"):
        url = "https://" + url

    existing = await db.get_feeds(message.chat.id)
    if any(f["url"].rstrip("/") == url.rstrip("/") for f in existing):
        await message.answer("⚠️ 這個來源已經在訂閱列表中了")
        return

    success = await db.add_feed(message.chat.id, url, title=url.split("//")[-1].split(".")[0])
    if success:
        await message.answer(
            f"✅ 已新增訂閱：\n{url}\n\n"
            "使用 /fetch 開始抓取最新文章"
        )
    else:
        await message.answer("❌ 新增失敗，請稍後再試")


@router.message(Command("remove"))
async def cmd_remove(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("請提供要移除的 Substack 網址")
        return

    url = args[1].strip()
    success = await db.remove_feed(message.chat.id, url)
    if success:
        await message.answer(f"✅ 已移除：{url}")
    else:
        await message.answer("⚠️ 找不到這個訂閱來源")


@router.message(Command("list"))
async def cmd_list(message: types.Message):
    feeds = await db.get_feeds(message.chat.id)
    if not feeds:
        await message.answer(
            "📭 目前沒有訂閱任何來源\n\n"
            "使用 /add <url> 新增你的第一個 Substack 訂閱"
        )
        return

    lines = ["📚 **你的訂閱列表：**\n"]
    for i, feed in enumerate(feeds, 1):
        article_count = 0
        all_articles = await db.get_articles(message.chat.id, limit=1000)
        article_count = sum(1 for a in all_articles if a["feed_url"] == feed["url"])
        lines.append(f"{i}. {feed['url']}")
        lines.append(f"   📄 已抓取 {article_count} 篇文章\n")

    lines.append(f"共 {len(feeds)} 個來源")
    await message.answer("\n".join(lines), parse_mode="Markdown")

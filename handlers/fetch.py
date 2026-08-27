from aiogram import Router, types
from aiogram.filters import Command

import database as db
from substack_fetcher import fetch_all_feeds, fetch_feed

router = Router()


@router.message(Command("fetch"))
async def cmd_fetch(message: types.Message):
    feeds = await db.get_feeds(message.chat.id)
    if not feeds:
        await message.answer(
            "📭 目前沒有訂閱任何來源\n\n"
            "使用 /add <url> 新增 Substack 訂閱"
        )
        return

    status_msg = await message.answer("🔄 正在抓取最新文章...")

    results = await fetch_all_feeds(message.chat.id)
    errors = results["errors"]
    all_articles = results["articles"]

    if not all_articles and not errors:
        await status_msg.edit_text("✅ 抓取完成！目前沒有新文章")
        return

    lines = [f"✅ 抓取完成！共找到 {len(all_articles)} 篇文章\n"]
    for article in all_articles[:10]:
        lines.append(f"📰 {article['title']}")
        lines.append(f"   👤 {article.get('author', 'Unknown')}")
        lines.append(f"   🔗 {article['url']}\n")

    if errors:
        lines.append(f"\n⚠️ {len(errors)} 個來源抓取失敗：")
        for err in errors:
            lines.append(f"   ❌ {err['url']}: {err['error']}")

    lines.append("\n💡 使用 /latest 查看摘要，或 /ask 提問")

    await status_msg.edit_text("\n".join(lines), parse_mode="Markdown")


@router.message(Command("latest"))
async def cmd_latest(message: types.Message):
    feeds = await db.get_feeds(message.chat.id)
    if not feeds:
        await message.answer(
            "📭 目前沒有訂閱任何來源\n\n"
            "使用 /add <url> 新增 Substack 訂閱"
        )
        return

    status_msg = await message.answer("🔄 正在抓取最新文章...")

    all_articles = []
    for feed in feeds:
        try:
            articles = await fetch_feed(feed["url"])
            for article in articles[:3]:
                article["feed_title"] = feed.get("title") or feed["url"].split("//")[-1].split(".")[0]
                all_articles.append(article)
        except Exception:
            continue

    all_articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    all_articles = all_articles[:10]

    if not all_articles:
        await status_msg.edit_text("📭 目前沒有文章\n\n請先新增訂閱來源")
        return

    lines = ["📰 **最新文章列表：**\n"]
    for i, article in enumerate(all_articles):
        date = article.get("published_at", "")[:10] if article.get("published_at") else ""
        feed_title = article.get("feed_title", "")
        lines.append(f"{i+1}. {article['title']}")
        if date:
            lines.append(f"   📅 {date} | 📰 {feed_title}")

    lines.append("\n💡 使用 /ask <問題> 針對文章提問")
    await status_msg.edit_text("\n".join(lines), parse_mode="Markdown")

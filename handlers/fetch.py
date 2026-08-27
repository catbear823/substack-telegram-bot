from aiogram import Router, types
from aiogram.filters import Command

import database as db
from substack_fetcher import fetch_all_feeds, fetch_and_store

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

    new_count = results["total_new"]
    errors = results["errors"]

    if new_count == 0 and not errors:
        await status_msg.edit_text(
            "✅ 抓取完成！目前沒有新文章\n"
            "（所有文章都已抓取過）"
        )
        return

    lines = []
    if new_count > 0:
        lines.append(f"✅ 抓取完成！新增 {new_count} 篇文章\n")
        for article in results["articles"][:10]:
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
    articles = await db.get_articles(message.chat.id, limit=10, with_summary=True)
    if not articles:
        articles = await db.get_articles(message.chat.id, limit=10)

    if not articles:
        await message.answer(
            "📭 目前沒有文章\n\n"
            "使用 /fetch 抓取最新文章"
        )
        return

    lines = ["📰 **最新文章列表：**\n"]
    for article in articles:
        summary_preview = ""
        if article.get("summary"):
            summary_preview = f"\n   📝 {article['summary'][:100]}..."
        lines.append(f"🆔 `{article['id']}` - {article['title']}")
        lines.append(f"   👤 {article.get('author', 'Unknown')}{summary_preview}\n")

    lines.append("使用 /summary <id> 查看詳細摘要")
    lines.append("使用 /ask <問題> 針對文章提問")
    await message.answer("\n".join(lines), parse_mode="Markdown")

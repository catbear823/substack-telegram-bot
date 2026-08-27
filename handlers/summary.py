from aiogram import Router, types
from aiogram.filters import Command

import database as db
from substack_fetcher import fetch_feed
from summarizer import summarize_article

router = Router()


@router.message(Command("summary"))
async def cmd_summary(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(
            "請提供文章編號\n"
            "格式：/summary <編號>\n\n"
            "使用 /latest 查看文章列表"
        )
        return

    try:
        article_index = int(args[1].strip()) - 1
    except ValueError:
        await message.answer("⚠️ 請輸入有效的數字編號")
        return

    feeds = await db.get_feeds(message.chat.id)
    if not feeds:
        await message.answer("📭 目前沒有訂閱任何來源\n\n使用 /add <url> 新增 Substack 訂閱")
        return

    status_msg = await message.answer("🔄 正在抓取文章...")

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

    if article_index >= len(all_articles) or article_index < 0:
        await status_msg.edit_text(f"⚠️ 找不到第 {article_index + 1} 篇文章\n\n共找到 {len(all_articles)} 篇文章")
        return

    article = all_articles[article_index]

    await status_msg.edit_text("🔄 正在生成摘要...")
    content = article.get("content", "")
    if content:
        summary = await summarize_article(article["title"], content)
    else:
        summary = "無法取得文章內容"

    text = (
        f"📄 **{article['title']}**\n\n"
        f"👤 作者：{article.get('author', 'Unknown')}\n"
        f"📅 發布：{article.get('published_at', 'Unknown')}\n"
        f"📰 來源：{article.get('feed_title', 'Unknown')}\n"
        f"🔗 連結：{article.get('url', '')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📝 **AI 摘要：**\n\n"
        f"{summary}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💡 使用 /ask 針對這篇文章提問"
    )

    try:
        await status_msg.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        await status_msg.edit_text(text, disable_web_page_preview=True)

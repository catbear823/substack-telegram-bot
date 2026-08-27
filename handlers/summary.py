from aiogram import Router, types
from aiogram.filters import Command

import database as db
from summarizer import summarize_article

router = Router()


@router.message(Command("summary"))
async def cmd_summary(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer(
            "請提供文章 ID\n"
            "格式：/summary <id>\n\n"
            "使用 /latest 查看文章列表"
        )
        return

    article_id = int(args[1].strip())
    article = await db.get_article_by_id(article_id)

    if not article:
        await message.answer("⚠️ 找不到這篇文章，請檢查 ID 是否正確")
        return

    if article.get("summary"):
        summary = article["summary"]
    else:
        status_msg = await message.answer("🔄 正在生成摘要...")
        content = article.get("content", "")
        if not content:
            await status_msg.edit_text("⚠️ 這篇文章沒有可用的內容")
            return
        summary = await summarize_article(article["title"], content)
        await db.update_article_summary(article_id, summary)

    text = (
        f"📄 **{article['title']}**\n\n"
        f"👤 作者：{article.get('author', 'Unknown')}\n"
        f"📅 發布：{article.get('published_at', 'Unknown')}\n"
        f"🔗 連結：{article.get('url', '')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📝 **AI 摘要：**\n\n"
        f"{summary}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💡 使用 /ask 針對這篇文章提問"
    )

    try:
        await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        await message.answer(text, disable_web_page_preview=True)

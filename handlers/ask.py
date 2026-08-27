from aiogram import Router, types
from aiogram.filters import Command

import database as db
from summarizer import answer_question

router = Router()


@router.message(Command("ask"))
async def cmd_ask(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(
            "請提供你的問題\n"
            "格式：/ask <你的問題>\n\n"
            "例如：/ask 最近的文章討論了什麼主題？"
        )
        return

    question = args[1].strip()

    articles = await db.get_articles(message.chat.id, limit=30)
    if not articles:
        await message.answer(
            "📭 目前沒有已抓取的文章\n\n"
            "請先使用 /fetch 抓取文章，然後再提問"
        )
        return

    relevant = await db.search_articles(message.chat.id, question, limit=5)
    if not relevant:
        relevant = articles[:5]

    status_msg = await message.answer("🔄 正在分析文章並回答你的問題...")

    history = await db.get_conversation_history(message.chat.id, limit=6)
    answer = await answer_question(question, relevant, history)

    await db.add_conversation(message.chat.id, "user", question,
                              ",".join(str(a["id"]) for a in relevant))
    await db.add_conversation(message.chat.id, "assistant", answer)

    source_lines = []
    for a in relevant[:3]:
        source_lines.append(f"• {a['title']} ({a.get('url', '')})")
    sources = "\n".join(source_lines)

    text = (
        f"❓ **你的問題：**\n{question}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💡 **回答：**\n\n"
        f"{answer}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📚 **參考來源：**\n{sources}\n\n"
        f"💡 你可以繼續追問！"
    )

    try:
        await status_msg.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        await status_msg.edit_text(text, disable_web_page_preview=True)

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from substack_fetcher import fetch_feed
from summarizer import answer_question

router = Router()


class AskState(StatesGroup):
    waiting_for_question = State()


async def process_question(message: Message, question: str):
    feeds = await db.get_feeds(message.chat.id)
    if not feeds:
        await message.answer(
            "📭 目前沒有訂閱任何來源\n\n"
            "請先使用 /add 新增 Substack 訂閱"
        )
        return

    status_msg = await message.answer("🔄 正在抓取文章並分析...")

    all_articles = []
    for feed in feeds:
        try:
            articles = await fetch_feed(feed["url"])
            for article in articles[:5]:
                article["feed_title"] = feed.get("title") or feed["url"].split("//")[-1].split(".")[0]
                all_articles.append(article)
        except Exception:
            continue

    if not all_articles:
        await status_msg.edit_text("📭 無法抓取到任何文章\n\n請稍後再試")
        return

    relevant = all_articles[:10]

    history = await db.get_conversation_history(message.chat.id, limit=6)
    answer = await answer_question(question, relevant, history)

    await db.add_conversation(message.chat.id, "user", question)
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

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❓ 繼續提問", callback_data="menu_ask")],
            [InlineKeyboardButton(text="🏠 返回主選單", callback_data="menu_back")],
        ]
    )

    try:
        await status_msg.edit_text(text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        await status_msg.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)


@router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await state.set_state(AskState.waiting_for_question)
        await message.answer(
            "請提供你的問題\n"
            "格式：/ask <你的問題>\n\n"
            "例如：/ask 最近的文章討論了什麼主題？"
        )
        return

    question = args[1].strip()
    await process_question(message, question)


@router.message(AskState.waiting_for_question, F.text)
async def handle_ask_question(message: Message, state: FSMContext):
    await state.clear()
    question = message.text.strip()
    await process_question(message, question)

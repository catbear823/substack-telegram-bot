from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import database as db

router = Router()


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="📰 追蹤列表", callback_data="menu_list"),
            InlineKeyboardButton(text="🔄 抓取文章", callback_data="menu_fetch"),
        ],
        [
            InlineKeyboardButton(text="📝 最新摘要", callback_data="menu_latest"),
            InlineKeyboardButton(text="📚 歷史文章", callback_data="menu_history"),
        ],
        [
            InlineKeyboardButton(text="❓ 提問", callback_data="menu_ask"),
            InlineKeyboardButton(text="⏰ 定時推送", callback_data="menu_schedule"),
        ],
        [
            InlineKeyboardButton(text="➕ 新增訂閱", callback_data="menu_add"),
            InlineKeyboardButton(text="📖 使用說明", callback_data="menu_help"),
        ],
        [
            InlineKeyboardButton(text="🔗 分享訂閱", callback_data="menu_share"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) >= 2 and args[1].strip():
        share_code = args[1].strip()
        owner_chat_id = await db.get_owner_by_share_code(share_code)

        if owner_chat_id and owner_chat_id != message.chat.id:
            feeds = await db.get_feeds(owner_chat_id)
            if not feeds:
                await message.answer("📭 此用戶目前沒有訂閱任何來源")
                return

            lines = ["📚 **對方的訂閱列表：**\n"]
            buttons = []
            for i, feed in enumerate(feeds):
                count = await db.get_articles_by_feed_count(owner_chat_id, feed["url"])
                title = feed.get("title") or feed["url"].split("//")[-1].split(".")[0]
                lines.append(f"{i+1}. {title} ({count} 篇)")
                buttons.append(
                    [InlineKeyboardButton(
                        text=f"📰 {title} ({count})",
                        callback_data=f"shared_feed_{owner_chat_id}_{i}"
                    )]
                )

            buttons.append([InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await message.answer("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")
            return

    text = (
        "👋 你好！我是 Substack 閱讀助手 Bot\n\n"
        "我可以幫你：\n"
        "📰 追蹤 Substack Newsletter\n"
        "📝 自動生成文章摘要\n"
        "❓ 針對文章內容回答問題\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "👇 點擊下方按鈕開始使用："
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard())


@router.message(Command("menu"))
async def cmd_menu(message: types.Message):
    text = "📋 主選單\n\n點擊按鈕執行操作："
    await message.answer(text, reply_markup=get_main_menu_keyboard())

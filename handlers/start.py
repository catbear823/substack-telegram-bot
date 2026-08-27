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
            InlineKeyboardButton(text="❓ 提問", callback_data="menu_ask"),
        ],
        [
            InlineKeyboardButton(text="➕ 新增訂閱", callback_data="menu_add"),
            InlineKeyboardButton(text="⏰ 定時推送", callback_data="menu_schedule"),
        ],
        [
            InlineKeyboardButton(text="📖 使用說明", callback_data="menu_help"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(CommandStart())
async def cmd_start(message: types.Message):
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

from aiogram import Router, types
from aiogram.filters import CommandStart

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    text = (
        "👋 你好！我是 Substack 閱讀助手 Bot\n\n"
        "我可以幫你：\n"
        "📰 追蹤 Substack Newsletter\n"
        "📝 自動生成文章摘要\n"
        "❓ 針對文章內容回答問題\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "**可用命令：**\n\n"
        "/add <url> - 新增 Substack 訂閱\n"
        "例如：/add https://example.substack.com\n\n"
        "/list - 列出所有已訂閱的來源\n\n"
        "/remove <url> - 移除訂閱\n\n"
        "/fetch - 手動抓取最新文章\n\n"
        "/latest - 查看最新文章摘要\n\n"
        "/summary <id> - 查看特定文章的詳細摘要\n"
        "例如：/summary 5\n\n"
        "/ask <問題> - 針對已抓取的文章提問\n"
        "例如：/ask 這篇文章的重點是什麼？\n\n"
        "/schedule - 設定每日自動抓取\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💡 提示：先用 /add 新增你的 Substack 來源，然後 /fetch 開始抓取！"
    )
    await message.answer(text, parse_mode="Markdown")

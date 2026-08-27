from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
from substack_fetcher import fetch_all_feeds, fetch_feed
from summarizer import summarize_article, answer_question
from handlers.start import get_main_menu_keyboard
from handlers.feeds import AddFeedState
from handlers.ask import AskState

router = Router()


def back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")]]
    )


@router.callback_query(F.data == "menu_back")
async def callback_back(callback: types.CallbackQuery):
    text = "📋 主選單\n\n點擊按鈕執行操作："
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu_help")
async def callback_help(callback: types.CallbackQuery):
    text = (
        "📖 **使用說明**\n\n"
        "**基本流程：**\n"
        "1️⃣ 點擊「➕ 新增訂閱」新增 Substack 來源\n"
        "2️⃣ 點擊「🔄 抓取文章」查看最新內容\n"
        "3️⃣ 點擊「📝 最新摘要」查看 AI 摘要\n"
        "4️⃣ 點擊「❓ 提問」針對文章內容提問\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "**支援的網址格式：**\n"
        "• https://example.substack.com\n"
        "• https://substack.com/@username\n\n"
        "**指令格式：**\n"
        "• /add <url> - 新增訂閱\n"
        "• /ask <問題> - 針對文章提問\n"
        "• /share - 分享訂閱列表\n"
    )
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_list")
async def callback_list(callback: types.CallbackQuery):
    feeds = await db.get_feeds(callback.message.chat.id)
    if not feeds:
        text = (
            "📭 目前沒有訂閱任何來源\n\n"
            "點擊「➕ 新增訂閱」新增你的第一個 Substack 訂閱"
        )
        await callback.message.edit_text(text, reply_markup=back_button())
        await callback.answer()
        return

    lines = ["📚 **你的訂閱列表：**\n"]
    for i, feed in enumerate(feeds, 1):
        title = feed.get("title") or feed["url"].split("//")[-1].split(".")[0]
        lines.append(f"{i}. {title}")
        lines.append(f"   🔗 {feed['url']}\n")

    lines.append(f"共 {len(feeds)} 個來源")
    await callback.message.edit_text("\n".join(lines), reply_markup=back_button(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_fetch")
async def callback_fetch(callback: types.CallbackQuery):
    feeds = await db.get_feeds(callback.message.chat.id)
    if not feeds:
        text = "📭 目前沒有訂閱任何來源\n\n點擊「➕ 新增訂閱」新增 Substack 訂閱"
        await callback.message.edit_text(text, reply_markup=back_button())
        await callback.answer()
        return

    await callback.message.edit_text("🔄 正在抓取最新文章...", reply_markup=back_button())
    await callback.answer()

    results = await fetch_all_feeds(callback.message.chat.id)
    errors = results["errors"]
    all_articles = results["articles"]

    if not all_articles and not errors:
        text = "✅ 抓取完成！目前沒有新文章"
        await callback.message.edit_text(text, reply_markup=back_button())
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

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 查看最新摘要", callback_data="menu_latest")],
            [InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")],
        ]
    )
    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data == "menu_latest")
async def callback_latest(callback: types.CallbackQuery):
    feeds = await db.get_feeds(callback.message.chat.id)
    if not feeds:
        text = "📭 目前沒有訂閱任何來源\n\n點擊「➕ 新增訂閱」新增 Substack 訂閱"
        await callback.message.edit_text(text, reply_markup=back_button())
        await callback.answer()
        return

    await callback.message.edit_text("🔄 正在抓取最新文章...", reply_markup=back_button())
    await callback.answer()

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
        text = "📭 目前沒有文章\n\n請先新增訂閱來源"
        await callback.message.edit_text(text, reply_markup=back_button())
        return

    lines = ["📰 **最新文章列表：**\n"]
    buttons = []
    for i, article in enumerate(all_articles[:5]):
        date = article.get("published_at", "")[:10] if article.get("published_at") else ""
        feed_title = article.get("feed_title", "")
        lines.append(f"{i+1}. {article['title']}")
        if date:
            lines.append(f"   📅 {date} | 📰 {feed_title}")
        buttons.append(
            [InlineKeyboardButton(
                text=f"📄 {article['title'][:30]}...",
                callback_data=f"view_article_{i}"
            )]
        )

    buttons.append([InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data.startswith("view_article_"))
async def callback_view_article(callback: types.CallbackQuery):
    article_index = int(callback.data.split("_")[2])

    feeds = await db.get_feeds(callback.message.chat.id)
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

    if article_index >= len(all_articles):
        await callback.message.edit_text("⚠️ 找不到這篇文章", reply_markup=back_button())
        await callback.answer()
        return

    article = all_articles[article_index]

    await callback.message.edit_text("🔄 正在生成摘要...", reply_markup=back_button())
    await callback.answer()

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
        f"{summary}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 閱讀全文", url=article.get("url", ""))],
            [InlineKeyboardButton(text="🔙 返回文章列表", callback_data="menu_latest")],
        ]
    )

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)


@router.callback_query(F.data == "menu_ask")
async def callback_ask_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AskState.waiting_for_question)
    text = (
        "❓ **提問功能**\n\n"
        "請直接輸入你的問題，例如：\n"
        "• 最近的文章討論了什麼主題？\n"
        "• NVIDIA 的財報如何？\n"
        "• 有什麼投資建議？\n\n"
        "💡 系統會從訂閱來源中搜尋相關內容回答"
    )
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_add")
async def callback_add_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddFeedState.waiting_for_url)
    text = (
        "➕ **新增訂閱**\n\n"
        "請直接輸入 Substack 網址，格式：\n"
        "• https://example.substack.com\n"
        "• https://substack.com/@username\n\n"
        "💡 輸入網址後會自動新增"
    )
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_schedule")
async def callback_schedule(callback: types.CallbackQuery):
    feeds = await db.get_feeds(callback.message.chat.id)
    if not feeds:
        text = "📭 請先新增訂閱來源，再設定排程"
        await callback.message.edit_text(text, reply_markup=back_button())
        await callback.answer()
        return

    text = (
        "⏰ **定時推送設定**\n\n"
        "請輸入時間（24小時制），例如：\n"
        "• 8:00 - 每天早上8點\n"
        "• 18:30 - 每天下午6點半\n\n"
        "💡 再次點擊可停止自動抓取"
    )
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_history")
async def callback_history(callback: types.CallbackQuery):
    feeds = await db.get_feeds(callback.message.chat.id)
    if not feeds:
        text = "📭 目前沒有訂閱任何來源\n\n點擊「➕ 新增訂閱」新增你的第一個 Substack 訂閱"
        await callback.message.edit_text(text, reply_markup=back_button())
        await callback.answer()
        return

    lines = ["📚 **歷史文章**\n\n選擇一個來源查看歷史文章：\n"]
    buttons = []
    for i, feed in enumerate(feeds):
        title = feed.get("title") or feed["url"].split("//")[-1].split(".")[0]
        lines.append(f"{i+1}. {title}")
        buttons.append(
            [InlineKeyboardButton(
                text=f"📰 {title}",
                callback_data=f"history_feed_{i}"
            )]
        )

    buttons.append([InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("history_feed_"))
async def callback_history_feed(callback: types.CallbackQuery):
    feed_index = int(callback.data.split("_")[2])
    feeds = await db.get_feeds(callback.message.chat.id)

    if feed_index >= len(feeds):
        await callback.message.edit_text("⚠️ 來源不存在", reply_markup=back_button())
        await callback.answer()
        return

    feed = feeds[feed_index]
    feed_url = feed["url"]
    title = feed.get("title") or feed_url.split("//")[-1].split(".")[0]

    await callback.message.edit_text(f"🔄 正在抓取 **{title}** 的文章...", reply_markup=back_button(), parse_mode="Markdown")
    await callback.answer()

    try:
        articles = await fetch_feed(feed_url)
    except Exception:
        articles = []

    if not articles:
        text = f"📭 **{title}**\n\n此來源目前沒有文章"
        await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="Markdown")
        return

    lines = [f"📚 **{title}** （最新 {min(len(articles), 10)} 篇）\n"]
    buttons = []
    for i, article in enumerate(articles[:10]):
        date = article.get("published_at", "")[:10] if article.get("published_at") else ""
        lines.append(f"{i+1}. {article['title']}")
        if date:
            lines.append(f"   📅 {date}")
        buttons.append(
            [InlineKeyboardButton(
                text=f"📄 {article['title'][:35]}...",
                callback_data=f"history_view_{feed_index}_{i}"
            )]
        )

    buttons.append([InlineKeyboardButton(text="🔙 返回來源列表", callback_data="menu_history")])
    buttons.append([InlineKeyboardButton(text="🏠 主選單", callback_data="menu_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data.startswith("history_view_"))
async def callback_history_view(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    feed_index = int(parts[2])
    article_index = int(parts[3])

    feeds = await db.get_feeds(callback.message.chat.id)
    if feed_index >= len(feeds):
        await callback.message.edit_text("⚠️ 來源不存在", reply_markup=back_button())
        await callback.answer()
        return

    feed = feeds[feed_index]
    feed_url = feed["url"]

    await callback.message.edit_text("🔄 正在抓取文章內容...", reply_markup=back_button())
    await callback.answer()

    try:
        articles = await fetch_feed(feed_url)
    except Exception:
        articles = []

    if article_index >= len(articles):
        await callback.message.edit_text("⚠️ 找不到這篇文章", reply_markup=back_button())
        return

    article = articles[article_index]

    content = article.get("content", "")
    if content:
        summary = await summarize_article(article["title"], content)
    else:
        summary = "無法取得文章內容"

    text = (
        f"📄 **{article['title']}**\n\n"
        f"👤 作者：{article.get('author', 'Unknown')}\n"
        f"📅 發布：{article.get('published_at', 'Unknown')}\n"
        f"🔗 連結：{article.get('url', '')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📝 **AI 摘要：**\n\n"
        f"{summary}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 閱讀全文", url=article.get("url", ""))],
            [
                InlineKeyboardButton(text="⬅️ 返回列表", callback_data=f"history_feed_{feed_index}"),
                InlineKeyboardButton(text="🏠 主選單", callback_data="menu_back"),
            ],
        ]
    )

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)

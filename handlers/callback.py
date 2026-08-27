from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from substack_fetcher import fetch_all_feeds
from summarizer import summarize_article, answer_question
from handlers.start import get_main_menu_keyboard

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
        "2️⃣ 點擊「🔄 抓取文章」抓取最新內容\n"
        "3️⃣ 點擊「📝 最新摘要」查看 AI 摘要\n"
        "4️⃣ 點擊「❓ 提問」針對文章內容提問\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "**支援的網址格式：**\n"
        "• https://example.substack.com\n"
        "• https://substack.com/@username\n\n"
        "**指令格式：**\n"
        "• /add <url> - 新增訂閱\n"
        "• /ask <問題> - 針對文章提問\n"
        "• /summary <id> - 查看特定文章摘要\n"
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
        all_articles = await db.get_articles(callback.message.chat.id, limit=1000)
        article_count = sum(1 for a in all_articles if a["feed_url"] == feed["url"])
        lines.append(f"{i}. {feed['url']}")
        lines.append(f"   📄 已抓取 {article_count} 篇文章\n")

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
    new_count = results["total_new"]
    errors = results["errors"]

    if new_count == 0 and not errors:
        text = "✅ 抓取完成！目前沒有新文章\n（所有文章都已抓取過）"
        await callback.message.edit_text(text, reply_markup=back_button())
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

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 查看最新摘要", callback_data="menu_latest")],
            [InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")],
        ]
    )
    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data == "menu_latest")
async def callback_latest(callback: types.CallbackQuery):
    articles = await db.get_articles(callback.message.chat.id, limit=10, with_summary=True)
    if not articles:
        articles = await db.get_articles(callback.message.chat.id, limit=10)

    if not articles:
        text = "📭 目前沒有文章\n\n點擊「🔄 抓取文章」抓取最新內容"
        await callback.message.edit_text(text, reply_markup=back_button())
        await callback.answer()
        return

    lines = ["📰 **最新文章列表：**\n"]
    buttons = []
    for article in articles[:5]:
        summary_preview = ""
        if article.get("summary"):
            summary_preview = f"\n   📝 {article['summary'][:80]}..."
        lines.append(f"🆔 `{article['id']}` - {article['title']}")
        lines.append(f"   👤 {article.get('author', 'Unknown')}{summary_preview}\n")
        buttons.append(
            [InlineKeyboardButton(
                text=f"📄 {article['title'][:30]}...",
                callback_data=f"summary_{article['id']}"
            )]
        )

    if len(articles) > 5:
        lines.append("（顯示最近 5 篇，更多文章請用 /summary <id>）")

    buttons.append([InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("summary_"))
async def callback_summary(callback: types.CallbackQuery):
    article_id = int(callback.data.split("_")[1])
    article = await db.get_article_by_id(article_id)

    if not article:
        await callback.message.edit_text("⚠️ 找不到這篇文章", reply_markup=back_button())
        await callback.answer()
        return

    if article.get("summary"):
        summary = article["summary"]
    else:
        await callback.message.edit_text("🔄 正在生成摘要...", reply_markup=back_button())
        await callback.answer()
        content = article.get("content", "")
        if not content:
            await callback.message.edit_text("⚠️ 這篇文章沒有可用的內容", reply_markup=back_button())
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
        f"{summary}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❓ 針對此文提問", callback_data=f"ask_article_{article_id}")],
            [InlineKeyboardButton(text="🔙 返回文章列表", callback_data="menu_latest")],
        ]
    )

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data == "menu_ask")
async def callback_ask_prompt(callback: types.CallbackQuery):
    text = (
        "❓ **提問功能**\n\n"
        "請直接輸入你的問題，例如：\n"
        "• 最近的文章討論了什麼主題？\n"
        "• NVIDIA 的財報如何？\n"
        "• 有什麼投資建議？\n\n"
        "💡 系統會從已抓取的文章中搜尋相關內容回答"
    )
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("ask_article_"))
async def callback_ask_article(callback: types.CallbackQuery):
    article_id = int(callback.data.split("_")[2])
    article = await db.get_article_by_id(article_id)

    if not article:
        await callback.message.edit_text("⚠️ 找不到這篇文章", reply_markup=back_button())
        await callback.answer()
        return

    text = (
        f"❓ **針對「{article['title'][:30]}...」提問**\n\n"
        "請輸入你的問題："
    )
    await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_add")
async def callback_add_prompt(callback: types.CallbackQuery):
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
        count = await db.get_articles_by_feed_count(callback.message.chat.id, feed["url"])
        title = feed.get("title") or feed["url"].split("//")[-1].split(".")[0]
        lines.append(f"{i+1}. {title} ({count} 篇)")
        buttons.append(
            [InlineKeyboardButton(
                text=f"📰 {title} ({count})",
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
    page = 0
    per_page = 5

    articles = await db.get_articles_by_feed(callback.message.chat.id, feed_url, limit=per_page, offset=page * per_page)
    total = await db.get_articles_by_feed_count(callback.message.chat.id, feed_url)
    title = feed.get("title") or feed_url.split("//")[-1].split(".")[0]

    if not articles:
        text = f"📭 **{title}**\n\n目前沒有已抓取的文章"
        await callback.message.edit_text(text, reply_markup=back_button(), parse_mode="Markdown")
        await callback.answer()
        return

    lines = [f"📚 **{title}** （共 {total} 篇）\n"]
    buttons = []
    for article in articles:
        date = article.get("published_at", "")[:10] if article.get("published_at") else ""
        summary_preview = ""
        if article.get("summary"):
            summary_preview = f"\n   📝 {article['summary'][:60]}..."
        lines.append(f"🆔 `{article['id']}` - {article['title']}")
        if date:
            lines.append(f"   📅 {date}{summary_preview}\n")
        else:
            lines.append(f"   {summary_preview}\n")
        buttons.append(
            [InlineKeyboardButton(
                text=f"📄 {article['title'][:35]}...",
                callback_data=f"history_article_{article['id']}"
            )]
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ 上一頁", callback_data=f"history_page_{feed_index}_{page-1}")
        )
    if total > (page + 1) * per_page:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️ 下一頁", callback_data=f"history_page_{feed_index}_{page+1}")
        )
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="🔙 返回來源列表", callback_data="menu_history")])
    buttons.append([InlineKeyboardButton(text="🏠 主選單", callback_data="menu_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("history_page_"))
async def callback_history_page(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    feed_index = int(parts[2])
    page = int(parts[3])

    feeds = await db.get_feeds(callback.message.chat.id)
    if feed_index >= len(feeds):
        await callback.message.edit_text("⚠️ 來源不存在", reply_markup=back_button())
        await callback.answer()
        return

    feed = feeds[feed_index]
    feed_url = feed["url"]
    per_page = 5

    articles = await db.get_articles_by_feed(callback.message.chat.id, feed_url, limit=per_page, offset=page * per_page)
    total = await db.get_articles_by_feed_count(callback.message.chat.id, feed_url)
    title = feed.get("title") or feed_url.split("//")[-1].split(".")[0]

    lines = [f"📚 **{title}** （共 {total} 篇，第 {page+1} 頁）\n"]
    buttons = []
    for article in articles:
        date = article.get("published_at", "")[:10] if article.get("published_at") else ""
        summary_preview = ""
        if article.get("summary"):
            summary_preview = f"\n   📝 {article['summary'][:60]}..."
        lines.append(f"🆔 `{article['id']}` - {article['title']}")
        if date:
            lines.append(f"   📅 {date}{summary_preview}\n")
        else:
            lines.append(f"   {summary_preview}\n")
        buttons.append(
            [InlineKeyboardButton(
                text=f"📄 {article['title'][:35]}...",
                callback_data=f"history_article_{article['id']}"
            )]
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ 上一頁", callback_data=f"history_page_{feed_index}_{page-1}")
        )
    if total > (page + 1) * per_page:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️ 下一頁", callback_data=f"history_page_{feed_index}_{page+1}")
        )
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="🔙 返回來源列表", callback_data="menu_history")])
    buttons.append([InlineKeyboardButton(text="🏠 主選單", callback_data="menu_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("history_article_"))
async def callback_history_article(callback: types.CallbackQuery):
    article_id = int(callback.data.split("_")[2])
    article = await db.get_article_by_id(article_id)

    if not article:
        await callback.message.edit_text("⚠️ 找不到這篇文章", reply_markup=back_button())
        await callback.answer()
        return

    if article.get("summary"):
        summary = article["summary"]
    else:
        await callback.message.edit_text("🔄 正在生成摘要...", reply_markup=back_button())
        await callback.answer()
        content = article.get("content", "")
        if not content:
            await callback.message.edit_text("⚠️ 這篇文章沒有可用的內容", reply_markup=back_button())
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
        f"{summary}"
    )

    feed_url = article.get("feed_url", "")
    feeds = await db.get_feeds(callback.message.chat.id)
    feed_index = 0
    for i, f in enumerate(feeds):
        if f["url"] == feed_url:
            feed_index = i
            break

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❓ 針對此文提問", callback_data=f"ask_article_{article_id}")],
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
    await callback.answer()

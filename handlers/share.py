import secrets
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from handlers.start import get_main_menu_keyboard

router = Router()


def back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")]]
    )


@router.message(Command("share"))
async def cmd_share(message: types.Message):
    existing = await db.get_shared_feeds(message.chat.id)
    if existing:
        share_code = existing["share_code"]
        bot_info = await message.bot.get_me()
        bot_username = bot_info.username
        link = f"https://t.me/{bot_username}?start={share_code}"

        text = (
            "🔗 **你的分享連結**\n\n"
            f"連結：{link}\n\n"
            "分享此連結給朋友，他們可以查看你的訂閱列表和文章摘要\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "💡 點擊「🔄 重新產生」可重新整理分享連結\n"
            "💡 點擊「❌ 停止分享」可關閉分享功能"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 重新產生", callback_data="share_regenerate")],
                [InlineKeyboardButton(text="❌ 停止分享", callback_data="share_stop")],
                [InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")],
            ]
        )
    else:
        share_code = secrets.token_urlsafe(8)
        await db.create_shared_feed(message.chat.id, share_code)

        bot_info = await message.bot.get_me()
        bot_username = bot_info.username
        link = f"https://t.me/{bot_username}?start={share_code}"

        text = (
            "🔗 **分享功能已啟用**\n\n"
            f"你的分享連結：\n{link}\n\n"
            "分享此連結給朋友，他們可以查看你的訂閱列表和文章摘要\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "💡 朋友點擊連結後，即可查看你的訂閱"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📋 複製連結", callback_data="share_copy")],
                [InlineKeyboardButton(text="❌ 停止分享", callback_data="share_stop")],
                [InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")],
            ]
        )

    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data == "menu_share")
async def callback_menu_share(callback: types.CallbackQuery):
    existing = await db.get_shared_feeds(callback.message.chat.id)
    if existing:
        share_code = existing["share_code"]
        bot_info = await callback.bot.get_me()
        bot_username = bot_info.username
        link = f"https://t.me/{bot_username}?start={share_code}"

        text = (
            "🔗 **你的分享連結**\n\n"
            f"連結：{link}\n\n"
            "分享此連結給朋友，他們可以查看你的訂閱列表和文章摘要\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "💡 點擊「🔄 重新產生」可重新整理分享連結\n"
            "💡 點擊「❌ 停止分享」可關閉分享功能"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 重新產生", callback_data="share_regenerate")],
                [InlineKeyboardButton(text="❌ 停止分享", callback_data="share_stop")],
                [InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")],
            ]
        )
    else:
        share_code = secrets.token_urlsafe(8)
        await db.create_shared_feed(callback.message.chat.id, share_code)

        bot_info = await callback.bot.get_me()
        bot_username = bot_info.username
        link = f"https://t.me/{bot_username}?start={share_code}"

        text = (
            "🔗 **分享功能已啟用**\n\n"
            f"你的分享連結：\n{link}\n\n"
            "分享此連結給朋友，他們可以查看你的訂閱列表和文章摘要\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "💡 朋友點擊連結後，即可查看你的訂閱"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📋 複製連結", callback_data="share_copy")],
                [InlineKeyboardButton(text="❌ 停止分享", callback_data="share_stop")],
                [InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")],
            ]
        )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "share_regenerate")
async def callback_share_regenerate(callback: types.CallbackQuery):
    await db.remove_shared_feed(callback.message.chat.id)
    share_code = secrets.token_urlsafe(8)
    await db.create_shared_feed(callback.message.chat.id, share_code)

    bot_info = await callback.bot.get_me()
    bot_username = bot_info.username
    link = f"https://t.me/{bot_username}?start={share_code}"

    text = (
        "✅ **分享連結已重新產生**\n\n"
        f"新的分享連結：\n{link}\n\n"
        "分享此連結給朋友，他們可以查看你的訂閱列表和文章摘要"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 複製連結", callback_data="share_copy")],
            [InlineKeyboardButton(text="❌ 停止分享", callback_data="share_stop")],
            [InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")],
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "share_copy")
async def callback_share_copy(callback: types.CallbackQuery):
    await callback.answer("連結已複製！", show_alert=True)


@router.callback_query(F.data == "share_stop")
async def callback_share_stop(callback: types.CallbackQuery):
    await db.remove_shared_feed(callback.message.chat.id)
    text = "✅ 分享功能已關閉"
    await callback.message.edit_text(text, reply_markup=back_button())
    await callback.answer()


@router.message(Command("view"))
async def cmd_view(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(
            "請提供分享代碼\n"
            "格式：/view <分享代碼>\n\n"
            "💡 分享代碼會包含在分享連結中"
        )
        return

    share_code = args[1].strip()
    owner_chat_id = await db.get_owner_by_share_code(share_code)

    if not owner_chat_id:
        await message.answer("⚠️ 找不到此分享代碼，請確認代碼是否正確")
        return

    if owner_chat_id == message.chat.id:
        await message.answer("⚠️ 這是你自己的分享連結，無法查看自己的訂閱")
        return

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


@router.callback_query(F.data.startswith("shared_feed_"))
async def callback_shared_feed(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    owner_chat_id = int(parts[2])
    feed_index = int(parts[3])

    feeds = await db.get_feeds(owner_chat_id)
    if feed_index >= len(feeds):
        await callback.message.edit_text("⚠️ 來源不存在", reply_markup=back_button())
        await callback.answer()
        return

    feed = feeds[feed_index]
    feed_url = feed["url"]
    page = 0
    per_page = 5

    articles = await db.get_articles_by_feed(owner_chat_id, feed_url, limit=per_page, offset=page * per_page)
    total = await db.get_articles_by_feed_count(owner_chat_id, feed_url)
    title = feed.get("title") or feed_url.split("//")[-1].split(".")[0]

    if not articles:
        text = f"📭 **{title}**\n\n此來源目前沒有已抓取的文章"
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
                callback_data=f"shared_article_{owner_chat_id}_{article['id']}"
            )]
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ 上一頁", callback_data=f"shared_page_{owner_chat_id}_{feed_index}_{page-1}")
        )
    if total > (page + 1) * per_page:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️ 下一頁", callback_data=f"shared_page_{owner_chat_id}_{feed_index}_{page+1}")
        )
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="🔙 返回列表", callback_data=f"shared_feeds_{owner_chat_id}")])
    buttons.append([InlineKeyboardButton(text="🏠 主選單", callback_data="menu_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("shared_feeds_"))
async def callback_shared_feeds_list(callback: types.CallbackQuery):
    owner_chat_id = int(callback.data.split("_")[2])

    feeds = await db.get_feeds(owner_chat_id)
    if not feeds:
        await callback.message.edit_text("📭 此用戶目前沒有訂閱任何來源", reply_markup=back_button())
        await callback.answer()
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

    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("shared_page_"))
async def callback_shared_page(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    owner_chat_id = int(parts[2])
    feed_index = int(parts[3])
    page = int(parts[4])

    feeds = await db.get_feeds(owner_chat_id)
    if feed_index >= len(feeds):
        await callback.message.edit_text("⚠️ 來源不存在", reply_markup=back_button())
        await callback.answer()
        return

    feed = feeds[feed_index]
    feed_url = feed["url"]
    per_page = 5

    articles = await db.get_articles_by_feed(owner_chat_id, feed_url, limit=per_page, offset=page * per_page)
    total = await db.get_articles_by_feed_count(owner_chat_id, feed_url)
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
                callback_data=f"shared_article_{owner_chat_id}_{article['id']}"
            )]
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ 上一頁", callback_data=f"shared_page_{owner_chat_id}_{feed_index}_{page-1}")
        )
    if total > (page + 1) * per_page:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️ 下一頁", callback_data=f"shared_page_{owner_chat_id}_{feed_index}_{page+1}")
        )
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="🔙 返回列表", callback_data=f"shared_feeds_{owner_chat_id}")])
    buttons.append([InlineKeyboardButton(text="🏠 主選單", callback_data="menu_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("shared_article_"))
async def callback_shared_article(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    owner_chat_id = int(parts[2])
    article_id = int(parts[3])

    article = await db.get_article_by_id(article_id)
    if not article:
        await callback.message.edit_text("⚠️ 找不到這篇文章", reply_markup=back_button())
        await callback.answer()
        return

    text = (
        f"📄 **{article['title']}**\n\n"
        f"👤 作者：{article.get('author', 'Unknown')}\n"
        f"📅 發布：{article.get('published_at', 'Unknown')}\n"
        f"🔗 連結：{article.get('url', '')}\n\n"
    )

    if article.get("summary"):
        text += (
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📝 **AI 摘要：**\n\n"
            f"{article['summary']}"
        )
    else:
        text += "📝 摘要尚未生成"

    feed_url = article.get("feed_url", "")
    feeds = await db.get_feeds(owner_chat_id)
    feed_index = 0
    for i, f in enumerate(feeds):
        if f["url"] == feed_url:
            feed_index = i
            break

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ 返回列表", callback_data=f"shared_feed_{owner_chat_id}_{feed_index}"),
                InlineKeyboardButton(text="🏠 主選單", callback_data="menu_back"),
            ],
        ]
    )

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)
    await callback.answer()

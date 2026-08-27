import secrets
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from substack_fetcher import fetch_feed

router = Router()


def back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")]]
    )


@router.message(Command("share"))
async def cmd_share(message: types.Message):
    args = message.text.split(maxsplit=1)
    max_uses = 0

    if len(args) >= 2:
        try:
            max_uses = int(args[1].strip())
        except ValueError:
            pass

    existing = await db.get_shared_feeds(message.chat.id)
    if existing:
        share_code = existing["share_code"]
        bot_info = await message.bot.get_me()
        bot_username = bot_info.username
        link = f"https://t.me/{bot_username}?start={share_code}"

        text = (
            "🔗 **你的分享連結**\n\n"
            f"連結：{link}\n\n"
            "分享此連結給朋友，他們可以查看你的訂閱列表\n\n"
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
        await db.create_shared_feed(message.chat.id, share_code, max_uses)

        bot_info = await message.bot.get_me()
        bot_username = bot_info.username
        link = f"https://t.me/{bot_username}?start={share_code}"

        uses_text = f"（僅限 {max_uses} 次使用）" if max_uses > 0 else "（不限次數）"
        text = (
            "🔗 **分享功能已啟用**\n\n"
            f"你的分享連結：\n{link}\n\n"
            f"使用次數限制：{uses_text}\n\n"
            "分享此連結給朋友，他們可以查看你的訂閱列表\n\n"
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
            "分享此連結給朋友，他們可以查看你的訂閱列表\n\n"
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
            "分享此連結給朋友，他們可以查看你的訂閱列表\n\n"
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
    existing = await db.get_shared_feeds(callback.message.chat.id)
    max_uses = existing.get("max_uses", 0) if existing else 0

    await db.remove_shared_feed(callback.message.chat.id)
    share_code = secrets.token_urlsafe(8)
    await db.create_shared_feed(callback.message.chat.id, share_code, max_uses)

    bot_info = await callback.bot.get_me()
    bot_username = bot_info.username
    link = f"https://t.me/{bot_username}?start={share_code}"

    uses_text = f"（僅限 {max_uses} 次使用）" if max_uses > 0 else "（不限次數）"
    text = (
        "✅ **分享連結已重新產生**\n\n"
        f"新的分享連結：\n{link}\n\n"
        f"使用次數限制：{uses_text}"
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
        await message.answer("⚠️ 此分享連結已過期或不存在")
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
        title = feed.get("title") or feed["url"].split("//")[-1].split(".")[0]
        lines.append(f"{i+1}. {title}")
        buttons.append(
            [InlineKeyboardButton(
                text=f"📰 {title}",
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
    title = feed.get("title") or feed_url.split("//")[-1].split(".")[0]

    await callback.message.edit_text(f"🔄 正在抓取 **{title}** 的最新文章...", reply_markup=back_button(), parse_mode="Markdown")
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
                callback_data=f"shared_view_{owner_chat_id}_{feed_index}_{i}"
            )]
        )

    buttons.append([InlineKeyboardButton(text="🔙 返回列表", callback_data=f"shared_feeds_{owner_chat_id}")])
    buttons.append([InlineKeyboardButton(text="🏠 主選單", callback_data="menu_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data.startswith("shared_view_"))
async def callback_shared_view(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    owner_chat_id = int(parts[2])
    feed_index = int(parts[3])
    article_index = int(parts[4])

    feeds = await db.get_feeds(owner_chat_id)
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

    text = (
        f"📄 **{article['title']}**\n\n"
        f"👤 作者：{article.get('author', 'Unknown')}\n"
        f"📅 發布：{article.get('published_at', 'Unknown')}\n"
        f"🔗 連結：{article.get('url', '')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💡 連線查看完整文章"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 閱讀全文", url=article.get("url", ""))],
            [
                InlineKeyboardButton(text="⬅️ 返回列表", callback_data=f"shared_feed_{owner_chat_id}_{feed_index}"),
                InlineKeyboardButton(text="🏠 主選單", callback_data="menu_back"),
            ],
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)


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
        title = feed.get("title") or feed["url"].split("//")[-1].split(".")[0]
        lines.append(f"{i+1}. {title}")
        buttons.append(
            [InlineKeyboardButton(
                text=f"📰 {title}",
                callback_data=f"shared_feed_{owner_chat_id}_{i}"
            )]
        )

    buttons.append([InlineKeyboardButton(text="🔙 返回主選單", callback_data="menu_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

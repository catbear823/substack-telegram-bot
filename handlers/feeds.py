from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re
import httpx

import database as db

router = Router()


class AddFeedState(StatesGroup):
    waiting_for_url = State()


def is_valid_substack_url(url: str) -> bool:
    patterns = [
        r"https?://[^\s]+\.substack\.com",
        r"https?://substack\.com/@[^\s]+",
    ]
    return any(re.search(p, url) for p in patterns)


async def resolve_substack_url(url: str) -> str:
    if "substack.com/@" in url:
        username = url.split("substack.com/@")[-1].strip("/")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://substack.com/@{username}",
                    follow_redirects=True,
                    headers={"User-Agent": "SubstackBot/1.0"},
                )
                text = resp.text
                match = re.search(r'https://([a-zA-Z0-9-]+)\.substack\.com', text)
                if match:
                    return f"https://{match.group(1)}.substack.com"
        except Exception:
            pass
        return f"https://{username}.substack.com"
    return url


async def process_add_feed(message: Message, url: str):
    if not url.startswith("http"):
        url = "https://" + url

    status_msg = await message.answer("🔄 正在解析網址...")
    url = await resolve_substack_url(url)

    existing = await db.get_feeds(message.chat.id)
    if any(f["url"].rstrip("/") == url.rstrip("/") for f in existing):
        await status_msg.edit_text("⚠️ 這個來源已經在訂閱列表中了")
        return

    title = url.split("//")[-1].split(".")[0]
    success = await db.add_feed(message.chat.id, url, title=title)
    if success:
        await status_msg.edit_text(
            f"✅ 已新增訂閱：\n{url}\n\n"
            "點擊「🔄 抓取文章」開始抓取最新內容"
        )
    else:
        await status_msg.edit_text("❌ 新增失敗，請稍後再試")


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await state.set_state(AddFeedState.waiting_for_url)
        await message.answer(
            "請提供 Substack 網址\n"
            "格式：/add https://example.substack.com\n"
            "或：/add https://substack.com/@username"
        )
        return

    url = args[1].strip()
    if not is_valid_substack_url(url):
        await message.answer(
            "⚠️ 請提供有效的 Substack 網址\n\n"
            "支援格式：\n"
            "• https://example.substack.com\n"
            "• https://substack.com/@username"
        )
        return

    await process_add_feed(message, url)


@router.message(AddFeedState.waiting_for_url, F.text)
async def handle_add_feed_url(message: Message, state: FSMContext):
    await state.clear()
    url = message.text.strip()

    if not is_valid_substack_url(url):
        await message.answer(
            "⚠️ 請提供有效的 Substack 網址\n\n"
            "支援格式：\n"
            "• https://example.substack.com\n"
            "• https://substack.com/@username"
        )
        return

    await process_add_feed(message, url)


@router.message(Command("remove"))
async def cmd_remove(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("請提供要移除的 Substack 網址")
        return

    url = args[1].strip()
    success = await db.remove_feed(message.chat.id, url)
    if success:
        await message.answer(f"✅ 已移除：{url}")
    else:
        await message.answer("⚠️ 找不到這個訂閱來源")


@router.message(Command("list"))
async def cmd_list(message: Message):
    feeds = await db.get_feeds(message.chat.id)
    if not feeds:
        await message.answer(
            "📭 目前沒有訂閱任何來源\n\n"
            "使用 /add <url> 新增你的第一個 Substack 訂閱"
        )
        return

    lines = ["📚 **你的訂閱列表：**\n"]
    for i, feed in enumerate(feeds, 1):
        title = feed.get("title") or feed["url"].split("//")[-1].split(".")[0]
        lines.append(f"{i}. {title}")
        lines.append(f"   🔗 {feed['url']}\n")

    lines.append(f"共 {len(feeds)} 個來源")
    await message.answer("\n".join(lines), parse_mode="Markdown")

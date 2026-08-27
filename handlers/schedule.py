from aiogram import Router, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import database as db
from substack_fetcher import fetch_all_feeds

router = Router()
scheduler = AsyncIOScheduler()


async def scheduled_fetch(chat_id: int):
    try:
        results = await fetch_all_feeds(chat_id)
        from aiogram import Bot
        from config import TELEGRAM_BOT_TOKEN

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        if results["total_new"] > 0:
            await bot.send_message(
                chat_id,
                f"⏰ 每日自動抓取完成！\n新增 {results['total_new']} 篇新文章\n\n"
                "使用 /latest 查看摘要",
            )
        await bot.session.close()
    except Exception as e:
        print(f"Scheduled fetch error for chat {chat_id}: {e}")


@router.message(Command("schedule"))
async def cmd_schedule(message: types.Message):
    args = message.text.split(maxsplit=1)
    feeds = await db.get_feeds(message.chat.id)

    if not feeds:
        await message.answer(
            "📭 請先新增訂閱來源（/add <url>），再設定排程"
        )
        return

    job_id = f"fetch_{message.chat.id}"
    existing_job = scheduler.get_job(job_id)

    if existing_job:
        existing_job.remove()
        await message.answer("⏹️ 已停止自動抓取排程\n\n使用 /schedule 重新設定")
        return

    hour = 8
    minute = 0
    if len(args) > 1:
        time_str = args[1].strip()
        parts = time_str.split(":")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            hour = int(parts[0])
            minute = int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                await message.answer("⚠️ 時間格式無效，請使用 HH:MM（24小時制）")
                return

    scheduler.add_job(
        scheduled_fetch,
        CronTrigger(hour=hour, minute=minute),
        args=[message.chat.id],
        id=job_id,
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()

    await message.answer(
        f"✅ 已設定每日自動抓取\n"
        f"⏰ 時間：每天 {hour:02d}:{minute:02d}\n"
        f"📰 來源：{len(feeds)} 個\n\n"
        f"再次使用 /schedule 可停止自動抓取"
    )

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

import config
from database import init_db
from handlers import (
    start_router,
    feeds_router,
    fetch_router,
    summary_router,
    ask_router,
    schedule_router,
    callback_router,
)


async def main():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    await init_db()

    bot = Bot(
        token=config.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="Markdown"),
    )

    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(feeds_router)
    dp.include_router(fetch_router)
    dp.include_router(summary_router)
    dp.include_router(ask_router)
    dp.include_router(schedule_router)
    dp.include_router(callback_router)

    logging.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

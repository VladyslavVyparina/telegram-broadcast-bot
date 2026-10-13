from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import Config
from bot.database.db import Database
from bot.handlers import (
    auto_reply,
    autopost,
    broadcast,
    chat_events,
    content,
    menu,
    quick_reply,
    settings_panel,
    start,
    subscription,
    system,
    user_messages,
    users_admin,
    verification,
)
from bot.services.broadcaster import BackgroundSchedulers
from bot.services.scheduler import AutoPostScheduler

logger = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(verification.router)
    dp.include_router(menu.router)
    dp.include_router(settings_panel.router)
    dp.include_router(system.router)
    dp.include_router(broadcast.router)
    dp.include_router(content.router)
    dp.include_router(subscription.router)
    dp.include_router(users_admin.router)
    dp.include_router(autopost.router)
    dp.include_router(quick_reply.router)
    dp.include_router(chat_events.router)
    dp.include_router(auto_reply.router)
    dp.include_router(user_messages.router)
    return dp


async def run_bot_instance(config: Config) -> None:
    """Run one clone/main bot until cancelled."""
    db = Database(config.database_path)
    await db.connect()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            protect_content=True,
        ),
    )
    dp = build_dispatcher()

    autopost_scheduler = AutoPostScheduler(bot, db, config.admin_id)
    autopost_scheduler.start()
    bg_schedulers = BackgroundSchedulers(bot, db, config.admin_id)
    bg_schedulers.start()

    logger.info("Bot instance started. Admin ID: %s", config.admin_id)
    try:
        await dp.start_polling(
            bot,
            config=config,
            db=db,
            scheduler=autopost_scheduler,
        )
    except asyncio.CancelledError:
        logger.info("Bot instance stopped. Admin ID: %s", config.admin_id)
        raise
    finally:
        autopost_scheduler.stop()
        bg_schedulers.stop()
        await db.close()
        await bot.session.close()

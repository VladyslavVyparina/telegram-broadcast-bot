from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot_public.config import Config, load_config
from bot_public.database.db import PlatformDB
from bot_public.handlers import admin, admin_ops, create, payment, start
from bot_public.handlers.wallet_webhook import start_wallet_webhook_server
from bot_public.services.child_manager import ChildManager
from bot_public.services.crypto_poll import poll_pending_cryptobot_orders
from bot_public.services.notify import notify_expiry_reminder
from bot_public.services.wallet_poll import poll_pending_wallet_orders

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def expiry_loop(
    bot: Bot,
    platform_db: PlatformDB,
    child_manager: ChildManager,
    config: Config,
) -> None:
    while True:
        try:
            await child_manager.ensure_running()
            await child_manager.stop_expired()
            await poll_pending_wallet_orders(bot, platform_db, child_manager, config)
            await poll_pending_cryptobot_orders(bot, platform_db, child_manager, config)
            price = await platform_db.subscription_price()
            for child in await platform_db.get_bots_needing_reminder(hours=24):
                owner_id = int(child["owner_id"])
                lang = await platform_db.get_user_language(owner_id)
                days = platform_db.days_remaining(child.get("expires_at"))
                label = child.get("bot_name") or child.get("bot_username") or "—"
                await notify_expiry_reminder(
                    bot,
                    owner_id,
                    lang,
                    child_bot_id=int(child["id"]),
                    bot_name=label,
                    days_left=days,
                    price=price,
                )
                await platform_db.mark_reminder_sent(int(child["id"]))
        except Exception as exc:
            logger.exception("Expiry loop error: %s", exc)
        await asyncio.sleep(60)


async def main() -> None:
    config = load_config()
    platform_db = PlatformDB(config.database_path)
    await platform_db.connect()

    child_manager = ChildManager(platform_db)
    await child_manager.start_all_active()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            protect_content=True,
        ),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(create.router)
    dp.include_router(payment.router)
    dp.include_router(admin.router)
    dp.include_router(admin_ops.router)

    expiry_task = asyncio.create_task(
        expiry_loop(bot, platform_db, child_manager, config),
    )
    webhook_runner = None
    try:
        webhook_runner = await start_wallet_webhook_server(
            bot, platform_db, child_manager, config,
        )
    except Exception as exc:
        logger.warning(
            "Payment webhook server failed (bot will use polling): %s",
            exc,
        )

    logger.info(
        "Platform bot started (%s child bots, stars+crypto: wallet=%s cryptobot=%s)",
        child_manager.running_count(),
        "on" if config.wallet_pay_enabled else "off",
        "on" if config.crypto_pay_enabled else "off",
    )
    try:
        await dp.start_polling(
            bot,
            config=config,
            platform_db=platform_db,
            child_manager=child_manager,
        )
    finally:
        expiry_task.cancel()
        if webhook_runner:
            await webhook_runner.cleanup()
        await child_manager.shutdown()
        await platform_db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

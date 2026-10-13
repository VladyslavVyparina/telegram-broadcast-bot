"""Poll Wallet Pay for paid orders (no webhook / domain required)."""

from __future__ import annotations

import logging

from aiogram import Bot

from bot_public.config import Config
from bot_public.database.db import PlatformDB
from bot_public.services.child_manager import ChildManager
from bot_public.services.payment_fulfillment import fulfill_crypto_order
from bot_public.services.wallet_pay import WalletPayError, get_order_status

logger = logging.getLogger(__name__)

_FAILED_STATUSES = frozenset({"EXPIRED", "CANCELLED", "FAILED"})


async def poll_pending_wallet_orders(
    bot: Bot,
    platform_db: PlatformDB,
    child_manager: ChildManager,
    config: Config,
) -> None:
    if not config.wallet_pay_enabled:
        return

    orders = await platform_db.get_pending_wallet_orders()
    for order in orders:
        wallet_order_id = order.get("wallet_order_id")
        external_id = order.get("external_id", "?")
        if not wallet_order_id:
            continue
        try:
            status = await get_order_status(
                config.wallet_pay_api_key,
                int(wallet_order_id),
            )
        except WalletPayError as exc:
            logger.warning("Wallet poll %s failed: %s", external_id, exc)
            continue

        if status == "PAID":
            await fulfill_crypto_order(
                bot,
                platform_db,
                child_manager,
                config,
                order=order,
            )
        elif status in _FAILED_STATUSES:
            await platform_db.mark_wallet_order_failed(str(external_id))

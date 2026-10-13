"""Poll Crypto Pay for paid invoices (no webhook required)."""

from __future__ import annotations

import logging

from aiogram import Bot

from bot_public.config import Config
from bot_public.database.db import PlatformDB
from bot_public.services.child_manager import ChildManager
from bot_public.services.crypto_pay import PROVIDER_CRYPTOBOT, CryptoPayError, get_invoice_status
from bot_public.services.payment_fulfillment import fulfill_crypto_order

logger = logging.getLogger(__name__)

_FAILED_STATUSES = frozenset({"expired"})


async def poll_pending_cryptobot_orders(
    bot: Bot,
    platform_db: PlatformDB,
    child_manager: ChildManager,
    config: Config,
) -> None:
    if not config.crypto_pay_enabled:
        return

    orders = await platform_db.get_pending_crypto_orders(PROVIDER_CRYPTOBOT)
    for order in orders:
        invoice_id = order.get("wallet_order_id")
        external_id = order.get("external_id", "?")
        if not invoice_id:
            continue
        try:
            status = await get_invoice_status(
                config.crypto_pay_api_token,
                int(invoice_id),
                testnet=config.crypto_pay_testnet,
            )
        except CryptoPayError as exc:
            logger.warning("Crypto Pay poll %s failed: %s", external_id, exc)
            continue

        if status == "paid":
            await fulfill_crypto_order(
                bot,
                platform_db,
                child_manager,
                config,
                order=order,
            )
        elif status in _FAILED_STATUSES:
            await platform_db.mark_wallet_order_failed(str(external_id))

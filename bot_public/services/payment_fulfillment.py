"""Fulfill crypto payment orders (CryptoBot, Wallet Pay)."""

from __future__ import annotations

import logging

from aiogram import Bot

from bot_public.config import Config
from bot_public.database.db import PlatformDB
from bot_public.locales import t
from bot_public.services.child_manager import ChildManager
from bot_public.services.crypto_pay import PROVIDER_CRYPTOBOT
from bot_public.services.notify import notify_purchase
from bot.utils.helpers import format_display_time

logger = logging.getLogger(__name__)


def _payment_types(provider: str, base: str) -> tuple[str, str]:
    if provider == PROVIDER_CRYPTOBOT:
        return f"cryptobot_{base}", f"cryptobot:{base}"
    return f"wallet_{base}", f"wallet:{base}"


async def fulfill_crypto_order(
    bot: Bot,
    platform_db: PlatformDB,
    child_manager: ChildManager,
    config: Config,
    *,
    order: dict,
) -> bool:
    if order.get("status") != "pending":
        return False

    user_id = int(order["user_id"])
    days = int(order["days"])
    payment_type = order["payment_type"]
    external_id = order["external_id"]
    currency = order.get("currency", "")
    amount = order.get("amount", "")
    provider = order.get("provider", "wallet_pay")

    user = await platform_db.get_user(user_id)
    lang = await platform_db.get_user_language(user_id)
    create_type, payload_prefix = _payment_types(provider, "create")
    renew_type, _ = _payment_types(provider, "renew")

    if payment_type == "create":
        if not await platform_db.mark_wallet_order_paid(external_id):
            return False
        await platform_db.record_payment(
            user_id,
            0,
            days,
            create_type,
            payload=f"{payload_prefix}:{currency}:{amount}:{external_id}",
        )
        await notify_purchase(
            bot,
            config,
            platform_db,
            user_id=user_id,
            first_name=user.get("first_name") if user else None,
            username=user.get("username") if user else None,
            amount=0,
            days=days,
            bot_name=None,
            payment_type=create_type,
            wallet_amount=f"{amount} {currency}",
        )
        await bot.send_message(user_id, t(lang, "send_token"))
        return True

    if payment_type == "renew":
        bot_id = order.get("child_bot_id")
        if not bot_id:
            logger.error("Crypto renew order %s missing child_bot_id", external_id)
            return False
        child = await platform_db.get_child_bot(int(bot_id))
        if not child or int(child["owner_id"]) != user_id:
            logger.error("Crypto renew order %s child mismatch", external_id)
            return False

        if not await platform_db.mark_wallet_order_paid(external_id):
            return False

        await platform_db.record_payment(
            user_id,
            0,
            days,
            renew_type,
            child_bot_id=int(bot_id),
            payload=f"{payload_prefix}:{currency}:{amount}:{external_id}",
        )
        expires = await platform_db.extend_child_bot(int(bot_id), days)
        child = await platform_db.get_child_bot(int(bot_id))
        await child_manager.restart_child(child)
        await notify_purchase(
            bot,
            config,
            platform_db,
            user_id=user_id,
            first_name=user.get("first_name") if user else None,
            username=user.get("username") if user else None,
            amount=0,
            days=days,
            bot_name=child.get("bot_name") if child else None,
            payment_type=renew_type,
            wallet_amount=f"{amount} {currency}",
        )
        username = child.get("bot_username") or "bot" if child else "bot"
        date_str = format_display_time(expires, config.timezone)
        await bot.send_message(
            user_id,
            t(lang, "renew_success", username=username, date=date_str),
        )
        return True

    logger.error("Unknown payment_type %s for %s", payment_type, external_id)
    return False

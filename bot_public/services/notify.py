from __future__ import annotations

import logging

from aiogram import Bot

from bot_public.config import PLATFORM_ADMIN_IDS, STARS_OWNER_ID, Config
from bot_public.database.db import PlatformDB
from bot_public.locales import t

logger = logging.getLogger(__name__)


async def notify_purchase(
    bot: Bot,
    config: Config,
    db: PlatformDB,
    *,
    user_id: int,
    first_name: str | None,
    username: str | None,
    amount: int,
    days: int,
    bot_name: str | None,
    payment_type: str,
    wallet_amount: str | None = None,
) -> None:
    name = first_name or username or str(user_id)
    uname = f"@{username}" if username else "—"
    bot_line = bot_name or "—"
    if payment_type in ("wallet_create", "wallet_renew", "cryptobot_create", "cryptobot_renew"):
        type_ar = {
            "wallet_create": "إنشاء بوت (Wallet)",
            "wallet_renew": "تجديد (Wallet)",
            "cryptobot_create": "إنشاء بوت (CryptoBot)",
            "cryptobot_renew": "تجديد (CryptoBot)",
        }.get(payment_type, payment_type)
        pay_line = f"👛 {wallet_amount or 'Wallet'}"
        balance_hint = ""
    elif payment_type == "create":
        type_ar = "إنشاء بوت"
        pay_line = f"⭐ {amount}"
        balance_hint = (
            f"💳 <b>+{amount}⭐</b> على رصيد بوت المنصة"
        )
    else:
        type_ar = "تجديد اشتراك"
        pay_line = f"⭐ {amount}"
        balance_hint = (
            f"💳 <b>+{amount}⭐</b> على رصيد بوت المنصة"
        )
    text = (
        f"💰 <b>عملية شراء جديدة</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👤 {name} ({uname})\n"
        f"🆔 <code>{user_id}</code>\n"
        f"📦 {type_ar}\n"
        f"🤖 {bot_line}\n"
        f"{pay_line} | 📅 {days} يوم\n"
    )
    if balance_hint:
        text += f"\n{balance_hint}"
    recipients = set(PLATFORM_ADMIN_IDS)
    recipients.add(STARS_OWNER_ID)
    for admin_id in recipients:
        try:
            await bot.send_message(admin_id, text)
        except Exception as exc:
            logger.warning("Notify admin %s failed: %s", admin_id, exc)

    platform = await db.platform_bot_username()
    if payment_type not in ("wallet_create", "wallet_renew", "cryptobot_create", "cryptobot_renew"):
        stars_hint = (
            f"⭐ <b>+{amount} Stars</b> зараховано на баланс "
            f"<b>@{platform}</b>\n\n"
            f"Переглянути баланс (тільки власник бота в BotFather):\n"
            f"• BotFather → /mybots → {platform} → Balance\n"
            f"• або Telegram → @{platform} → Manage Bot → Balance"
        )
        try:
            await bot.send_message(STARS_OWNER_ID, stars_hint)
        except Exception as exc:
            logger.warning("Stars owner notify %s failed: %s", STARS_OWNER_ID, exc)


async def notify_expiry_reminder(
    bot: Bot,
    owner_id: int,
    lang: str,
    *,
    child_bot_id: int,
    bot_name: str | None,
    days_left: int,
    price: int,
) -> None:
    bot_line = bot_name or "—"
    text = t(
        lang,
        "reminder_expiry",
        bot=bot_line,
        days=days_left,
        price=price,
    )
    try:
        from bot_public.keyboards.common import renew_kb

        await bot.send_message(
            owner_id, text, reply_markup=renew_kb(lang, child_bot_id)
        )
    except Exception:
        pass
from __future__ import annotations

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import Config
from bot.database.db import Database
from bot.locales import t
from bot.utils.subscription import days_to_months, format_months_label, months_to_days


def paywall_kb(lang: str, *, show_status: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=t(lang, "paid_access_buy_btn"),
                callback_data="fin:buyaccess",
            )
        ]
    ]
    if show_status:
        rows.append([
            InlineKeyboardButton(
                text=t(lang, "paid_access_status_btn"),
                callback_data="fin:status",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def get_subscription_period(db: Database) -> tuple[str, str, str]:
    """Return (price, months, months_label)."""
    price = await db.get_cfg("finance_access_price", "100")
    months = await db.get_cfg("finance_access_months", "1")
    if not months.isdigit():
        days = await db.get_cfg("finance_access_days", "30")
        months = str(days_to_months(int(days)))
    label = format_months_label(int(months))
    return price, months, label


async def get_subscription_days(db: Database) -> int:
    days_raw = await db.get_cfg("finance_access_days", "30")
    if days_raw.isdigit():
        return int(days_raw)
    months = await db.get_cfg("finance_access_months", "1")
    return months_to_days(int(months) if months.isdigit() else 1)


async def user_has_bot_access(db: Database, user_id: int, config: Config) -> bool:
    if await db.is_admin(user_id, config.admin_id):
        return True
    if not await db.get_cfg_bool("finance_access_enabled"):
        return True
    return await db.has_paid_access(user_id)


async def get_paywall_text(db: Database, user_id: int, lang: str) -> str:
    price, months, months_label = await get_subscription_period(db)
    if await db.get_access_expires_at(user_id):
        return t(lang, "paid_access_expired", price=price, months_label=months_label)
    return t(lang, "paid_access_required", price=price, months_label=months_label)


async def get_subscription_status_text(
    db: Database, user_id: int, lang: str, timezone: str
) -> str:
    from bot.utils.helpers import format_display_time

    if not await db.has_paid_access(user_id):
        expires = await db.get_access_expires_at(user_id)
        price, _, months_label = await get_subscription_period(db)
        if expires:
            return t(lang, "paid_access_expired", price=price, months_label=months_label)
        return t(lang, "paid_access_status_none", price=price, months_label=months_label)

    days_left = await db.get_access_days_remaining(user_id) or 0
    expires = await db.get_access_expires_at(user_id)
    date_str = format_display_time(expires, timezone)
    return t(lang, "paid_access_status_active", days=days_left, date=date_str)


async def send_paywall(target: Message | CallbackQuery, db: Database, config: Config) -> None:
    if not target.from_user:
        return
    lang = config.default_language
    text = await get_paywall_text(db, target.from_user.id, lang)
    kb = paywall_kb(lang, show_status=True)
    if isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb)


async def block_if_no_access(
    event: Message | CallbackQuery,
    db: Database,
    config: Config,
    *,
    private_only: bool = True,
) -> bool:
    """Return True if the handler should stop (user has no paid access)."""
    user = event.from_user
    if not user:
        return False
    if private_only:
        chat = event.chat if isinstance(event, Message) else event.message.chat
        if chat.type != "private":
            return False
    if await user_has_bot_access(db, user.id, config):
        return False
    await send_paywall(event, db, config)
    return True

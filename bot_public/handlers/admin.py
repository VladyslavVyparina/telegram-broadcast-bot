from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot_public.config import STARS_OWNER_ID, is_platform_owner
from bot_public.database.db import PlatformDB
from bot_public.handlers.start import _lang
from bot_public.keyboards.admin_kb import (
    admin_billing_kb,
    admin_features_kb,
    admin_hub_kb,
)
from bot_public.keyboards.common import back_kb, main_kb
from bot_public.locales import t
from bot_public.services.child_manager import ChildManager
from bot_public.utils.crypto_prices import normalize_usdt_price
from bot_public.utils.states import AdminState
from bot_public.services.wallet_pay import WalletPayError

router = Router()


async def _resolve_user_id(text: str, platform_db: PlatformDB, bot: Bot) -> int | None:
    raw = text.strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    username = raw.lstrip("@")
    if not username:
        return None
    found = await platform_db.get_user_by_username(username)
    if found:
        return int(found["user_id"])
    try:
        chat = await bot.get_chat(f"@{username}")
        return int(chat.id)
    except Exception:
        return None


def _parse_duration(text: str) -> int | None:
    raw = text.strip().lower().replace(" ", "")
    if not raw:
        return None
    if raw.endswith("m") or raw.endswith("м"):
        months = raw[:-1]
        if months.isdigit() and int(months) > 0:
            return int(months) * 30
        return None
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return None


async def _admin_hub_text(platform_db: PlatformDB, lang: str) -> str:
    stats = await platform_db.get_stats()
    paid = await platform_db.is_paid_mode()
    mode = t(lang, "admin_mode_free" if not paid else "admin_mode_paid")
    return (
        t(lang, "admin_hub_title")
        + "\n"
        + t(lang, "admin_stats", **stats)
        + "\n"
        + mode
    )


async def _admin_billing_text(platform_db: PlatformDB, lang: str) -> str:
    price = await platform_db.subscription_price()
    days = await platform_db.subscription_days()
    months = max(1, round(days / 30))
    usdt = await platform_db.crypto_price_usdt()
    paid = await platform_db.is_paid_mode()
    mode = t(lang, "admin_mode_free" if not paid else "admin_mode_paid")
    return (
        t(lang, "admin_billing_title")
        + "\n"
        + t(lang, "admin_current_plan", price=price, days=days, months=months)
        + "\n"
        + t(lang, "admin_crypto_plan", usdt_price=usdt)
        + "\n"
        + mode
    )


@router.callback_query(F.data == "admin:panel")
async def admin_panel(callback: CallbackQuery, platform_db: PlatformDB, state: FSMContext) -> None:
    if not callback.from_user or not is_platform_owner(callback.from_user.id):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    await state.clear()
    lang = await _lang(platform_db, callback.from_user.id)
    paid = await platform_db.is_paid_mode()
    text = await _admin_hub_text(platform_db, lang)
    await callback.message.edit_text(text, reply_markup=admin_hub_kb(lang, paid_mode=paid))
    await callback.answer()


@router.callback_query(F.data == "admin:section:features")
async def admin_section_features(
    callback: CallbackQuery, platform_db: PlatformDB, state: FSMContext,
) -> None:
    if not callback.from_user or not is_platform_owner(callback.from_user.id):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    await state.clear()
    lang = await _lang(platform_db, callback.from_user.id)
    await callback.message.edit_text(
        t(lang, "admin_features_text"),
        reply_markup=admin_features_kb(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:section:billing")
async def admin_section_billing(
    callback: CallbackQuery, platform_db: PlatformDB, state: FSMContext,
) -> None:
    if not callback.from_user or not is_platform_owner(callback.from_user.id):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    await state.clear()
    lang = await _lang(platform_db, callback.from_user.id)
    text = await _admin_billing_text(platform_db, lang)
    await callback.message.edit_text(text, reply_markup=admin_billing_kb(lang))
    await callback.answer()


@router.callback_query(F.data == "admin:toggle_paid")
async def admin_toggle_paid(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    child_manager: ChildManager,
) -> None:
    if not callback.from_user or not is_platform_owner(callback.from_user.id):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    lang = await _lang(platform_db, callback.from_user.id)
    paid = await platform_db.is_paid_mode()
    if paid:
        await platform_db.set_cfg("platform_paid_mode", "0")
        restored = await platform_db.restore_all_access(child_manager)
        await callback.answer(
            t(lang, "admin_mode_switched_free", count=restored),
            show_alert=True,
        )
    else:
        await platform_db.set_cfg("platform_paid_mode", "1")
        revoked = await platform_db.revoke_all_access(child_manager)
        await callback.answer(
            t(lang, "admin_mode_switched_paid", count=revoked),
            show_alert=True,
        )
    text = await _admin_hub_text(platform_db, lang)
    paid_now = await platform_db.is_paid_mode()
    await callback.message.edit_text(text, reply_markup=admin_hub_kb(lang, paid_mode=paid_now))


@router.callback_query(F.data == "admin:grant")
async def admin_grant_start(
    callback: CallbackQuery, platform_db: PlatformDB, state: FSMContext,
) -> None:
    if not callback.from_user or not is_platform_owner(callback.from_user.id):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    lang = await _lang(platform_db, callback.from_user.id)
    await state.set_state(AdminState.waiting_grant_user)
    await callback.message.edit_text(
        t(lang, "admin_grant_prompt"),
        reply_markup=back_kb(lang, "admin:section:billing"),
    )
    await callback.answer()


@router.message(AdminState.waiting_grant_user, F.text)
async def admin_grant_save(
    message: Message,
    platform_db: PlatformDB,
    state: FSMContext,
    bot: Bot,
) -> None:
    if not message.from_user or not is_platform_owner(message.from_user.id):
        return
    if not message.text:
        return
    lang = await _lang(platform_db, message.from_user.id)
    user_id = await _resolve_user_id(message.text, platform_db, bot)
    if user_id is None:
        await message.answer(t(lang, "admin_grant_not_found"))
        return
    days = await platform_db.subscription_days()
    await platform_db.grant_manual_create(user_id, days, admin_id=message.from_user.id)
    await state.clear()
    await message.answer(
        t(lang, "admin_grant_done", user_id=user_id, days=days),
        reply_markup=main_kb(lang, show_admin=True, paid_mode=await platform_db.is_paid_mode()),
    )
    try:
        user_lang = await platform_db.get_user_language(user_id)
        await bot.send_message(user_id, t(user_lang, "grant_access_notify", days=days))
    except Exception:
        pass


@router.callback_query(F.data == "admin:crypto_price_usdt")
async def admin_crypto_price_usdt_start(
    callback: CallbackQuery, platform_db: PlatformDB, state: FSMContext,
) -> None:
    if not callback.from_user or not is_platform_owner(callback.from_user.id):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    lang = await _lang(platform_db, callback.from_user.id)
    current = await platform_db.crypto_price_usdt()
    await state.set_state(AdminState.waiting_crypto_price_usdt)
    await callback.message.edit_text(
        t(lang, "admin_crypto_usdt_prompt", price=current),
        reply_markup=back_kb(lang, "admin:section:billing"),
    )
    await callback.answer()


@router.message(AdminState.waiting_crypto_price_usdt, F.text)
async def admin_crypto_price_usdt_save(
    message: Message, platform_db: PlatformDB, state: FSMContext,
) -> None:
    if not message.from_user or not is_platform_owner(message.from_user.id):
        return
    if not message.text or not message.text.strip():
        return
    lang = await _lang(platform_db, message.from_user.id)
    try:
        price = normalize_usdt_price(message.text.strip()[:32])
    except WalletPayError:
        await message.answer(t(lang, "admin_invalid_crypto_price"))
        return
    await state.clear()
    await platform_db.set_cfg("crypto_price_usdt", price)
    await message.answer(
        t(lang, "admin_crypto_usdt_saved", price=price),
        reply_markup=main_kb(lang, show_admin=True, paid_mode=await platform_db.is_paid_mode()),
    )


@router.callback_query(F.data == "admin:price")
async def admin_set_price(
    callback: CallbackQuery, platform_db: PlatformDB, state: FSMContext,
) -> None:
    if not callback.from_user or not is_platform_owner(callback.from_user.id):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    lang = await _lang(platform_db, callback.from_user.id)
    price = await platform_db.subscription_price()
    await state.set_state(AdminState.waiting_price)
    await callback.message.edit_text(
        t(lang, "admin_set_price_prompt", price=price),
        reply_markup=back_kb(lang, "admin:section:billing"),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:duration")
async def admin_set_duration(
    callback: CallbackQuery, platform_db: PlatformDB, state: FSMContext,
) -> None:
    if not callback.from_user or not is_platform_owner(callback.from_user.id):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    lang = await _lang(platform_db, callback.from_user.id)
    days = await platform_db.subscription_days()
    months = max(1, round(days / 30))
    await state.set_state(AdminState.waiting_duration)
    await callback.message.edit_text(
        t(lang, "admin_set_duration_prompt", days=days, months=months),
        reply_markup=back_kb(lang, "admin:section:billing"),
    )
    await callback.answer()


@router.message(AdminState.waiting_price, F.text)
async def admin_save_price(message: Message, platform_db: PlatformDB, state: FSMContext) -> None:
    if not message.from_user or not is_platform_owner(message.from_user.id):
        return
    if not message.text:
        return
    lang = await _lang(platform_db, message.from_user.id)
    price_raw = message.text.strip().split()[0]
    if not price_raw.isdigit() or int(price_raw) <= 0:
        await message.answer(t(lang, "admin_invalid_price"))
        return
    price = price_raw
    await state.clear()
    await platform_db.set_cfg("subscription_price", price)
    days = await platform_db.subscription_days()
    months = max(1, round(days / 30))
    await message.answer(
        t(lang, "admin_price_saved", price=price, days=days, months=months),
        reply_markup=main_kb(lang, show_admin=True, paid_mode=await platform_db.is_paid_mode()),
    )


@router.message(AdminState.waiting_duration, F.text)
async def admin_save_duration(message: Message, platform_db: PlatformDB, state: FSMContext) -> None:
    if not message.from_user or not is_platform_owner(message.from_user.id):
        return
    if not message.text:
        return
    lang = await _lang(platform_db, message.from_user.id)
    days = _parse_duration(message.text)
    if days is None:
        await message.answer(t(lang, "admin_invalid_duration"))
        return
    await state.clear()
    await platform_db.set_cfg("subscription_days", str(days))
    months = max(1, round(days / 30))
    await platform_db.set_cfg("subscription_months", str(months))
    price = await platform_db.subscription_price()
    await message.answer(
        t(lang, "admin_duration_saved", price=price, days=days, months=months),
        reply_markup=main_kb(lang, show_admin=True, paid_mode=await platform_db.is_paid_mode()),
    )


@router.callback_query(F.data == "admin:stars")
async def admin_stars(
    callback: CallbackQuery, platform_db: PlatformDB, bot: Bot,
) -> None:
    if not callback.from_user or not is_platform_owner(callback.from_user.id):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    lang = await _lang(platform_db, callback.from_user.id)
    stats = await platform_db.get_stats()
    lines = [
        t(lang, "admin_stars_title"),
        t(lang, "admin_stars_db", today=stats["today_stars"], total=stats["total_stars"]),
        t(lang, "admin_stars_owner", owner_id=STARS_OWNER_ID),
    ]
    try:
        tx = await bot.get_star_transactions(limit=20)
        balance = sum(tr.amount for tr in tx.transactions)
        lines.append(t(lang, "admin_stars_telegram", balance=balance))
    except Exception as exc:
        lines.append(t(lang, "admin_stars_api_error", error=str(exc)[:80]))
    lines.append(t(lang, "admin_stars_hint"))
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_kb(lang, "admin:section:billing"),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:purchases")
async def admin_purchases(callback: CallbackQuery, platform_db: PlatformDB) -> None:
    if not callback.from_user or not is_platform_owner(callback.from_user.id):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    lang = await _lang(platform_db, callback.from_user.id)
    payments = await platform_db.get_recent_payments(15)
    lines = [t(lang, "admin_recent")]
    for p in payments:
        name = p.get("first_name") or p.get("username") or str(p["user_id"])
        bot = p.get("bot_name") or "—"
        lines.append(t(
            lang, "payment_line",
            name=name,
            amount=p["amount_stars"],
            days=p["days"],
            bot=bot,
        ))
    if len(lines) == 1:
        lines.append("—")
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_kb(lang, "admin:section:billing"),
    )
    await callback.answer()

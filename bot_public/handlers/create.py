from __future__ import annotations

import logging
import re

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message

from bot_public.config import Config
from bot_public.database.db import PlatformDB
from bot_public.handlers.start import _lang
from bot_public.keyboards.common import (
    back_kb,
    crypto_pay_link_kb,
    crypto_wallets_kb,
    pay_methods_kb,
    wallet_pay_kb,
    wallet_pay_link_kb,
)
from bot_public.locales import t
from bot_public.services.child_manager import ChildManager
from bot_public.services.crypto_pay import (
    PROVIDER_CRYPTOBOT,
    CryptoPayError,
    create_invoice as create_cryptobot_invoice,
    encode_payload,
    make_external_id as make_crypto_external_id,
)
from bot_public.services.wallet_pay import (
    WalletPayError,
    create_order,
    encode_custom_data,
    make_external_id,
)
from bot_public.utils.payment_plan import PaymentPlan, load_payment_plan
from bot_public.utils.states import CreateBotState
from bot.utils.helpers import format_display_time

router = Router()
logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]{30,}$")


async def _send_cryptobot_invoice(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    config: Config,
    plan: PaymentPlan,
) -> None:
    if not callback.from_user:
        return
    if not config.crypto_pay_enabled:
        lang = await _lang(platform_db, callback.from_user.id)
        await callback.answer(t(lang, "cryptobot_not_configured"), show_alert=True)
        return

    lang = await _lang(platform_db, callback.from_user.id)
    external_id = make_crypto_external_id("cb", callback.from_user.id)
    payload = encode_payload(
        uid=callback.from_user.id,
        days=plan.days,
        type="create",
        eid=external_id,
    )
    description = t(
        lang, "cryptobot_invoice_desc",
        days=plan.days, price=plan.usdt_display,
    )[:1024]

    try:
        invoice = await create_cryptobot_invoice(
            config.crypto_pay_api_token,
            asset="USDT",
            amount=plan.usdt_amount,
            description=description,
            payload=payload,
            external_id=external_id,
            return_url=config.crypto_pay_return_url,
            expires_in=config.crypto_pay_order_timeout,
            testnet=config.crypto_pay_testnet,
        )
    except CryptoPayError as exc:
        logger.exception("Crypto Pay createInvoice failed for user %s", callback.from_user.id)
        await callback.answer(str(exc)[:180], show_alert=True)
        return

    await platform_db.create_wallet_order(
        external_id=external_id,
        wallet_order_id=invoice.invoice_id,
        user_id=callback.from_user.id,
        payment_type="create",
        days=plan.days,
        currency="USDT",
        amount=plan.usdt_amount,
        provider=PROVIDER_CRYPTOBOT,
    )

    logger.info(
        "CryptoBot invoice %s for user %s: %s USDT, %s days",
        invoice.invoice_id, callback.from_user.id, plan.usdt_amount, plan.days,
    )

    text = t(
        lang, "cryptobot_pay_ready",
        price=plan.usdt_display,
        days=plan.days,
    )
    markup = crypto_pay_link_kb(lang, invoice.pay_url, price=plan.usdt_display)
    try:
        if callback.message:
            await callback.message.edit_text(text, reply_markup=markup)
        else:
            await callback.bot.send_message(callback.from_user.id, text, reply_markup=markup)
    except TelegramBadRequest:
        await callback.bot.send_message(callback.from_user.id, text, reply_markup=markup)


@router.callback_query(F.data == "create:intro")
async def create_intro(callback: CallbackQuery, platform_db: PlatformDB, state: FSMContext) -> None:
    if not callback.from_user:
        return
    lang = await _lang(platform_db, callback.from_user.id)
    plan = await load_payment_plan(platform_db)

    if not await platform_db.is_paid_mode():
        await state.set_state(CreateBotState.waiting_token)
        await state.update_data(paid_days=plan.days)
        await callback.message.edit_text(
            t(lang, "create_free_intro", days=plan.days),
            reply_markup=back_kb(lang),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        t(
            lang, "create_intro",
            price=plan.stars, days=plan.days,
            crypto_usdt=plan.usdt_display,
        ),
        reply_markup=pay_methods_kb(
            lang, plan.stars, usdt_price=plan.usdt_display, days=plan.days,
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "pay:method:stars")
async def pay_stars(callback: CallbackQuery, platform_db: PlatformDB) -> None:
    if not callback.from_user:
        return
    lang = await _lang(platform_db, callback.from_user.id)
    plan = await load_payment_plan(platform_db)
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=t(lang, "invoice_title"),
        description=t(lang, "invoice_desc", days=plan.days),
        payload=f"create:{plan.days}",
        currency="XTR",
        prices=[LabeledPrice(label=t(lang, "invoice_title"), amount=plan.stars)],
    )
    await callback.answer()


@router.callback_query(F.data == "pay:method:crypto")
async def pay_crypto_menu(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    config: Config,
) -> None:
    if not callback.from_user:
        return
    lang = await _lang(platform_db, callback.from_user.id)
    plan = await load_payment_plan(platform_db)

    try:
        if config.crypto_pay_enabled:
            await _send_cryptobot_invoice(callback, platform_db, config, plan)
            await callback.answer()
            return
        if config.wallet_pay_enabled:
            text = t(
                lang, "wallet_choose_currency",
                usdt_price=plan.usdt_display, days=plan.days,
            )
            markup = wallet_pay_kb(lang, usdt_price=plan.usdt_display)
        else:
            admin = await platform_db.crypto_admin_username()
            text = t(
                lang, "crypto_choose_wallet",
                usdt_price=plan.usdt_display, days=plan.days, admin=admin,
            )
            markup = crypto_wallets_kb(
                lang, admin, usdt_price=plan.usdt_display,
            )
        if callback.message:
            try:
                await callback.message.edit_text(text, reply_markup=markup)
            except TelegramBadRequest:
                await callback.message.answer(text, reply_markup=markup)
        else:
            await callback.bot.send_message(callback.from_user.id, text, reply_markup=markup)
    except Exception:
        logger.exception("pay_crypto_menu failed for user %s", callback.from_user.id)
        await callback.answer("Error. Try again or contact support.", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data == "pay:cryptobot:usdt")
async def pay_cryptobot_invoice(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    config: Config,
) -> None:
    plan = await load_payment_plan(platform_db)
    await _send_cryptobot_invoice(callback, platform_db, config, plan)
    await callback.answer()


@router.callback_query(F.data == "pay:crypto:trc20")
async def pay_crypto_wallet(callback: CallbackQuery, platform_db: PlatformDB) -> None:
    if not callback.from_user:
        return
    lang = await _lang(platform_db, callback.from_user.id)
    plan = await load_payment_plan(platform_db)
    admin = await platform_db.crypto_admin_username()
    wallet = await platform_db.get_cfg("crypto_wallet_trc20")
    text = t(
        lang, "crypto_wallet_trc20",
        price=plan.usdt_display, days=plan.days, wallet=wallet, admin=admin,
    )
    markup = crypto_wallets_kb(lang, admin, usdt_price=plan.usdt_display)
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "pay:wallet:usdt")
async def pay_wallet_order(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    config: Config,
) -> None:
    if not callback.from_user:
        return
    if not config.wallet_pay_enabled:
        lang = await _lang(platform_db, callback.from_user.id)
        await callback.answer(t(lang, "wallet_pay_not_configured"), show_alert=True)
        return

    lang = await _lang(platform_db, callback.from_user.id)
    plan = await load_payment_plan(platform_db)

    external_id = make_external_id("create", callback.from_user.id)
    custom_data = encode_custom_data(
        uid=callback.from_user.id,
        days=plan.days,
        type="create",
    )
    description = t(
        lang, "cryptobot_invoice_desc",
        days=plan.days, price=plan.usdt_display,
    )[:100]

    try:
        order = await create_order(
            config.wallet_pay_api_key,
            currency="USDT",
            amount=plan.usdt_amount,
            description=description,
            external_id=external_id,
            customer_telegram_user_id=callback.from_user.id,
            return_url=config.wallet_pay_return_url,
            fail_return_url=config.wallet_pay_return_url,
            custom_data=custom_data,
            timeout_seconds=config.wallet_pay_order_timeout,
        )
    except WalletPayError as exc:
        logger.exception("Wallet Pay create_order failed for user %s", callback.from_user.id)
        await callback.answer(str(exc)[:180], show_alert=True)
        return

    await platform_db.create_wallet_order(
        external_id=external_id,
        wallet_order_id=order.order_id,
        user_id=callback.from_user.id,
        payment_type="create",
        days=plan.days,
        currency="USDT",
        amount=plan.usdt_amount,
        provider="wallet_pay",
    )

    text = t(
        lang, "wallet_pay_ready",
        price=plan.usdt_display,
        days=plan.days,
    )
    markup = wallet_pay_link_kb(lang, order.direct_pay_link)
    try:
        if callback.message:
            await callback.message.edit_text(text, reply_markup=markup)
        else:
            await callback.bot.send_message(callback.from_user.id, text, reply_markup=markup)
    except TelegramBadRequest:
        await callback.bot.send_message(callback.from_user.id, text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("renew:"))
async def renew_invoice(callback: CallbackQuery, platform_db: PlatformDB) -> None:
    if not callback.from_user:
        return
    if not await platform_db.is_paid_mode():
        await callback.answer()
        return
    bot_id = int(callback.data.split(":")[-1])
    child = await platform_db.get_child_bot(bot_id)
    if not child or int(child["owner_id"]) != callback.from_user.id:
        await callback.answer()
        return
    lang = await _lang(platform_db, callback.from_user.id)
    price = await platform_db.subscription_price()
    days = await platform_db.subscription_days()
    username = child.get("bot_username") or "bot"
    await callback.message.answer(
        t(lang, "renew_intro", username=username, price=price, days=days),
    )
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=t(lang, "invoice_title"),
        description=t(lang, "invoice_desc", days=days),
        payload=f"renew:{bot_id}:{days}",
        currency="XTR",
        prices=[LabeledPrice(label=t(lang, "invoice_title"), amount=price)],
    )
    await callback.answer()


async def _submit_bot_token(
    message: Message,
    platform_db: PlatformDB,
    config: Config,
    state: FSMContext,
    child_manager: ChildManager,
    *,
    paid_days: int,
) -> None:
    if not message.from_user or not message.text:
        return
    lang = await _lang(platform_db, message.from_user.id)
    token = message.text.strip()
    if not TOKEN_RE.match(token):
        await message.answer(t(lang, "token_invalid"))
        return
    if await platform_db.get_child_by_token(token):
        await message.answer(t(lang, "token_exists"))
        return

    try:
        test_bot = Bot(token=token)
        try:
            bot_me = await test_bot.get_me()
        finally:
            await test_bot.session.close()
    except Exception:
        await message.answer(t(lang, "token_invalid"))
        return

    child = await platform_db.add_child_bot(
        message.from_user.id,
        token,
        bot_me.username,
        bot_me.full_name or bot_me.username,
        paid_days,
    )
    await platform_db.fulfill_create_payment(message.from_user.id, int(child["id"]))
    await state.clear()

    started = await child_manager.start_child(child)
    if not started:
        await message.answer(t(lang, "bot_start_failed"))
        return

    expires = child["expires_at"]
    date_str = format_display_time(expires, config.timezone)
    days_left = platform_db.days_remaining(expires)
    username = bot_me.username or "bot"

    await message.answer(
        t(
            lang,
            "bot_created",
            username=username,
            name=bot_me.full_name or username,
            date=date_str,
            days=days_left,
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text=t(lang, "btn_open_bot"),
                    url=f"https://t.me/{username}",
                )
            ]]
        ),
    )


@router.message(CreateBotState.waiting_token, F.text)
async def receive_token(
    message: Message,
    platform_db: PlatformDB,
    config: Config,
    state: FSMContext,
    child_manager: ChildManager,
) -> None:
    data = await state.get_data()
    days = int(data.get("paid_days") or await platform_db.subscription_days())
    await _submit_bot_token(
        message, platform_db, config, state, child_manager, paid_days=days,
    )


@router.message(F.text.regexp(TOKEN_RE))
async def receive_token_after_restart(
    message: Message,
    platform_db: PlatformDB,
    config: Config,
    state: FSMContext,
    child_manager: ChildManager,
) -> None:
    if not message.from_user:
        return
    current = await state.get_state()
    if current == CreateBotState.waiting_token.state:
        return
    pending = await platform_db.get_pending_create(message.from_user.id)
    if not pending and await platform_db.is_paid_mode():
        return
    if not pending and not await platform_db.is_paid_mode():
        days = await platform_db.subscription_days()
    else:
        days = int(pending.get("days") or await platform_db.subscription_days())
    await _submit_bot_token(
        message, platform_db, config, state, child_manager, paid_days=days,
    )


@router.callback_query(F.data == "my:bots")
async def my_bots(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    child_manager: ChildManager,
) -> None:
    if not callback.from_user:
        return
    lang = await _lang(platform_db, callback.from_user.id)
    paid = await platform_db.is_paid_mode()
    pending = await platform_db.get_pending_create(callback.from_user.id)
    bots = await platform_db.get_user_bots(callback.from_user.id)
    if not bots and not pending:
        await callback.message.edit_text(
            t(lang, "my_bots_empty"),
            reply_markup=back_kb(lang),
        )
        await callback.answer()
        return

    lines = [t(lang, "my_bots_title")]
    if pending and paid:
        lines.append(t(lang, "pending_token_hint"))
    kb_rows: list[list[InlineKeyboardButton]] = []
    for b in bots:
        username = b.get("bot_username")
        name = b.get("bot_name") or username or "Bot"
        bot_id = int(b["id"])
        if not username or str(b.get("bot_token", "")).startswith("virtual:"):
            lines.append(f"⚠️ {name} — {t(lang, 'bot_needs_token')}")
            continue
        if await platform_db.is_child_active(b.get("expires_at")):
            days = (
                await platform_db.subscription_days()
                if not paid
                else platform_db.days_remaining(b.get("expires_at"))
            )
            if child_manager.is_child_running(bot_id):
                lines.append(t(
                    lang, "bot_line_active",
                    username=username,
                    name=name,
                    days=days,
                ))
            else:
                lines.append(t(
                    lang, "bot_line_offline",
                    username=username,
                    name=name,
                    days=days,
                ))
            kb_rows.append([InlineKeyboardButton(
                text=f"🤖 @{username}",
                url=f"https://t.me/{username}",
            )])
        else:
            lines.append(t(lang, "bot_line_expired", username=username, name=name))
            if await platform_db.is_paid_mode():
                kb_rows.append([InlineKeyboardButton(
                    text=t(lang, "btn_renew"),
                    callback_data=f"renew:{b['id']}",
                )])

    kb_rows.append([InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="menu:main",
    )])
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
    )
    await callback.answer()

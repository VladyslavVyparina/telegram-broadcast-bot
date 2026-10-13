from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PreCheckoutQuery

from bot_public.config import Config
from bot_public.database.db import PlatformDB
from bot_public.handlers.start import _lang
from bot_public.locales import t
from bot_public.services.child_manager import ChildManager
from bot_public.services.notify import notify_purchase
from bot_public.utils.states import CreateBotState
from bot.utils.helpers import format_display_time

router = Router()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(
    message: Message,
    platform_db: PlatformDB,
    config: Config,
    state: FSMContext,
    child_manager: ChildManager,
) -> None:
    if not message.from_user or not message.successful_payment:
        return
    payment = message.successful_payment
    payload = payment.invoice_payload
    amount = payment.total_amount
    uid = message.from_user.id
    lang = await _lang(platform_db, uid)

    if payload.startswith("create:"):
        days = int(payload.split(":")[1])
        await platform_db.record_payment(uid, amount, days, "create", payload=payload)
        await notify_purchase(
            message.bot,
            config,
            platform_db,
            user_id=uid,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            amount=amount,
            days=days,
            bot_name=None,
            payment_type="create",
        )
        await state.set_state(CreateBotState.waiting_token)
        await state.update_data(paid_days=days)
        await message.answer(t(lang, "send_token"))

    elif payload.startswith("renew:"):
        parts = payload.split(":")
        bot_id = int(parts[1])
        days = int(parts[2])
        child = await platform_db.get_child_bot(bot_id)
        if not child or int(child["owner_id"]) != uid:
            return
        await platform_db.record_payment(
            uid, amount, days, "renew",
            child_bot_id=bot_id, payload=payload,
        )
        expires = await platform_db.extend_child_bot(bot_id, days)
        child = await platform_db.get_child_bot(bot_id)
        await child_manager.restart_child(child)
        await notify_purchase(
            message.bot,
            config,
            platform_db,
            user_id=uid,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            amount=amount,
            days=days,
            bot_name=child.get("bot_name") if child else None,
            payment_type="renew",
        )
        username = child.get("bot_username") or "bot" if child else "bot"
        date_str = format_display_time(expires, config.timezone)
        await message.answer(
            t(lang, "renew_success", username=username, date=date_str)
        )

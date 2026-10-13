from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.database.db import Database
from bot.filters.admin import AdminFilter
from bot.keyboards.inline import (
    broadcast_done_kb,
    content_prompt_kb,
    stop_broadcast_kb,
)
from bot.locales import t
from bot.services.broadcaster import broadcast_manager
from bot.utils.helpers import new_broadcast_id, serialize_message
from bot.utils.states import BroadcastState

router = Router()
admin = AdminFilter()

AUDIENCE_HEADERS = {
    "all": "broadcast_header_all",
    "groups": "broadcast_header_groups",
    "private": "broadcast_header_private",
}


@router.callback_query(admin, F.data == "com:quick")
async def com_quick(
    callback: CallbackQuery,
    db: Database,
    config: Config,
    state: FSMContext,
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(BroadcastState.quick_content)
    await callback.message.edit_text(t(lang, "quick_broadcast_prompt"))
    await callback.answer()


@router.message(admin, BroadcastState.quick_content)
async def quick_receive(
    message: Message,
    db: Database,
    config: Config,
    state: FSMContext,
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    content = serialize_message(message, method="direct")
    if content.get("content_type") == "unsupported":
        await message.answer(t(lang, "no_content"))
        return
    await state.clear()
    await _run_broadcast(message, db, config, lang, "all", "direct", content)


@router.callback_query(admin, F.data.startswith("bc:audience:"))
async def bc_audience(
    callback: CallbackQuery,
    db: Database,
    config: Config,
    state: FSMContext,
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    parts = callback.data.split(":")
    audience = parts[2]
    method = parts[3]
    await state.update_data(audience=audience, method=method)

    header_key = AUDIENCE_HEADERS.get(audience, "broadcast_header_all")
    if method == "forward":
        prompt = t(lang, "forward_content_prompt")
        await state.set_state(BroadcastState.waiting_forward)
        await callback.message.edit_text(
            f"<b>{t(lang, header_key)}</b>\n━━━━━━━━━━━━━━━━\n{prompt}"
        )
    else:
        prompt = t(lang, "send_content_prompt")
        await state.set_state(BroadcastState.waiting_content)
        await callback.message.edit_text(
            f"<b>{t(lang, header_key)}</b>\n━━━━━━━━━━━━━━━━\n{prompt}",
            reply_markup=content_prompt_kb(lang),
        )
    await callback.answer()


@router.callback_query(admin, F.data.startswith("bc:stop:"))
async def bc_stop(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    broadcast_id = callback.data.split(":")[-1]
    broadcast_manager.request_stop(broadcast_id)
    await callback.answer(t(lang, "broadcast_stopped"))


@router.message(admin, BroadcastState.waiting_content)
async def bc_receive_content(
    message: Message,
    db: Database,
    config: Config,
    state: FSMContext,
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    data = await state.get_data()
    audience = data.get("audience", "all")
    method = data.get("method", "direct")
    await state.clear()
    content = serialize_message(message, method=method)
    if content.get("content_type") == "unsupported":
        await message.answer(t(lang, "no_content"))
        return
    await _run_broadcast(message, db, config, lang, audience, method, content)


@router.message(admin, BroadcastState.waiting_forward)
async def bc_receive_forward(
    message: Message,
    db: Database,
    config: Config,
    state: FSMContext,
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if not message.forward_origin and not message.forward_from_chat and not message.text:
        await message.answer(t(lang, "forward_content_prompt"))
        return
    data = await state.get_data()
    audience = data.get("audience", "all")
    await state.clear()
    content = serialize_message(message, method="forward")
    await _run_broadcast(message, db, config, lang, audience, "forward", content)


async def _run_broadcast(
    message: Message,
    db: Database,
    config: Config,
    lang: str,
    audience: str,
    method: str,
    content: dict,
) -> None:
    broadcast_id = new_broadcast_id()
    targets = await db.get_targets(audience)
    await db.create_broadcast(
        broadcast_id=broadcast_id,
        admin_id=config.admin_id,
        target_type=audience,
        send_method=method,
        content=content,
        total_targets=len(targets),
    )
    progress = await message.answer(
        t(lang, "broadcasting", broadcast_id=broadcast_id),
        reply_markup=stop_broadcast_kb(lang, broadcast_id),
    )
    result = await broadcast_manager.run(
        message.bot,
        db,
        broadcast_id,
        targets,
        content,
        method,
        progress_message=progress,
        lang=lang,
    )
    speed = round(result.sent / result.duration, 1)
    success = round((result.sent / result.total * 100) if result.total else 0, 1)
    header = t(lang, "broadcast_stopped") if result.stopped else t(lang, "broadcast_done")
    report = (
        f"<b>{header}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{t(lang, 'stat_users')}: {result.total}\n"
        f"{t(lang, 'stat_sent')}: {result.sent}\n"
        f"{t(lang, 'stat_blocked')}: {result.blocked}\n"
        f"{t(lang, 'stat_failed')}: {result.failed}\n\n"
        f"{t(lang, 'stat_performance', duration=round(result.duration, 1), speed=speed, success=success)}"
    )
    await progress.edit_text(report, reply_markup=broadcast_done_kb(lang))

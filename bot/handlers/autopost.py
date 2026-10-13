from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.database.db import MAX_AUTOPOST_ITEMS, Database
from bot.filters.admin import AdminFilter
from bot.keyboards.inline import autopost_item_kb, autopost_items_kb, autopost_menu_kb
from bot.locales import t
from bot.locales.ar import INTERVAL_LABELS
from bot.services.scheduler import AutoPostScheduler
from bot.utils.helpers import content_preview, serialize_message
from bot.utils.states import AutoPostState

router = Router()
admin = AdminFilter()


async def _items_header(lang: str, items: list) -> str:
    lines = [
        f"<b>{t(lang, 'autopost_messages_title')}</b>",
        "━━━━━━━━━━━━━━━━",
        t(lang, "autopost_messages_desc", max=MAX_AUTOPOST_ITEMS),
        t(lang, "autopost_messages_count", count=len(items), max=MAX_AUTOPOST_ITEMS),
    ]
    if not items:
        lines.append(t(lang, "autopost_messages_empty"))
    return "\n".join(lines)


async def _show_items(
    message_or_callback,
    db: Database,
    config: Config,
    *,
    enabled: bool | None = None,
    setup_mode: bool = False,
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    items = await db.list_auto_post_items()
    if enabled is None:
        settings = await db.get_auto_post() or {}
        enabled = bool(settings.get("is_enabled"))
    text = await _items_header(lang, items)
    kb = autopost_items_kb(lang, items, enabled=enabled, setup_mode=setup_mode)
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=kb)
    else:
        await message_or_callback.answer(text, reply_markup=kb)


@router.callback_query(admin, F.data == "ap:items")
async def ap_items(callback: CallbackQuery, db: Database, config: Config) -> None:
    await _show_items(callback, db, config)
    await callback.answer()


@router.callback_query(admin, F.data == "ap:item:add")
async def ap_item_add(
    callback: CallbackQuery, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    count = await db.count_auto_post_items()
    if count >= MAX_AUTOPOST_ITEMS:
        await callback.answer(t(lang, "ap_limit_reached", max=MAX_AUTOPOST_ITEMS), show_alert=True)
        return
    await state.set_state(AutoPostState.waiting_content)
    await callback.message.edit_text(t(lang, "ap_send_item"))
    await callback.answer()


@router.callback_query(admin, F.data.startswith("ap:item:view:"))
async def ap_item_view(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    item_id = int(callback.data.split(":")[-1])
    item = await db.get_auto_post_item(item_id)
    if not item:
        await callback.answer(t(lang, "unknown"), show_alert=True)
        return
    items = await db.list_auto_post_items()
    num = next((i + 1 for i, x in enumerate(items) if x["id"] == item_id), 1)
    preview = content_preview(item["content"], max_len=200)
    text = t(lang, "ap_item_view", num=num, preview=preview)
    await callback.message.edit_text(
        text, reply_markup=autopost_item_kb(lang, item_id)
    )
    await callback.answer()


@router.callback_query(admin, F.data.startswith("ap:item:edit:"))
async def ap_item_edit(
    callback: CallbackQuery, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    item_id = int(callback.data.split(":")[-1])
    if not await db.get_auto_post_item(item_id):
        await callback.answer(t(lang, "unknown"), show_alert=True)
        return
    await state.set_state(AutoPostState.waiting_edit_item)
    await state.update_data(edit_item_id=item_id)
    await callback.message.edit_text(t(lang, "ap_send_item_edit"))
    await callback.answer()


@router.callback_query(admin, F.data.startswith("ap:item:del:"))
async def ap_item_del(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    item_id = int(callback.data.split(":")[-1])
    await db.delete_auto_post_item(item_id)
    await callback.answer(t(lang, "ap_item_deleted"))
    await _show_items(callback, db, config)


@router.callback_query(admin, F.data == "ap:start")
async def ap_start(
    callback: CallbackQuery,
    db: Database,
    config: Config,
    scheduler: AutoPostScheduler,
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    items = await db.list_auto_post_items()
    if not items:
        await callback.answer(t(lang, "ap_need_message"), show_alert=True)
        return

    now = datetime.now(timezone.utc)
    settings = await db.get_auto_post() or {}
    interval = int(settings.get("interval_seconds", 300))
    next_post = datetime.fromtimestamp(
        now.timestamp() + interval, tz=timezone.utc
    ).isoformat()

    await db.save_auto_post(is_enabled=True, next_post_at=next_post)
    await scheduler.reschedule()
    scheduler.reset_session_stats()

    interval_key = INTERVAL_LABELS.get(interval, "interval_5m")
    await callback.message.edit_text(
        t(lang, "autopost_enabled", interval=t(lang, interval_key)),
        reply_markup=autopost_menu_kb(lang, True),
    )
    try:
        await callback.bot.send_message(
            config.admin_id,
            t(lang, "autopost_session_started"),
        )
    except Exception:
        pass
    await callback.answer()


@router.message(admin, AutoPostState.waiting_content)
async def ap_receive_content(
    message: Message,
    db: Database,
    config: Config,
    state: FSMContext,
    scheduler: AutoPostScheduler,
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    content = serialize_message(message, method="direct")
    if content.get("content_type") == "unsupported":
        await message.answer(t(lang, "no_content"))
        return

    await state.clear()
    await db.add_auto_post_item(content)
    items = await db.list_auto_post_items()
    settings = await db.get_auto_post() or {}
    enabled = bool(settings.get("is_enabled"))

    if enabled:
        await scheduler.reschedule()
        text = t(lang, "ap_item_saved") + "\n\n" + await _items_header(lang, items)
        await message.answer(
            text,
            reply_markup=autopost_items_kb(lang, items, enabled=True),
        )
    else:
        text = await _items_header(lang, items)
        await message.answer(
            t(lang, "ap_item_saved") + "\n\n" + text,
            reply_markup=autopost_items_kb(lang, items, enabled=False, setup_mode=True),
        )


@router.message(admin, AutoPostState.waiting_edit_item)
async def ap_receive_edit(
    message: Message,
    db: Database,
    config: Config,
    state: FSMContext,
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    data = await state.get_data()
    item_id = data.get("edit_item_id")
    if not item_id:
        await state.clear()
        return

    content = serialize_message(message, method="direct")
    if content.get("content_type") == "unsupported":
        await message.answer(t(lang, "no_content"))
        return

    await state.clear()
    ok = await db.update_auto_post_item(int(item_id), content)
    items = await db.list_auto_post_items()
    settings = await db.get_auto_post() or {}
    enabled = bool(settings.get("is_enabled"))

    if ok:
        text = t(lang, "ap_item_updated") + "\n\n" + await _items_header(lang, items)
        await message.answer(
            text,
            reply_markup=autopost_items_kb(lang, items, enabled=enabled),
        )
    else:
        await message.answer(t(lang, "unknown"))

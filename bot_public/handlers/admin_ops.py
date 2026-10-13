from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.utils.helpers import serialize_message
from bot_public.config import is_platform_owner
from bot_public.database.db import PlatformDB
from bot_public.handlers.start import _lang
from bot_public.keyboards.admin_kb import (
    admin_ar_item_kb,
    admin_auto_reply_kb,
    admin_bc_audience_kb,
    admin_bc_pick_bot_kb,
    admin_bot_detail_kb,
    admin_bots_kb,
    admin_ops_kb,
)
from bot_public.keyboards.common import back_kb
from bot_public.locales import t
from bot_public.services.child_manager import ChildManager
from bot_public.services.network_ops import (
    broadcast_to_clones,
    clear_auto_replies_on_clones,
    collect_network_stats,
    delete_auto_reply_from_clone,
    sync_auto_reply_to_clone,
    sync_global_replies_to_clones,
)
from bot_public.utils.states import AdminState

router = Router()
logger = logging.getLogger(__name__)


def _owner_only(callback: CallbackQuery) -> bool:
    return bool(callback.from_user and is_platform_owner(callback.from_user.id))


def _running_ids(child_manager: ChildManager, bots: list[dict]) -> set[int]:
    return {
        int(b["id"])
        for b in bots
        if child_manager.is_child_running(int(b["id"]))
    }


async def _sync_all_ar(platform_db: PlatformDB) -> tuple[int, int]:
    items = await platform_db.get_global_auto_replies()
    children = await platform_db.get_all_child_bots()
    return await sync_global_replies_to_clones(children, items)


def _ar_list_text(lang: str, items: list[dict]) -> str:
    lines = [t(lang, "admin_ar_title")]
    if not items:
        lines.append(t(lang, "admin_ar_empty"))
        lines.append(t(lang, "admin_ar_tap_hint"))
        return "\n".join(lines)
    lines.append(t(lang, "admin_ar_list_hint"))
    for idx, item in enumerate(items[:10], start=1):
        reply = item.get("reply_text") or ""
        short = reply[:80] + ("…" if len(reply) > 80 else "")
        lines.append(t(
            lang, "admin_ar_list_line",
            num=idx, trigger=item.get("trigger", "?"), reply=short,
        ))
    return "\n".join(lines)


@router.callback_query(F.data == "admin:section:ops")
async def admin_section_ops(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    await state.clear()
    lang = await _lang(platform_db, callback.from_user.id)
    await callback.message.edit_text(
        t(lang, "admin_ops_intro"),
        reply_markup=admin_ops_kb(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:ops:stats")
async def admin_ops_stats(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    child_manager: ChildManager,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    lang = await _lang(platform_db, callback.from_user.id)
    bots = await platform_db.get_all_child_bots()
    stats = await collect_network_stats(
        bots, running_count=child_manager.running_count(),
    )
    text = t(
        lang, "admin_network_stats",
        total_bots=stats.total_bots,
        active_bots=stats.active_bots,
        running_bots=stats.running_bots,
        disabled_bots=stats.disabled_bots,
        expired_bots=stats.expired_bots,
        total_users=stats.total_users,
        total_groups=stats.total_groups,
        autopost_enabled=stats.autopost_enabled,
        auto_replies_total=stats.auto_replies_total,
    )
    await callback.message.edit_text(
        text, reply_markup=back_kb(lang, "admin:section:ops"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:ops:bots:"))
async def admin_ops_bots(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    child_manager: ChildManager,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    lang = await _lang(platform_db, callback.from_user.id)
    page = int(callback.data.split(":")[-1])
    bots = await platform_db.get_all_child_bots()
    running = _running_ids(child_manager, bots)

    lines = [t(lang, "admin_bots_list_title", count=len(bots))]
    start = page * 6
    for bot in bots[start:start + 6]:
        bot_id = int(bot["id"])
        username = bot.get("bot_username") or "—"
        if bot.get("is_disabled"):
            status = t(lang, "admin_bot_status_disabled")
        elif bot_id in running:
            status = t(lang, "admin_bot_status_running")
        else:
            status = t(lang, "admin_bot_status_stopped")
        lines.append(t(
            lang, "admin_bot_line",
            username=username, status=status, bot_id=bot_id,
        ))

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_bots_kb(lang, bots, page=page, running_ids=running),
    )
    await callback.answer()


async def _render_bot_detail(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    child_manager: ChildManager,
    bot_id: int,
) -> None:
    child = await platform_db.get_child_bot(bot_id)
    if not child:
        return
    lang = await _lang(platform_db, callback.from_user.id)
    disabled = bool(child.get("is_disabled"))
    running = child_manager.is_child_running(bot_id) and not disabled
    days = platform_db.days_remaining(child.get("expires_at"))
    text = t(
        lang, "admin_bot_detail",
        username=child.get("bot_username") or "—",
        name=child.get("bot_name") or "—",
        owner_id=child.get("owner_id"),
        days=days,
        status=t(lang, "admin_bot_status_disabled") if disabled else (
            t(lang, "admin_bot_status_running") if running
            else t(lang, "admin_bot_status_stopped")
        ),
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_bot_detail_kb(
            lang, bot_id, disabled=disabled, running=running,
        ),
    )


@router.callback_query(F.data.regexp(r"^admin:bot:\d+$"))
async def admin_bot_detail(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    child_manager: ChildManager,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    bot_id = int(callback.data.split(":")[-1])
    if not await platform_db.get_child_bot(bot_id):
        await callback.answer()
        return
    await _render_bot_detail(callback, platform_db, child_manager, bot_id)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:bot:stop:"))
async def admin_bot_stop(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    child_manager: ChildManager,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    bot_id = int(callback.data.split(":")[-1])
    await child_manager.stop_child(bot_id)
    await platform_db.set_child_disabled(bot_id, True)
    lang = await _lang(platform_db, callback.from_user.id)
    await callback.answer(t(lang, "admin_bot_stopped"), show_alert=True)
    await _render_bot_detail(callback, platform_db, child_manager, bot_id)


@router.callback_query(F.data.startswith("admin:bot:start:"))
async def admin_bot_start(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    child_manager: ChildManager,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    bot_id = int(callback.data.split(":")[-1])
    child = await platform_db.get_child_bot(bot_id)
    if not child:
        await callback.answer()
        return
    await platform_db.set_child_disabled(bot_id, False)
    started = await child_manager.start_child(child)
    lang = await _lang(platform_db, callback.from_user.id)
    await callback.answer(
        t(lang, "admin_bot_started" if started else "admin_bot_start_failed"),
        show_alert=True,
    )
    await _render_bot_detail(callback, platform_db, child_manager, bot_id)


@router.callback_query(F.data.startswith("admin:bot:restart:"))
async def admin_bot_restart(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    child_manager: ChildManager,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    bot_id = int(callback.data.split(":")[-1])
    child = await platform_db.get_child_bot(bot_id)
    if not child:
        await callback.answer()
        return
    await platform_db.set_child_disabled(bot_id, False)
    await child_manager.restart_child(child)
    lang = await _lang(platform_db, callback.from_user.id)
    await callback.answer(t(lang, "admin_bot_restarted"), show_alert=True)
    await _render_bot_detail(callback, platform_db, child_manager, bot_id)


@router.callback_query(F.data == "admin:ops:start_all")
async def admin_ops_start_all(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    child_manager: ChildManager,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    started = 0
    for child in await platform_db.get_all_child_bots():
        bot_id = int(child["id"])
        await platform_db.set_child_disabled(bot_id, False)
        if await child_manager.start_child(child):
            started += 1
    lang = await _lang(platform_db, callback.from_user.id)
    await callback.answer(
        t(lang, "admin_started_all", count=started), show_alert=True,
    )


@router.callback_query(F.data == "admin:ops:stop_all")
async def admin_ops_stop_all(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    child_manager: ChildManager,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    stopped = 0
    for child in await platform_db.get_all_child_bots():
        bot_id = int(child["id"])
        await child_manager.stop_child(bot_id)
        await platform_db.set_child_disabled(bot_id, True)
        stopped += 1
    lang = await _lang(platform_db, callback.from_user.id)
    await callback.answer(
        t(lang, "admin_stopped_all", count=stopped), show_alert=True,
    )


@router.callback_query(F.data.startswith("admin:ops:bc:"))
async def admin_broadcast_start(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    parts = callback.data.split(":")
    # admin:ops:bc:pick:0
    if len(parts) >= 5 and parts[3] == "pick":
        lang = await _lang(platform_db, callback.from_user.id)
        page = int(parts[4])
        bots = await platform_db.get_all_child_bots()
        real = [b for b in bots if b.get("bot_token") and not str(b["bot_token"]).startswith("virtual:")]
        if not real:
            await callback.answer(t(lang, "admin_bc_no_bots"), show_alert=True)
            return
        await callback.message.edit_text(
            t(lang, "admin_bc_pick_bot"),
            reply_markup=admin_bc_pick_bot_kb(lang, real, page=page),
        )
        await callback.answer()
        return

    # admin:ops:bc:sel:5
    if len(parts) >= 5 and parts[3] == "sel":
        bot_id = int(parts[4])
        child = await platform_db.get_child_bot(bot_id)
        if not child:
            await callback.answer()
            return
        lang = await _lang(platform_db, callback.from_user.id)
        username = child.get("bot_username") or str(bot_id)
        await callback.message.edit_text(
            t(lang, "admin_bc_pick_audience", username=username),
            reply_markup=admin_bc_audience_kb(lang, bot_id),
        )
        await callback.answer()
        return

    # admin:ops:bc:bot:5:private
    if len(parts) >= 6 and parts[3] == "bot":
        bot_id = int(parts[4])
        audience = parts[5]
        if audience not in ("all", "private", "groups"):
            await callback.answer()
            return
        lang = await _lang(platform_db, callback.from_user.id)
        child = await platform_db.get_child_bot(bot_id)
        username = child.get("bot_username") if child else str(bot_id)
        await state.set_state(AdminState.waiting_broadcast_content)
        await state.update_data(audience=audience, bot_ids=[bot_id])
        key = f"admin_bc_prompt_{audience}"
        await callback.message.edit_text(
            t(lang, "admin_bc_prompt_one", username=username or bot_id)
            + "\n\n"
            + t(lang, key),
            reply_markup=back_kb(lang, f"admin:ops:bc:sel:{bot_id}"),
        )
        await callback.answer()
        return

    audience = parts[-1]
    if audience not in ("all", "private", "groups"):
        await callback.answer()
        return
    lang = await _lang(platform_db, callback.from_user.id)
    await state.set_state(AdminState.waiting_broadcast_content)
    await state.update_data(audience=audience, bot_ids=None)
    key = f"admin_bc_prompt_{audience}"
    await callback.message.edit_text(
        t(lang, key),
        reply_markup=back_kb(lang, "admin:section:ops"),
    )
    await callback.answer()


@router.message(AdminState.waiting_broadcast_content)
async def admin_broadcast_send(
    message: Message,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not message.from_user or not is_platform_owner(message.from_user.id):
        return
    lang = await _lang(platform_db, message.from_user.id)
    data = await state.get_data()
    audience = data.get("audience", "all")
    raw_ids = data.get("bot_ids")
    only_bot_ids = {int(x) for x in raw_ids} if raw_ids else None
    content = serialize_message(message, method="direct")
    if content.get("content_type") == "unsupported" and not message.text:
        await message.answer(t(lang, "admin_bc_no_content"))
        return
    if message.text and content.get("content_type") == "text":
        content["text"] = message.html_text or message.text

    await state.clear()
    status = await message.answer(t(lang, "admin_bc_sending"))
    children = await platform_db.get_all_child_bots()
    report = await broadcast_to_clones(
        children, audience=audience, content=content, only_bot_ids=only_bot_ids,
    )
    await status.edit_text(t(
        lang, "admin_bc_done",
        bots=report.bots_used,
        targets=report.total_targets,
        sent=report.sent,
        blocked=report.blocked,
        failed=report.failed,
    ))


@router.callback_query(F.data == "admin:ops:auto_reply")
async def admin_auto_reply_menu(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    await state.clear()
    lang = await _lang(platform_db, callback.from_user.id)
    items = await platform_db.get_global_auto_replies()
    await callback.message.edit_text(
        _ar_list_text(lang, items),
        reply_markup=admin_auto_reply_kb(lang, items),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:ar:i:\d+$"))
async def admin_ar_item_view(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    await state.clear()
    index = int(callback.data.split(":")[-1])
    item = await platform_db.get_global_auto_reply_at(index)
    if not item:
        await callback.answer()
        return
    lang = await _lang(platform_db, callback.from_user.id)
    await callback.message.edit_text(
        t(
            lang, "admin_ar_item_detail",
            trigger=item["trigger"],
            reply=item["reply_text"],
        ),
        reply_markup=admin_ar_item_kb(lang, index),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:ar:edit_reply:\d+$"))
async def admin_ar_edit_reply_start(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    index = int(callback.data.split(":")[-1])
    item = await platform_db.get_global_auto_reply_at(index)
    if not item:
        await callback.answer()
        return
    lang = await _lang(platform_db, callback.from_user.id)
    await state.set_state(AdminState.waiting_ar_edit_reply)
    await state.update_data(ar_index=index)
    await callback.message.edit_text(
        t(lang, "admin_ar_edit_reply_prompt", trigger=item["trigger"], reply=item["reply_text"]),
        reply_markup=back_kb(lang, f"admin:ar:i:{index}"),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:ar:edit_trigger:\d+$"))
async def admin_ar_edit_trigger_start(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    index = int(callback.data.split(":")[-1])
    item = await platform_db.get_global_auto_reply_at(index)
    if not item:
        await callback.answer()
        return
    lang = await _lang(platform_db, callback.from_user.id)
    await state.set_state(AdminState.waiting_ar_edit_trigger)
    await state.update_data(ar_index=index, ar_old_trigger=item["trigger"])
    await callback.message.edit_text(
        t(lang, "admin_ar_edit_trigger_prompt", trigger=item["trigger"]),
        reply_markup=back_kb(lang, f"admin:ar:i:{index}"),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:ar:del:\d+$"))
async def admin_ar_delete(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    index = int(callback.data.split(":")[-1])
    removed = await platform_db.remove_global_auto_reply_at(index)
    if not removed:
        await callback.answer()
        return
    lang = await _lang(platform_db, callback.from_user.id)
    for child in await platform_db.get_all_child_bots():
        if child.get("db_path"):
            await delete_auto_reply_from_clone(child["db_path"], removed["trigger"])
    await _sync_all_ar(platform_db)
    await callback.answer(t(lang, "admin_ar_deleted", trigger=removed["trigger"]), show_alert=True)
    await admin_auto_reply_menu(callback, platform_db, state)


@router.message(AdminState.waiting_ar_edit_reply, F.text)
async def admin_ar_edit_reply_save(
    message: Message,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not message.from_user or not is_platform_owner(message.from_user.id):
        return
    if not message.text or not message.text.strip():
        return
    lang = await _lang(platform_db, message.from_user.id)
    data = await state.get_data()
    index = int(data.get("ar_index", -1))
    item = await platform_db.update_global_auto_reply_at(
        index, reply_text=message.text.strip(),
    )
    if not item:
        await state.clear()
        await message.answer(t(lang, "admin_ar_failed"))
        return
    children = await platform_db.get_all_child_bots()
    synced = 0
    for child in children:
        if child.get("db_path") and await sync_auto_reply_to_clone(
            child["db_path"], item["trigger"], item["reply_text"],
        ):
            synced += 1
    await state.clear()
    await message.answer(t(lang, "admin_ar_updated", trigger=item["trigger"], bots=synced))


@router.message(AdminState.waiting_ar_edit_trigger, F.text)
async def admin_ar_edit_trigger_save(
    message: Message,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not message.from_user or not is_platform_owner(message.from_user.id):
        return
    if not message.text or not message.text.strip():
        return
    lang = await _lang(platform_db, message.from_user.id)
    data = await state.get_data()
    index = int(data.get("ar_index", -1))
    old_trigger = str(data.get("ar_old_trigger", ""))
    new_trigger = message.text.strip().lower()
    item = await platform_db.update_global_auto_reply_at(index, trigger=new_trigger)
    if not item:
        await state.clear()
        await message.answer(t(lang, "admin_ar_failed"))
        return
    if old_trigger and old_trigger != new_trigger:
        for child in await platform_db.get_all_child_bots():
            if child.get("db_path"):
                await delete_auto_reply_from_clone(child["db_path"], old_trigger)
    bots_ok, _ = await _sync_all_ar(platform_db)
    await state.clear()
    await message.answer(t(lang, "admin_ar_trigger_updated", trigger=new_trigger, bots=bots_ok))


@router.callback_query(F.data == "admin:ops:ar:add")
async def admin_ar_add_start(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    lang = await _lang(platform_db, callback.from_user.id)
    await state.set_state(AdminState.waiting_ar_trigger)
    await callback.message.edit_text(
        t(lang, "admin_ar_trigger_prompt"),
        reply_markup=back_kb(lang, "admin:ops:auto_reply"),
    )
    await callback.answer()


@router.message(AdminState.waiting_ar_trigger, F.text)
async def admin_ar_trigger_save(
    message: Message,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not message.from_user or not is_platform_owner(message.from_user.id):
        return
    if not message.text or not message.text.strip():
        return
    lang = await _lang(platform_db, message.from_user.id)
    await state.update_data(ar_trigger=message.text.strip().lower())
    await state.set_state(AdminState.waiting_ar_reply)
    await message.answer(t(lang, "admin_ar_reply_prompt"))


@router.message(AdminState.waiting_ar_reply, F.text)
async def admin_ar_reply_save(
    message: Message,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not message.from_user or not is_platform_owner(message.from_user.id):
        return
    if not message.text or not message.text.strip():
        return
    lang = await _lang(platform_db, message.from_user.id)
    data = await state.get_data()
    trigger = str(data.get("ar_trigger", "")).strip().lower()
    reply_text = message.text.strip()
    if not trigger:
        await state.clear()
        await message.answer(t(lang, "admin_ar_failed"))
        return

    await platform_db.add_global_auto_reply(trigger, reply_text)
    bots_ok, _ = await _sync_all_ar(platform_db)
    await state.clear()
    await message.answer(t(
        lang, "admin_ar_saved",
        trigger=trigger, bots=bots_ok,
    ))


@router.callback_query(F.data == "admin:ops:ar:sync")
async def admin_ar_sync(
    callback: CallbackQuery,
    platform_db: PlatformDB,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    lang = await _lang(platform_db, callback.from_user.id)
    items = await platform_db.get_global_auto_replies()
    if not items:
        await callback.answer(t(lang, "admin_ar_empty"), show_alert=True)
        return
    children = await platform_db.get_all_child_bots()
    bots_ok, rules = await sync_global_replies_to_clones(children, items)
    await callback.answer(
        t(lang, "admin_ar_synced", bots=bots_ok, rules=rules), show_alert=True,
    )


@router.callback_query(F.data == "admin:ops:ar:clear")
async def admin_ar_clear(
    callback: CallbackQuery,
    platform_db: PlatformDB,
    state: FSMContext,
) -> None:
    if not _owner_only(callback):
        await callback.answer(t("ar", "admin_denied"), show_alert=True)
        return
    lang = await _lang(platform_db, callback.from_user.id)
    await platform_db.clear_global_auto_replies()
    cleared = await clear_auto_replies_on_clones(
        await platform_db.get_all_child_bots(),
    )
    await callback.answer(
        t(lang, "admin_ar_cleared", bots=cleared), show_alert=True,
    )
    await admin_auto_reply_menu(callback, platform_db, state)

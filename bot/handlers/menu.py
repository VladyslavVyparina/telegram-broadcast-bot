from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config import Config
from bot.database.db import MAX_AUTOPOST_ITEMS, Database
from bot.filters.admin import AdminFilter
from bot.handlers.start import build_panel_text
from bot.keyboards.inline import (
    autopost_interval_kb,
    autopost_items_kb,
    autopost_menu_kb,
    autopost_target_kb,
    communication_kb,
    content_menu_kb,
    main_menu_kb,
    subscription_kb,
    users_menu_kb,
)
from bot.locales import t
from bot.locales.ar import INTERVAL_LABELS, TARGET_LABELS
from bot.services.scheduler import AutoPostScheduler
from bot.utils.helpers import format_display_time
from bot.utils.spam_guard import clamp_autopost_interval

router = Router()
admin = AdminFilter()


async def _main_menu(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    settings = await db.get_admin_settings(config.admin_id)
    text = await build_panel_text(db, lang)
    await callback.message.edit_text(
        text,
        reply_markup=main_menu_kb(
            lang,
            notify_join=bool(settings.get("notify_join", 1)),
            notify_ban=bool(settings.get("notify_ban", 1)),
        ),
    )


@router.callback_query(admin, F.data == "menu:main")
async def menu_main(callback: CallbackQuery, db: Database, config: Config) -> None:
    await _main_menu(callback, db, config)
    await callback.answer()


# ── Notification toggles ──────────────────────────────────────────────────────

@router.callback_query(admin, F.data.startswith("toggle:notify_"))
async def toggle_notification(callback: CallbackQuery, db: Database, config: Config) -> None:
    field = callback.data.replace("toggle:", "")  # notify_join or notify_ban
    settings = await db.get_admin_settings(config.admin_id)
    current = bool(settings.get(field, 1))
    await db.toggle_notification(config.admin_id, field, not current)
    await _main_menu(callback, db, config)
    await callback.answer()


# ── Communication ─────────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "menu:communication")
async def menu_communication(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    text = f"<b>{t(lang, 'communication_title')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'communication_desc')}"
    await callback.message.edit_text(text, reply_markup=communication_kb(lang))
    await callback.answer()


@router.callback_query(admin, F.data == "com:broadcast")
async def com_broadcast(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    text = f"<b>{t(lang, 'broadcast_menu')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'choose_send_method')}"
    from bot.keyboards.inline import broadcast_method_kb
    await callback.message.edit_text(text, reply_markup=broadcast_method_kb(lang))
    await callback.answer()


@router.callback_query(admin, F.data == "com:forward")
async def com_forward(callback: CallbackQuery, db: Database, config: Config, state) -> None:
    from bot.utils.states import BroadcastState
    lang = await db.get_admin_language(config.admin_id)
    await state.update_data(audience="all", method="forward")
    await state.set_state(BroadcastState.waiting_forward)
    await callback.message.edit_text(t(lang, "forward_content_prompt"))
    await callback.answer()


@router.callback_query(admin, F.data.startswith("bc:method:"))
async def bc_method(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    method = callback.data.split(":")[-1]
    header = (
        t(lang, "broadcast_header_forward")
        if method == "forward"
        else t(lang, "broadcast_header_direct")
    )
    from bot.keyboards.inline import broadcast_audience_kb
    text = f"<b>{header}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'choose_audience')}"
    await callback.message.edit_text(text, reply_markup=broadcast_audience_kb(lang, method))
    await callback.answer()


@router.callback_query(admin, F.data == "bc:formats")
async def bc_formats(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.answer(t(lang, "formats_help_full"), show_alert=True)


# ── Content ───────────────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "menu:content")
async def menu_content(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    replies = await db.get_auto_replies()
    btn_count = await db.count_content_buttons()
    text = f"<b>{t(lang, 'content_title')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'content_desc')}"
    await callback.message.edit_text(text, reply_markup=content_menu_kb(lang, len(replies), btn_count))
    await callback.answer()


# ── Subscription ──────────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "menu:subscription")
async def menu_subscription(callback: CallbackQuery, db: Database, config: Config) -> None:
    from bot.handlers.subscription import _sub_menu
    await _sub_menu(callback, db, config)
    await callback.answer()


# ── Users ─────────────────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "menu:users")
async def menu_users(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    users = await db.count_users()
    groups = await db.count_groups()
    banned = await db.count_banned()
    text = (
        f"<b>{t(lang, 'users_title')}</b>\n━━━━━━━━━━━━━━━━\n"
        f"{t(lang, 'users_info', users=users, groups=groups, banned=banned)}"
    )
    await callback.message.edit_text(text, reply_markup=users_menu_kb(lang, banned))
    await callback.answer()


# ── Settings moved to settings_panel.py ───────────────────────────────────────

@router.callback_query(admin, F.data == "menu:autopost")
async def menu_autopost(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    settings = await db.get_auto_post() or {}
    enabled = bool(settings.get("is_enabled"))
    interval_sec = int(settings.get("interval_seconds", 300))
    target = settings.get("target_type", "groups")
    last_post_raw = settings.get("last_post_at")
    last_post = (
        format_display_time(last_post_raw, config.timezone)
        if last_post_raw
        else t(lang, "never")
    )
    msg_count = await db.count_auto_post_items()

    interval_key = INTERVAL_LABELS.get(interval_sec, "interval_5m")
    target_key = TARGET_LABELS.get(target, "autopost_target_groups")
    status = t(lang, "autopost_status_on") if enabled else t(lang, "autopost_status_off")

    text = (
        f"<b>{t(lang, 'autopost_title')}</b>\n━━━━━━━━━━━━━━━━\n"
        f"{t(lang, 'autopost_current', status=status, interval=t(lang, interval_key), target=t(lang, target_key), messages=msg_count, last_post=last_post)}"
    )
    await callback.message.edit_text(text, reply_markup=autopost_menu_kb(lang, enabled))
    await callback.answer()


@router.callback_query(admin, F.data == "ap:setup")
async def ap_setup(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    text = f"<b>{t(lang, 'autopost_title')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'autopost_choose_interval')}"
    await callback.message.edit_text(text, reply_markup=autopost_interval_kb(lang))
    await callback.answer()


@router.callback_query(admin, F.data == "ap:interval")
async def ap_change_interval(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.message.edit_text(
        f"<b>{t(lang, 'autopost_title')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'autopost_choose_interval')}",
        reply_markup=autopost_interval_kb(lang),
    )
    await callback.answer()


@router.callback_query(admin, F.data.startswith("ap:int:"))
async def ap_set_interval(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    interval = await clamp_autopost_interval(db, int(callback.data.split(":")[-1]))
    await db.save_auto_post(interval_seconds=interval)
    await callback.message.edit_text(
        f"<b>{t(lang, 'autopost_title')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'autopost_choose_target')}",
        reply_markup=autopost_target_kb(lang),
    )
    await callback.answer()


@router.callback_query(admin, F.data == "ap:target")
async def ap_change_target(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.message.edit_text(
        f"<b>{t(lang, 'autopost_title')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'autopost_choose_target')}",
        reply_markup=autopost_target_kb(lang),
    )
    await callback.answer()


@router.callback_query(admin, F.data.startswith("ap:tgt:"))
async def ap_set_target(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    target = callback.data.split(":")[-1]
    await db.save_auto_post(target_type=target)
    items = await db.list_auto_post_items()
    text = (
        f"<b>{t(lang, 'autopost_messages_title')}</b>\n━━━━━━━━━━━━━━━━\n"
        f"{t(lang, 'autopost_messages_desc', max=MAX_AUTOPOST_ITEMS)}\n"
        f"{t(lang, 'autopost_messages_count', count=len(items), max=MAX_AUTOPOST_ITEMS)}"
    )
    if not items:
        text += f"\n{t(lang, 'autopost_messages_empty')}"
    await callback.message.edit_text(
        text,
        reply_markup=autopost_items_kb(lang, items, enabled=False, setup_mode=True),
    )
    await callback.answer()


@router.callback_query(admin, F.data == "ap:content")
async def ap_change_content(callback: CallbackQuery, db: Database, config: Config) -> None:
    from bot.utils.spam_guard import clamp_autopost_interval
    await _show_items(callback, db, config)
    await callback.answer()


@router.callback_query(admin, F.data == "ap:disable")
async def ap_disable(
    callback: CallbackQuery,
    db: Database,
    config: Config,
    scheduler: AutoPostScheduler,
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await db.save_auto_post(is_enabled=False)
    if scheduler.session_stats()["cycles"] > 0:
        await scheduler.send_session_report(lang, stopped=True)
    scheduler.reset_session_stats()
    await callback.answer(t(lang, "autopost_disabled"), show_alert=True)
    await menu_autopost(callback, db, config)

from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.database.db import Database
from bot.database.defaults import VERIFICATION_MODES
from bot.filters.admin import AdminFilter
from bot.keyboards.menus import (
    auto_delete_duration_kb,
    auto_delete_kb,
    bot_work_kb,
    content_protect_kb,
    guide_sections_kb,
    inactive_kb,
    language_kb,
    notifications_kb,
    quick_replies_kb,
    qr_item_kb,
    settings_main_kb_with_count,
    system_kb,
    verification_kb,
)
from bot.utils.toggle import toggle_btn
from bot.locales import t
from bot.utils.states import FinanceState, InactiveState, QuickReplyState, SubState

router = Router()
admin = AdminFilter()

VERIFY_LABELS = {
    "disabled": "verify_disabled",
    "captcha": "verify_captcha",
    "website": "verify_website",
    "phone": "verify_phone",
    "invitation": "verify_invitation",
    "approval": "verify_approval",
}


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()


# ── Settings main ─────────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "menu:settings")
async def menu_settings(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    cfg = await db.get_all_cfg()
    qr = await db.count_quick_replies()
    text = f"<b>{t(lang, 'settings_title')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'settings_desc')}"
    await callback.message.edit_text(
        text, reply_markup=settings_main_kb_with_count(lang, cfg, qr)
    )
    await callback.answer()


@router.callback_query(admin, F.data == "set:langmenu")
async def set_lang_menu(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.message.edit_text(
        f"<b>{t(lang, 'language')}</b>", reply_markup=language_kb(lang)
    )
    await callback.answer()


@router.callback_query(admin, F.data.startswith("set:lang:"))
async def set_lang(callback: CallbackQuery, db: Database, config: Config) -> None:
    await db.set_admin_language(config.admin_id, "ar")
    await callback.answer(t("ar", "language_changed"))
    await menu_settings(callback, db, config)


# ── Bot work ──────────────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "set:botwork")
async def set_botwork(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    on = await db.get_cfg_bool("bot_enabled")
    status = t(lang, "bot_work_on") if on else t(lang, "bot_work_off")
    await callback.message.edit_text(
        f"<b>{t(lang, 'set_bot_work')}</b>\n━━━━━━━━━━━━━━━━\n{status}",
        reply_markup=bot_work_kb(lang, on),
    )
    await callback.answer()


@router.callback_query(admin, F.data == "set:botwork:toggle")
async def set_botwork_toggle(callback: CallbackQuery, db: Database, config: Config) -> None:
    await db.toggle_cfg("bot_enabled")
    await set_botwork(callback, db, config)


# ── Content protection ────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "set:protect")
async def set_protect(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    cfg = await db.get_all_cfg()
    text = f"<b>{t(lang, 'protect_title')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'protect_desc')}"
    await callback.message.edit_text(text, reply_markup=content_protect_kb(lang, cfg))
    await callback.answer()


@router.callback_query(admin, F.data == "set:protect:help")
async def set_protect_help(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.answer(t(lang, "protect_help"), show_alert=True)


@router.callback_query(admin, F.data == "set:protect:toggle")
async def set_protect_toggle(callback: CallbackQuery, db: Database, config: Config) -> None:
    await db.toggle_cfg("content_protection")
    await set_protect(callback, db, config)


@router.callback_query(admin, F.data.in_({
    "set:protect:media", "set:protect:links", "set:protect:text"
}))
async def set_protect_ex(callback: CallbackQuery, db: Database, config: Config) -> None:
    key = callback.data.split(":")[-1]
    mapping = {"media": "content_exclude_media", "links": "content_exclude_links", "text": "content_exclude_text"}
    await db.toggle_cfg(mapping[key])
    await set_protect(callback, db, config)


# ── Notifications ───────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "set:notifs")
async def set_notifs(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    s = await db.get_admin_settings(config.admin_id)
    text = f"<b>{t(lang, 'set_notifications')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'notifications_title')}"
    await callback.message.edit_text(
        text,
        reply_markup=notifications_kb(
            lang, bool(s.get("notify_join", 1)), bool(s.get("notify_ban", 1))
        ),
    )
    await callback.answer()


@router.callback_query(admin, F.data == "set:notifs:help")
async def set_notifs_help(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.answer(t(lang, "notifications_title"), show_alert=True)


@router.callback_query(admin, F.data.in_({"set:notifs:join", "set:notifs:ban"}))
async def set_notifs_toggle(callback: CallbackQuery, db: Database, config: Config) -> None:
    field = "notify_join" if callback.data.endswith("join") else "notify_ban"
    s = await db.get_admin_settings(config.admin_id)
    await db.toggle_notification(config.admin_id, field, not bool(s.get(field, 1)))
    await set_notifs(callback, db, config)


# ── Verification ──────────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "set:verify")
async def set_verify(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    mode = await db.get_cfg("verification_mode", "disabled")
    label = t(lang, VERIFY_LABELS.get(mode, "verify_disabled"))
    pending = await db.count_pending_users()
    text = (
        f"<b>{t(lang, 'verify_title')}</b>\n━━━━━━━━━━━━━━━━\n"
        f"{t(lang, 'verify_current', mode=label)}\n"
        f"{t(lang, 'verify_pending_list', count=pending)}"
    )
    await callback.message.edit_text(text, reply_markup=verification_kb(lang, mode))
    await callback.answer()


@router.callback_query(admin, F.data == "set:verify:help")
async def set_verify_help(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.answer(t(lang, "verify_help"), show_alert=True)


@router.callback_query(admin, F.data.startswith("set:verify:mode:"))
async def set_verify_mode(callback: CallbackQuery, db: Database, config: Config) -> None:
    mode = callback.data.split(":")[-1]
    if mode in VERIFICATION_MODES:
        await db.set_cfg("verification_mode", mode)
    await set_verify(callback, db, config)


# ── Auto delete ───────────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "set:autodel")
async def set_autodel(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    cfg = await db.get_all_cfg()
    on = cfg.get("auto_delete_enabled") == "1"
    status = "🟢" if on else "🔴"
    text = (
        f"<b>{t(lang, 'ad_title')}</b>\n━━━━━━━━━━━━━━━━\n"
        f"{t(lang, 'ad_desc')}\n\n"
        f"{status} {t(lang, 'ad_stats', today=cfg.get('auto_delete_today', '0'), total=cfg.get('auto_delete_total', '0'))}"
    )
    await callback.message.edit_text(text, reply_markup=auto_delete_kb(lang, cfg))
    await callback.answer()


@router.callback_query(admin, F.data == "set:ad:help")
async def set_ad_help(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.answer(t(lang, "ad_help"), show_alert=True)


@router.callback_query(admin, F.data == "set:ad:toggle")
async def set_ad_toggle(callback: CallbackQuery, db: Database, config: Config) -> None:
    await db.toggle_cfg("auto_delete_enabled")
    await set_autodel(callback, db, config)


@router.callback_query(admin, F.data == "set:ad:duration")
async def set_ad_duration(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.message.edit_text(
        t(lang, "ad_duration", minutes=await db.get_cfg("auto_delete_minutes", "5")),
        reply_markup=auto_delete_duration_kb(lang),
    )
    await callback.answer()


@router.callback_query(admin, F.data.startswith("set:ad:mins:"))
async def set_ad_mins(callback: CallbackQuery, db: Database, config: Config) -> None:
    mins = callback.data.split(":")[-1]
    await db.set_cfg("auto_delete_minutes", mins)
    await set_autodel(callback, db, config)


_AD_TOGGLES = {
    "set:ad:private": "auto_delete_private",
    "set:ad:groups": "auto_delete_groups",
    "set:ad:channels": "auto_delete_channels",
    "set:ad:usermsgs": "auto_delete_user_msgs",
    "set:ad:between": "auto_delete_between",
    "set:ad:reaction": "auto_delete_reaction",
    "set:ad:exstart": "auto_delete_ex_start",
    "set:ad:exbuttons": "auto_delete_ex_buttons",
    "set:ad:expayment": "auto_delete_ex_payment",
    "set:ad:exadmin": "auto_delete_ex_admin",
}


@router.callback_query(admin, F.data.in_(_AD_TOGGLES.keys()))
async def set_ad_field_toggle(callback: CallbackQuery, db: Database, config: Config) -> None:
    await db.toggle_cfg(_AD_TOGGLES[callback.data])
    await set_autodel(callback, db, config)


# ── Inactive reminders ────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "set:inactive")
async def set_inactive(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    cfg = await db.get_all_cfg()
    reminders = await db.get_inactive_reminders()
    on = cfg.get("inactive_enabled") == "1"
    status = t(lang, "bot_work_on") if on else t(lang, "bot_work_off")
    text = (
        f"<b>{t(lang, 'inactive_title')}</b>\n━━━━━━━━━━━━━━━━\n"
        f"{t(lang, 'inactive_status', status=status)}\n"
        f"{t(lang, 'inactive_stats', sent=cfg.get('inactive_sent', '0'), returned=cfg.get('inactive_returned', '0'), blocked=cfg.get('inactive_blocked', '0'), waiting=cfg.get('inactive_waiting', '0'))}"
    )
    await callback.message.edit_text(
        text, reply_markup=inactive_kb(lang, cfg, len(reminders))
    )
    await callback.answer()


@router.callback_query(admin, F.data == "set:in:help")
async def set_in_help(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.answer(t(lang, "inactive_help"), show_alert=True)


@router.callback_query(admin, F.data == "set:in:toggle")
async def set_in_toggle(callback: CallbackQuery, db: Database, config: Config) -> None:
    await db.toggle_cfg("inactive_enabled")
    await set_inactive(callback, db, config)


@router.callback_query(admin, F.data.in_({"set:in:exsubs", "set:in:reward"}))
async def set_in_field(callback: CallbackQuery, db: Database, config: Config) -> None:
    key = "inactive_exclude_subs" if "exsubs" in callback.data else "inactive_return_reward"
    await db.toggle_cfg(key)
    await set_inactive(callback, db, config)


@router.callback_query(admin, F.data == "set:in:reset")
async def set_in_reset(callback: CallbackQuery, db: Database, config: Config) -> None:
    for k in ("inactive_sent", "inactive_returned", "inactive_blocked", "inactive_waiting"):
        await db.set_cfg(k, "0")
    await set_inactive(callback, db, config)
    lang = await db.get_admin_language(config.admin_id)
    await callback.answer(t(lang, "setting_saved"))


@router.callback_query(admin, F.data == "set:in:reminders")
async def set_in_reminders(callback: CallbackQuery, db: Database, config: Config) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    lang = await db.get_admin_language(config.admin_id)
    reminders = await db.get_inactive_reminders()
    lines = [f"<b>{t(lang, 'inactive_reminders', count=len(reminders))}</b>", "━━━━━━━━━━━━━━━━"]
    rows = []
    for r in reminders:
        lines.append(f"• {r['days']}d: {r['message_text'][:40]}")
        rows.append([
            InlineKeyboardButton(
                text=f"🗑 {r['days']}d",
                callback_data=f"set:in:delrem:{r['id']}",
            )
        ])
    rows.append([InlineKeyboardButton(text=t(lang, "inactive_add_reminder"), callback_data="set:in:addrem")])
    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="set:inactive")])
    if not reminders:
        lines.append(t(lang, "inactive_no_reminders"))
    await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(admin, F.data == "set:in:addrem")
async def set_in_add_reminder(callback: CallbackQuery, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(InactiveState.waiting_days)
    await callback.message.edit_text(t(lang, "inactive_days_prompt"))
    await callback.answer()


@router.message(admin, InactiveState.waiting_days)
async def set_in_reminder_days(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if not message.text or not message.text.strip().isdigit():
        await message.answer(t(lang, "inactive_days_prompt"))
        return
    await state.update_data(days=int(message.text.strip()))
    await state.set_state(InactiveState.waiting_message)
    await message.answer(t(lang, "inactive_msg_prompt"))


@router.message(admin, InactiveState.waiting_message)
async def set_in_reminder_msg(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if not message.text:
        return
    data = await state.get_data()
    await state.clear()
    ok = await db.add_inactive_reminder(data["days"], message.text.strip())
    if ok:
        await message.answer(t(lang, "inactive_reminder_added"))
    else:
        await message.answer(t(lang, "inactive_reminder_limit"))


@router.callback_query(admin, F.data.startswith("set:in:delrem:"))
async def set_in_del_reminder(callback: CallbackQuery, db: Database, config: Config) -> None:
    rid = int(callback.data.split(":")[-1])
    await db.delete_inactive_reminder(rid)
    await set_in_reminders(callback, db, config)


@router.callback_query(admin, F.data == "set:in:hours")
async def set_in_hours(callback: CallbackQuery, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(InactiveState.waiting_hours)
    cfg = await db.get_all_cfg()
    await callback.message.edit_text(
        t(lang, "inactive_hours_prompt", start=cfg.get("inactive_hours_start", "0"), end=cfg.get("inactive_hours_end", "24"))
    )
    await callback.answer()


@router.message(admin, InactiveState.waiting_hours)
async def set_in_hours_receive(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if not message.text:
        return
    parts = message.text.strip().replace("-", " ").split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer(t(lang, "inactive_hours_format"))
        return
    await state.clear()
    await db.set_cfg("inactive_hours_start", parts[0])
    await db.set_cfg("inactive_hours_end", parts[1])
    await message.answer(t(lang, "setting_saved"))


@router.callback_query(admin, F.data.startswith("set:qr:edit:"))
async def set_qr_edit(callback: CallbackQuery, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    slot = int(callback.data.split(":")[-1])
    await state.update_data(slot=slot)
    await state.set_state(QuickReplyState.waiting_content)
    await callback.message.edit_text(t(lang, "qr_content_prompt"))
    await callback.answer()


@router.callback_query(admin, F.data == "set:verify:config")
async def set_verify_config(callback: CallbackQuery, db: Database, config: Config) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    lang = await db.get_admin_language(config.admin_id)
    url = await db.get_cfg("verification_website_url")
    code = await db.get_cfg("verification_invite_code")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "verify_set_url"), callback_data="set:verify:url")],
            [InlineKeyboardButton(text=t(lang, "verify_set_code"), callback_data="set:verify:code")],
            [
                InlineKeyboardButton(
                    text=toggle_btn(t(lang, "verify_auto_clean"), await db.get_cfg_bool("verification_auto_clean"), suffix=True),
                    callback_data="set:verify:autoclean",
                )
            ],
            [InlineKeyboardButton(text=t(lang, "verify_pending", count=await db.count_pending_users()), callback_data="set:verify:pending")],
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="set:verify")],
        ]
    )
    await callback.message.edit_text(
        f"<b>{t(lang, 'verify_config')}</b>\n━━━━━━━━━━━━━━━━\n"
        f"URL: {url}\nCode: {code}",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(admin, F.data == "set:verify:autoclean")
async def set_verify_autoclean(callback: CallbackQuery, db: Database, config: Config) -> None:
    await db.toggle_cfg("verification_auto_clean")
    await set_verify_config(callback, db, config)


@router.callback_query(admin, F.data == "set:verify:url")
async def set_verify_url(callback: CallbackQuery, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(FinanceState.waiting_website_url)
    await callback.message.edit_text(t(lang, "verify_url_prompt"))
    await callback.answer()


@router.callback_query(admin, F.data == "set:verify:code")
async def set_verify_code(callback: CallbackQuery, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(FinanceState.waiting_invite_code)
    await callback.message.edit_text(t(lang, "verify_code_prompt"))
    await callback.answer()


@router.message(admin, FinanceState.waiting_website_url)
async def verify_url_receive(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if message.text:
        await state.clear()
        await db.set_cfg("verification_website_url", message.text.strip())
        await message.answer(t(lang, "setting_saved"))


@router.message(admin, FinanceState.waiting_invite_code)
async def verify_code_receive(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if message.text:
        await state.clear()
        await db.set_cfg("verification_invite_code", message.text.strip())
        await message.answer(t(lang, "setting_saved"))


# ── Quick replies ─────────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "set:qreplies")
async def set_qreplies(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    replies = await db.get_quick_replies()
    text = f"<b>{t(lang, 'qr_title')}</b>\n━━━━━━━━━━━━━━━━"
    await callback.message.edit_text(text, reply_markup=quick_replies_kb(lang, replies))
    await callback.answer()


@router.callback_query(admin, F.data == "set:qr:help")
async def set_qr_help(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.answer(t(lang, "qr_help"), show_alert=True)


@router.callback_query(admin, F.data == "set:qr:add")
async def set_qr_add(callback: CallbackQuery, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(QuickReplyState.waiting_slot)
    await callback.message.edit_text(t(lang, "qr_slot_prompt"))
    await callback.answer()


@router.message(admin, QuickReplyState.waiting_slot)
async def qr_receive_slot(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if not message.text or not message.text.strip().isdigit():
        await message.answer(t(lang, "qr_slot_prompt"))
        return
    slot = int(message.text.strip())
    if slot < 1 or slot > 20:
        await message.answer("1-20")
        return
    await state.update_data(slot=slot)
    await state.set_state(QuickReplyState.waiting_content)
    await message.answer(t(lang, "qr_content_prompt"))


@router.message(admin, QuickReplyState.waiting_content)
async def qr_receive_content(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    data = await state.get_data()
    slot = data.get("slot", 1)
    await state.clear()
    if message.photo:
        await db.save_quick_reply(slot, media_type="photo", file_id=message.photo[-1].file_id, caption=message.caption)
    elif message.video:
        await db.save_quick_reply(slot, media_type="video", file_id=message.video.file_id, caption=message.caption)
    elif message.text:
        await db.save_quick_reply(slot, reply_text=message.text)
    else:
        await message.answer(t(lang, "no_content"))
        return
    await message.answer(t(lang, "qr_saved", slot=slot))
    replies = await db.get_quick_replies()
    await message.answer(t(lang, "qr_title"), reply_markup=quick_replies_kb(lang, replies))


@router.callback_query(admin, F.data.startswith("set:qr:view:"))
async def set_qr_view(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    slot = int(callback.data.split(":")[-1])
    r = await db.get_quick_reply(slot)
    if not r:
        await callback.answer()
        return
    preview = r.get("reply_text") or r.get("caption") or "—"
    await callback.message.edit_text(
        f"/r{slot}: {preview}", reply_markup=qr_item_kb(lang, slot)
    )
    await callback.answer()


@router.callback_query(admin, F.data.startswith("set:qr:del:"))
async def set_qr_del(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    slot = int(callback.data.split(":")[-1])
    await db.delete_quick_reply(slot)
    await callback.answer(t(lang, "qr_deleted"))
    await set_qreplies(callback, db, config)


# ── System ────────────────────────────────────────────────────────────────────
async def menu_system(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    text = f"<b>{t(lang, 'sys_title')}</b>\n━━━━━━━━━━━━━━━━\n{t(lang, 'sys_info')}"
    await callback.message.edit_text(text, reply_markup=system_kb(lang))
    await callback.answer()


# System actions handled in system.py


# ── Guide ─────────────────────────────────────────────────────────────────────

@router.callback_query(admin, F.data == "menu:guide")
async def menu_guide(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.message.edit_text(
        f"<b>{t(lang, 'guide_title')}</b>\n━━━━━━━━━━━━━━━━",
        reply_markup=guide_sections_kb(lang),
    )
    await callback.answer()


_GUIDE_MAP = {
    "guide:settings": "guide_text_settings",
    "guide:content": "guide_text_content",
    "guide:users": "guide_text_users",
    "guide:subscription": "guide_text_subscription",
    "guide:communication": "guide_text_communication",
    "guide:finance": "guide_text_finance",
}


@router.callback_query(admin, F.data.in_(_GUIDE_MAP.keys()))
async def guide_section(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    key = _GUIDE_MAP[callback.data]
    from bot.keyboards.inline import back_button
    from aiogram.types import InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[[back_button(lang, "menu:guide")]])
    await callback.message.edit_text(t(lang, key), reply_markup=kb)
    await callback.answer()

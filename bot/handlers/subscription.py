from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.database.db import Database
from bot.filters.admin import AdminFilter
from bot.keyboards.inline import sub_item_kb, sub_list_kb, subscription_kb
from bot.locales import t
from bot.utils.states import SubState

router = Router()
admin = AdminFilter()


async def _sub_menu(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    sub_cfg = await db.get_sub_settings()
    subs = await db.get_mandatory_subs()
    enabled = bool(sub_cfg.get("is_enabled"))
    notify = bool(sub_cfg.get("notify_on_join", 1))
    grouped = bool(sub_cfg.get("display_grouped", 1))
    verify_btn = bool(sub_cfg.get("verify_button", 0))
    status = t(lang, "sub_status_on") if enabled else t(lang, "sub_status_off")
    text = (
        f"<b>{t(lang, 'sub_title')}</b>\n━━━━━━━━━━━━━━━━\n"
        f"الحالة: {status}\n"
        f"{t(lang, 'sub_channels_count', count=len(subs))}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=subscription_kb(lang, enabled, len(subs), notify, grouped, verify_btn),
    )


@router.callback_query(admin, F.data == "sub:toggle")
async def sub_toggle(callback: CallbackQuery, db: Database, config: Config) -> None:
    sub_cfg = await db.get_sub_settings()
    current = bool(sub_cfg.get("is_enabled"))
    await db.set_sub_enabled(not current)
    await _sub_menu(callback, db, config)
    await callback.answer()


@router.callback_query(admin, F.data == "sub:notify:toggle")
async def sub_notify_toggle(
    callback: CallbackQuery, db: Database, config: Config
) -> None:
    sub_cfg = await db.get_sub_settings()
    current = bool(sub_cfg.get("notify_on_join", 1))
    await db.update_sub_setting("notify_on_join", int(not current))
    await _sub_menu(callback, db, config)
    await callback.answer()


@router.callback_query(admin, F.data == "sub:display:toggle")
async def sub_display_toggle(callback: CallbackQuery, db: Database, config: Config) -> None:
    sub_cfg = await db.get_sub_settings()
    current = bool(sub_cfg.get("display_grouped", 1))
    await db.update_sub_setting("display_grouped", int(not current))
    await _sub_menu(callback, db, config)
    await callback.answer()


@router.callback_query(admin, F.data == "sub:verify:toggle")
async def sub_verify_toggle(callback: CallbackQuery, db: Database, config: Config) -> None:
    sub_cfg = await db.get_sub_settings()
    current = bool(sub_cfg.get("verify_button", 0))
    await db.update_sub_setting("verify_button", int(not current))
    await _sub_menu(callback, db, config)
    await callback.answer()


@router.callback_query(admin, F.data == "sub:grouped:msg")
async def sub_grouped_msg(callback: CallbackQuery, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(SubState.waiting_grouped_msg)
    await callback.message.edit_text(t(lang, "sub_grouped_prompt"))
    await callback.answer()


@router.message(admin, SubState.waiting_grouped_msg)
async def sub_receive_grouped_msg(message: Message, db: Database, config: Config, state: FSMContext) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.clear()
    await db.update_sub_setting("grouped_message", message.text or "")
    await message.answer(t(lang, "sub_grouped_saved"))


@router.callback_query(admin, F.data == "sub:help")
async def sub_help(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await callback.answer(t(lang, "guide_text_subscription"), show_alert=True)


@router.callback_query(admin, F.data == "sub:add")
async def sub_add(
    callback: CallbackQuery, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    subs = await db.get_mandatory_subs()
    if len(subs) >= 10:
        await callback.answer(t(lang, "sub_max_reached"), show_alert=True)
        return
    await state.set_state(SubState.waiting_channel)
    await callback.message.edit_text(t(lang, "sub_add_prompt"))
    await callback.answer()


@router.message(admin, SubState.waiting_channel)
async def sub_receive_channel(
    message: Message, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.clear()
    raw = message.text.strip() if message.text else ""

    try:
        chat = await message.bot.get_chat(raw)
        invite_link = None
        if not chat.username:
            try:
                link_obj = await message.bot.create_chat_invite_link(chat.id)
                invite_link = link_obj.invite_link
            except Exception:
                pass

        added = await db.add_mandatory_sub(
            chat_id=chat.id,
            chat_type=chat.type,
            title=chat.title,
            username=chat.username,
            invite_link=invite_link,
        )
        if added:
            await message.answer(t(lang, "sub_added", title=chat.title or raw))
        else:
            await message.answer(t(lang, "sub_already_exists"))
    except Exception:
        await message.answer(t(lang, "sub_not_found"))


@router.callback_query(admin, F.data == "sub:list")
async def sub_list(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    subs = await db.get_mandatory_subs()
    text = f"<b>{t(lang, 'sub_list', count=len(subs))}</b>\n━━━━━━━━━━━━━━━━"
    await callback.message.edit_text(text, reply_markup=sub_list_kb(lang, subs))
    await callback.answer()


@router.callback_query(admin, F.data.startswith("sub:view:"))
async def sub_view(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    sub_id = int(callback.data.split(":")[-1])
    subs = await db.get_mandatory_subs()
    s = next((x for x in subs if x["id"] == sub_id), None)
    if not s:
        await callback.answer()
        return
    title = s.get("title") or s.get("username") or str(s["chat_id"])
    link = s.get("invite_link") or (f"@{s['username']}" if s.get("username") else "—")
    text = f"<b>🏠 {title}</b>\nID: <code>{s['chat_id']}</code>\nLink: {link}"
    await callback.message.edit_text(text, reply_markup=sub_item_kb(lang, sub_id))
    await callback.answer()


@router.callback_query(admin, F.data.startswith("sub:del:"))
async def sub_delete(callback: CallbackQuery, db: Database, config: Config) -> None:
    sub_id = int(callback.data.split(":")[-1])
    await db.remove_mandatory_sub(sub_id)
    await _sub_menu(callback, db, config)
    await callback.answer()

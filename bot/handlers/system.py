from __future__ import annotations

import os
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.config import Config
from bot.database.db import Database
from bot.filters.admin import AdminFilter
from bot.keyboards.menus import system_kb
from bot.locales import t
from bot.utils.states import FinanceState

router = Router()
admin = AdminFilter()


@router.callback_query(admin, F.data == "sys:backup")
async def sys_backup(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    db_path = config.database_path
    if not os.path.exists(db_path):
        await callback.answer(t(lang, "sys_backup_fail"), show_alert=True)
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{stamp}.db"
    with open(db_path, "rb") as f:
        data = f.read()
    await callback.bot.send_document(
        config.admin_id,
        BufferedInputFile(data, filename=backup_name),
        caption=t(lang, "sys_backup_done", date=stamp),
    )
    await db.log_activity("backup", backup_name, config.admin_id)
    await callback.answer(t(lang, "sys_backup_sent"))


@router.callback_query(admin, F.data == "sys:logs")
async def sys_logs(callback: CallbackQuery, db: Database, config: Config) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from bot.keyboards.inline import back_button

    lang = await db.get_admin_language(config.admin_id)
    logs = await db.get_activity_logs(limit=15)
    if not logs:
        text = t(lang, "sys_logs_empty")
    else:
        lines = [f"<b>{t(lang, 'sys_logs_title')}</b>", "━━━━━━━━━━━━━━━━"]
        for log in logs:
            ts = log["created_at"][:16].replace("T", " ")
            lines.append(f"• [{ts}] {log['action']}: {log.get('details') or '—'}")
        text = "\n".join(lines)
    kb = InlineKeyboardMarkup(inline_keyboard=[[back_button(lang, "menu:system")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(admin, F.data == "sys:admins")
async def sys_admins(callback: CallbackQuery, db: Database, config: Config) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from bot.keyboards.inline import back_button

    lang = await db.get_admin_language(config.admin_id)
    admins = await db.get_bot_admins()
    lines = [
        f"<b>{t(lang, 'sys_admins_title')}</b>",
        "━━━━━━━━━━━━━━━━",
        f"👑 {config.admin_id} ({t(lang, 'sys_primary_admin')})",
    ]
    rows = []
    for a in admins:
        lines.append(f"• {a['user_id']}")
        rows.append([
            InlineKeyboardButton(
                text=f"❌ {a['user_id']}",
                callback_data=f"sys:rmadmin:{a['user_id']}",
            )
        ])
    rows.append([
        InlineKeyboardButton(text=t(lang, "sys_add_admin"), callback_data="sys:addadmin"),
    ])
    rows.append([back_button(lang, "menu:system")])
    lines.append(f"\n{t(lang, 'sys_admins_count', count=len(admins) + 1)}")
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(admin, F.data == "sys:addadmin")
async def sys_add_admin_prompt(
    callback: CallbackQuery, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(FinanceState.waiting_admin_id)
    await callback.message.edit_text(t(lang, "sys_admin_id_prompt"))
    await callback.answer()


@router.message(admin, FinanceState.waiting_admin_id)
async def sys_add_admin_receive(
    message: Message, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.clear()
    if not message.text or not message.text.strip().isdigit():
        await message.answer(t(lang, "sys_admin_id_prompt"))
        return
    uid = int(message.text.strip())
    if uid == config.admin_id:
        await message.answer(t(lang, "sys_admin_exists"))
        return
    ok = await db.add_bot_admin(uid, config.admin_id)
    if ok:
        await db.log_activity("add_admin", str(uid), config.admin_id)
        await message.answer(t(lang, "sys_admin_added", id=uid))
    else:
        await message.answer(t(lang, "sys_admin_exists"))


@router.callback_query(admin, F.data.startswith("sys:rmadmin:"))
async def sys_remove_admin(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    uid = int(callback.data.split(":")[-1])
    await db.remove_bot_admin(uid)
    await db.log_activity("remove_admin", str(uid), config.admin_id)
    await callback.answer(t(lang, "sys_admin_removed"))
    await sys_admins(callback, db, config)

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.database.db import Database
from bot.filters.admin import AdminFilter
from bot.keyboards.inline import banned_list_kb, user_card_kb, users_menu_kb
from bot.locales import t
from bot.utils.states import UsersState

router = Router()
admin = AdminFilter()


def _format_user_card(lang: str, u: dict) -> str:
    status = (
        t(lang, "user_status_banned")
        if u.get("is_blocked")
        else t(lang, "user_status_active")
    )
    username = f"@{u['username']}" if u.get("username") else "—"
    created = (u.get("created_at") or "—")[:10]
    return t(
        lang,
        "user_card",
        name=u.get("first_name") or "—",
        username=username,
        user_id=u["user_id"],
        lang=u.get("language_code") or "—",
        status=status,
        created_at=created,
    )


@router.callback_query(admin, F.data == "usr:search")
async def usr_search(
    callback: CallbackQuery, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.set_state(UsersState.waiting_search)
    await callback.message.edit_text(t(lang, "users_search_prompt"))
    await callback.answer()


@router.message(admin, UsersState.waiting_search)
async def usr_receive_search(
    message: Message, db: Database, config: Config, state: FSMContext
) -> None:
    lang = await db.get_admin_language(config.admin_id)
    await state.clear()
    raw = message.text.strip() if message.text else ""

    user = None
    if raw.lstrip("@").isdigit():
        user = await db.get_user(int(raw.lstrip("@")))
    elif raw.startswith("@"):
        from bot.database.db import Database
        cur = await db.conn.execute(
            "SELECT * FROM users WHERE username=?", (raw.lstrip("@"),)
        )
        row = await cur.fetchone()
        if row:
            user = dict(row)

    if not user:
        await message.answer(t(lang, "users_not_found"))
        return

    text = _format_user_card(lang, user)
    await message.answer(
        text,
        reply_markup=user_card_kb(lang, user["user_id"], bool(user.get("is_blocked"))),
    )


@router.callback_query(admin, F.data.startswith("usr:card:"))
async def usr_card(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    user_id = int(callback.data.split(":")[-1])
    user = await db.get_user(user_id)
    if not user:
        await callback.answer(t(lang, "users_not_found"))
        return
    text = _format_user_card(lang, user)
    await callback.message.edit_text(
        text,
        reply_markup=user_card_kb(lang, user_id, bool(user.get("is_blocked"))),
    )
    await callback.answer()


@router.callback_query(admin, F.data.startswith("usr:ban:"))
async def usr_ban(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    user_id = int(callback.data.split(":")[-1])
    await db.ban_user(user_id)
    await callback.answer(t(lang, "ban_confirm", user_id=user_id), show_alert=True)
    user = await db.get_user(user_id)
    if user:
        text = _format_user_card(lang, user)
        await callback.message.edit_text(
            text,
            reply_markup=user_card_kb(lang, user_id, True),
        )


@router.callback_query(admin, F.data.startswith("usr:unban:"))
async def usr_unban(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    user_id = int(callback.data.split(":")[-1])
    await db.unban_user(user_id)
    await callback.answer(t(lang, "unban_confirm", user_id=user_id), show_alert=True)
    user = await db.get_user(user_id)
    if user:
        text = _format_user_card(lang, user)
        await callback.message.edit_text(
            text,
            reply_markup=user_card_kb(lang, user_id, False),
        )


@router.callback_query(admin, F.data == "usr:banned")
async def usr_banned_list(callback: CallbackQuery, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    banned = await db.get_banned_users()
    text = f"<b>{t(lang, 'users_banned_list', count=len(banned))}</b>\n━━━━━━━━━━━━━━━━"
    if not banned:
        text += f"\n{t(lang, 'banned_list_empty')}"
    await callback.message.edit_text(text, reply_markup=banned_list_kb(lang, banned))
    await callback.answer()

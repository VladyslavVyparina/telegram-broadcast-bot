from __future__ import annotations

import random

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot.config import Config
from bot.database.db import Database
from bot.locales import t
from bot.utils.states import VerificationState

router = Router()


def _captcha_kb(correct: str, options: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=opt, callback_data=f"verify:cap:{opt}")
        for opt in options
    ]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def start_verification(
    message: Message,
    db: Database,
    state: FSMContext | None,
    lang: str = "ar",
    *,
    user=None,
) -> bool:
    """Return True if verification flow started (blocks welcome)."""
    from_user = user or message.from_user
    if not from_user:
        return False
    if await db.is_user_verified(from_user.id):
        return False

    mode = await db.get_cfg("verification_mode", "disabled")
    if mode == "disabled":
        return False

    if mode == "approval":
        pending = await db.get_pending_users()
        if any(p["user_id"] == from_user.id for p in pending):
            await message.answer(t(lang, "verify_wait_approval"))
            return True
        await db.add_pending_user(from_user.id, from_user.username, from_user.first_name)
        await message.answer(t(lang, "verify_wait_approval"))
        return True

    session = await db.get_verification_session(from_user.id)
    if session and session.get("passed"):
        return False

    if mode == "captcha":
        await _send_captcha(message, db, lang, from_user)
        return True
    if mode == "website":
        await _send_website(message, db, lang)
        return True
    if mode == "phone":
        await _send_phone(message, lang)
        return True
    if mode == "invitation":
        if state:
            await _send_invitation(message, db, state, lang)
        else:
            await message.answer(t(lang, "verify_invite_prompt"))
        return True
    return False


async def _send_captcha(message: Message, db: Database, lang: str, user) -> None:
    code = f"{random.randint(1000, 9999)}"
    await db.save_verification_session(user.id, "captcha", code)
    options = [code]
    while len(options) < 4:
        wrong = f"{random.randint(1000, 9999)}"
        if wrong not in options:
            options.append(wrong)
    random.shuffle(options)
    text = t(lang, "verify_captcha_prompt", code_hint="****")
    await message.answer(text, reply_markup=_captcha_kb(code, options))


async def _send_website(message: Message, db: Database, lang: str = "ar") -> None:
    url = await db.get_cfg("verification_website_url", "https://telegram.org")
    await db.save_verification_session(message.from_user.id, "website", url)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "verify_visit_site"), url=url)],
            [InlineKeyboardButton(text=t(lang, "verify_confirm"), callback_data="verify:web:ok")],
        ]
    )
    await message.answer(t(lang, "verify_website_prompt"), reply_markup=kb)


async def _send_phone(message: Message, lang: str = "ar") -> None:
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "verify_share_phone"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(t(lang, "verify_phone_prompt"), reply_markup=kb)


async def _send_invitation(message: Message, db: Database, state: FSMContext, lang: str = "ar") -> None:
    await state.set_state(VerificationState.waiting_invite)
    await message.answer(t(lang, "verify_invite_prompt"))


@router.callback_query(F.data.startswith("verify:cap:"))
async def verify_captcha_answer(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not callback.from_user:
        return
    answer = callback.data.split(":")[-1]
    session = await db.get_verification_session(callback.from_user.id)
    if not session or session.get("mode") != "captcha":
        await callback.answer()
        return
    lang = config.default_language
    if answer == session.get("challenge"):
        await db.mark_verification_passed(callback.from_user.id)
        await callback.message.edit_text(t(lang, "verify_success"))
        await callback.answer(t(lang, "verify_success"))
    else:
        await callback.answer(t(lang, "verify_wrong"), show_alert=True)


@router.callback_query(F.data == "verify:web:ok")
async def verify_website_confirm(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not callback.from_user:
        return
    session = await db.get_verification_session(callback.from_user.id)
    lang = config.default_language
    if session and session.get("mode") == "website":
        await db.mark_verification_passed(callback.from_user.id)
        await callback.message.edit_text(t(lang, "verify_success"))
        await callback.answer()
    else:
        await callback.answer()


@router.message(F.contact)
async def verify_phone_contact(message: Message, db: Database, config: Config) -> None:
    if not message.from_user or not message.contact:
        return
    if message.contact.user_id != message.from_user.id:
        return
    mode = await db.get_cfg("verification_mode", "disabled")
    if mode != "phone":
        return
    lang = config.default_language
    await db.mark_verification_passed(message.from_user.id, phone=message.contact.phone_number)
    await message.answer(t(lang, "verify_success"), reply_markup=ReplyKeyboardRemove())


@router.message(VerificationState.waiting_invite)
async def verify_invite_code(
    message: Message, db: Database, config: Config, state: FSMContext
) -> None:
    if not message.from_user or not message.text:
        return
    lang = config.default_language
    expected = await db.get_cfg("verification_invite_code", "WELCOME")
    if message.text.strip().upper() == expected.upper():
        await state.clear()
        await db.mark_verification_passed(message.from_user.id)
        await message.answer(t(lang, "verify_success"))
    else:
        await message.answer(t(lang, "verify_wrong"))


# ── Admin: pending approval ───────────────────────────────────────────────────

@router.callback_query(F.data == "set:verify:pending")
async def verify_pending_list(callback: CallbackQuery, db: Database, config: Config) -> None:
    from bot.filters.admin import AdminFilter

    if not await AdminFilter()(callback, config=config):
        return
    lang = await db.get_admin_language(config.admin_id)
    pending = await db.get_pending_users()
    if not pending:
        await callback.answer(t(lang, "verify_no_pending"), show_alert=True)
        return
    rows = []
    for p in pending[:10]:
        name = p.get("first_name") or p.get("username") or str(p["user_id"])
        rows.append([
            InlineKeyboardButton(
                text=f"✅ {name}",
                callback_data=f"verify:approve:{p['user_id']}",
            ),
            InlineKeyboardButton(
                text=f"❌",
                callback_data=f"verify:reject:{p['user_id']}",
            ),
        ])
    rows.append([
        InlineKeyboardButton(text=t(lang, "back"), callback_data="set:verify"),
    ])
    await callback.message.edit_text(
        t(lang, "verify_pending_title", count=len(pending)),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("verify:approve:"))
async def verify_approve(callback: CallbackQuery, db: Database, config: Config) -> None:
    from bot.filters.admin import AdminFilter

    if not await AdminFilter()(callback, config=config):
        return
    lang = await db.get_admin_language(config.admin_id)
    user_id = int(callback.data.split(":")[-1])
    await db.remove_pending_user(user_id)
    await db.mark_verification_passed(user_id)
    await db.log_activity("verify_approve", str(user_id), config.admin_id)
    try:
        await callback.bot.send_message(user_id, t(config.default_language, "verify_approved"))
    except Exception:
        pass
    await callback.answer(t(lang, "verify_approved_admin"))
    await verify_pending_list(callback, db, config)


@router.callback_query(F.data.startswith("verify:reject:"))
async def verify_reject(callback: CallbackQuery, db: Database, config: Config) -> None:
    from bot.filters.admin import AdminFilter

    if not await AdminFilter()(callback, config=config):
        return
    lang = await db.get_admin_language(config.admin_id)
    user_id = int(callback.data.split(":")[-1])
    await db.remove_pending_user(user_id)
    await db.log_activity("verify_reject", str(user_id), config.admin_id)
    await callback.answer(t(lang, "verify_rejected_admin"))
    await verify_pending_list(callback, db, config)

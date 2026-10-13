from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, User

import os

from bot.config import Config
from bot.database.db import Database
from bot.handlers.verification import start_verification
from bot.keyboards.inline import build_content_buttons_kb, build_sub_check_kb, main_menu_kb
from bot.locales import t
from bot.services.admin_notify import notify_new_user

router = Router()


async def build_panel_text(db: Database, lang: str) -> str:
    stats = await db.get_today_stats()
    users = await db.count_users()
    groups = await db.count_groups()
    banned = await db.count_banned()
    total = users + groups

    return (
        f"<b>{t(lang, 'panel_title')}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<b>{t(lang, 'stats_today')}</b>\n"
        f"{t(lang, 'stats_total')}: {total} 👤\n"
        f"{t(lang, 'stats_new_users')}: {stats['new_users']} 📈\n"
        f"{t(lang, 'stats_messages')}: {stats['messages']} 📈\n"
        f"{t(lang, 'stats_sessions')}: {stats['sessions']}\n\n"
        f"{t(lang, 'stats_users_count')}: {users}\n"
        f"{t(lang, 'stats_groups_count')}: {groups}\n"
        f"{t(lang, 'stats_banned')}: {banned}"
    )


async def _check_mandatory_sub(bot, user_id: int, db: Database) -> bool:
    sub_settings = await db.get_sub_settings()
    if not sub_settings.get("is_enabled"):
        return True
    subs = await db.get_mandatory_subs()
    if not subs:
        return True
    for sub in subs:
        try:
            member = await bot.get_chat_member(sub["chat_id"], user_id)
            if member.status in ("left", "kicked"):
                return False
        except Exception:
            pass
    return True


async def _build_sub_prompt(db: Database, lang: str) -> tuple[str, InlineKeyboardMarkup | None]:
    subs = await db.get_mandatory_subs()
    sub_settings = await db.get_sub_settings()
    grouped = bool(sub_settings.get("display_grouped", 1))
    grouped_msg = sub_settings.get("grouped_message") or ""

    if grouped and grouped_msg:
        text = grouped_msg
    else:
        lines = [t(lang, "sub_required")]
        for s in subs:
            if s.get("invite_link"):
                lines.append(f"• {s.get('title') or s.get('username')}: {s['invite_link']}")
            elif s.get("username"):
                lines.append(f"• @{s['username'].lstrip('@')}")
        text = "\n".join(lines)

    verify_btn = bool(sub_settings.get("verify_button", 0))
    kb = build_sub_check_kb(lang, subs, show_verify=verify_btn)
    return text, kb


async def send_welcome_message(
    message: Message,
    db: Database,
    config: Config,
    user: User,
) -> None:
    lang = config.default_language
    wm = await db.get_welcome_message()
    buttons = await db.get_content_buttons()
    markup = build_content_buttons_kb(buttons) if buttons else None

    content: dict = {"content_type": "text", "text": wm.get("text") or t(lang, "welcome_user")}
    media_type = wm.get("media_type")
    file_id = wm.get("file_id")
    if media_type == "photo" and file_id:
        content = {"content_type": "photo", "file_id": file_id, "caption": wm.get("text") or ""}
    elif media_type == "video" and file_id:
        content = {"content_type": "video", "file_id": file_id, "caption": wm.get("text") or ""}

    from bot.utils.sender import bot_send_content

    await bot_send_content(
        message.bot,
        db,
        user.id,
        content,
        reply_markup=markup,
        is_start=True,
    )


async def send_user_welcome(
    message: Message,
    db: Database,
    config: Config,
    user: User,
    *,
    is_new: bool = False,
) -> None:
    await send_welcome_message(message, db, config, user)
    await notify_new_user(message.bot, db, config, user, is_new=is_new)


@router.message(CommandStart())
async def cmd_start(
    message: Message, db: Database, config: Config, state: FSMContext
) -> None:
    user = message.from_user
    if not user:
        return

    is_new = await db.upsert_user(
        user.id, user.username, user.first_name, user.language_code
    )
    await db.touch_user_activity(user.id)
    await db.increment_sessions()
    await db.increment_messages()

    if await db.is_admin(user.id, config.admin_id):
        lang = await db.get_admin_language(config.admin_id, config.default_language)
        settings = await db.get_admin_settings(config.admin_id)
        text = await build_panel_text(db, lang)
        await message.answer(
            text,
            reply_markup=main_menu_kb(
                lang,
                notify_join=bool(settings.get("notify_join", 1)),
                notify_ban=bool(settings.get("notify_ban", 1)),
            ),
        )
        return

    existing = await db.get_user(user.id)
    if existing and existing.get("is_blocked"):
        await message.answer(t(config.default_language, "user_banned"))
        return

    if not await db.get_cfg_bool("bot_enabled"):
        await message.answer(t(config.default_language, "bot_work_off"))
        return

    platform_bot = os.getenv("CLONE_PLATFORM_BOT", "").strip().lstrip("@")
    if platform_bot:
        lang = config.default_language
        me = await message.bot.get_me()
        bot_name = me.full_name or me.username or "Bot"
        await message.answer(
            t(
                lang,
                "clone_user_welcome",
                bot_name=bot_name,
                user_id=user.id,
                platform_bot=platform_bot,
            ),
        )
        await notify_new_user(message.bot, db, config, user, is_new=is_new)
        if not await _check_mandatory_sub(message.bot, user.id, db):
            text, kb = await _build_sub_prompt(db, lang)
            await message.answer(text, reply_markup=kb)
        return

    await send_welcome_message(message, db, config, user)
    await notify_new_user(message.bot, db, config, user, is_new=is_new)

    if not await _check_mandatory_sub(message.bot, user.id, db):
        lang = config.default_language
        text, kb = await _build_sub_prompt(db, lang)
        await message.answer(text, reply_markup=kb)
        return

    mode = await db.get_cfg("verification_mode", "disabled")
    if mode == "disabled":
        await db.set_user_verified(user.id)
    elif not await db.is_user_verified(user.id):
        blocked = await start_verification(message, db, state, config.default_language)
        if blocked:
            return


@router.callback_query(F.data == "sub:check")
async def sub_check_callback(
    callback: CallbackQuery, db: Database, config: Config, state: FSMContext
) -> None:
    if not callback.from_user:
        return
    lang = config.default_language
    if await _check_mandatory_sub(callback.bot, callback.from_user.id, db):
        await callback.answer(t(lang, "sub_verified_ok"), show_alert=True)
        mode = await db.get_cfg("verification_mode", "disabled")
        if mode != "disabled" and not await db.is_user_verified(callback.from_user.id):
            blocked = await start_verification(
                callback.message, db, state, lang, user=callback.from_user
            )
            if blocked:
                return
    else:
        await callback.answer(t(lang, "sub_not_joined"), show_alert=True)

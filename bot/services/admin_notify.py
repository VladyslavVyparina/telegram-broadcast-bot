from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import ChatMember, User

from bot.config import Config
from bot.database.db import Database
from bot.locales import t

logger = logging.getLogger(__name__)


def format_username(user: User | None, lang: str) -> str:
    if user and user.username:
        return f"@{user.username}"
    return t(lang, "no_username")


def format_lang(code: str | None, lang: str) -> str:
    return code or t(lang, "dash")


def bot_role_label(member: ChatMember, lang: str) -> str:
    if member.status == "creator":
        return t(lang, "bot_role_creator")
    if member.status == "administrator":
        return t(lang, "bot_role_admin")
    return t(lang, "bot_role_member")


def user_info_block(user: User | None, lang: str, *, header_key: str) -> str:
    if not user:
        return ""
    return (
        f"{t(lang, header_key)}\n"
        f"{t(lang, 'new_user_name')}: {user.first_name or t(lang, 'dash')}\n"
        f"{t(lang, 'new_user_username')}: {format_username(user, lang)}\n"
        f"{t(lang, 'new_user_id')}: <code>{user.id}</code>\n"
        f"{t(lang, 'new_user_lang')}: {format_lang(user.language_code, lang)}"
    )


async def admin_recipient_ids(db: Database, primary_admin_id: int) -> list[int]:
    ids = {primary_admin_id}
    for row in await db.get_bot_admins():
        ids.add(int(row["user_id"]))
    return list(ids)


async def notify_admins(bot: Bot, db: Database, config: Config, text: str) -> None:
    for admin_id in await admin_recipient_ids(db, config.admin_id):
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            logger.exception("Failed to notify admin %s", admin_id)


async def notify_new_user(
    bot: Bot, db: Database, config: Config, user: User, *, is_new: bool
) -> None:
    if not is_new:
        return
    settings = await db.get_admin_settings(config.admin_id)
    if not settings.get("notify_join", 1):
        return
    lang = await db.get_admin_language(config.admin_id, config.default_language)
    total = await db.count_users()
    text = (
        f"<b>{t(lang, 'new_user_title')}</b>\n\n"
        f"{user_info_block(user, lang, header_key='new_user_info_header')}\n\n"
        f"{t(lang, 'total_users')}: {total}"
    )
    await notify_admins(bot, db, config, text)


async def notify_group_added(
    bot: Bot,
    db: Database,
    config: Config,
    *,
    chat_title: str | None,
    chat_id: int,
    chat_username: str | None,
    member_count: int | None,
    bot_role: str,
    actor: User | None,
) -> None:
    settings = await db.get_admin_settings(config.admin_id)
    if not settings.get("notify_join", 1):
        return
    lang = await db.get_admin_language(config.admin_id, config.default_language)
    users_total = await db.count_users()
    chats_total = await db.count_total_chats()
    uname = f"@{chat_username}" if chat_username else t(lang, "no_username")
    members = member_count if member_count is not None else t(lang, "dash")
    text = (
        f"<b>{t(lang, 'group_added_title')}</b>\n\n"
        f"{t(lang, 'group_info_header')}\n"
        f"{t(lang, 'group_name')}: {chat_title or t(lang, 'dash')}\n"
        f"{t(lang, 'group_id')}: <code>{chat_id}</code>\n"
        f"{t(lang, 'group_username')}: {uname}\n"
        f"{t(lang, 'group_members')}: {members}\n"
        f"{t(lang, 'group_bot_role')}: {bot_role}\n\n"
        f"{user_info_block(actor, lang, header_key='group_added_by_header')}\n\n"
        f"{t(lang, 'total_users')}: {users_total}\n"
        f"{t(lang, 'total_chats')}: {chats_total}"
    )
    await notify_admins(bot, db, config, text)


async def notify_group_removed(
    bot: Bot,
    db: Database,
    config: Config,
    *,
    chat_title: str | None,
    chat_id: int,
    chat_username: str | None,
    actor: User | None,
) -> None:
    settings = await db.get_admin_settings(config.admin_id)
    if not settings.get("notify_ban", 1):
        return
    lang = await db.get_admin_language(config.admin_id, config.default_language)
    total_blocks = await db.increment_bot_blocks()
    uname = f"@{chat_username}" if chat_username else t(lang, "no_username")
    text = (
        f"<b>{t(lang, 'group_removed_title')}</b>\n\n"
        f"{t(lang, 'group_info_header')}\n"
        f"{t(lang, 'group_name')}: {chat_title or t(lang, 'dash')}\n"
        f"{t(lang, 'group_id')}: <code>{chat_id}</code>\n"
        f"{t(lang, 'group_username')}: {uname}\n\n"
        f"{user_info_block(actor, lang, header_key='group_removed_by_header')}\n\n"
        f"{t(lang, 'total_blocks')}: {total_blocks}"
    )
    await notify_admins(bot, db, config, text)


async def notify_private_block(
    bot: Bot, db: Database, config: Config, user: User | None
) -> None:
    settings = await db.get_admin_settings(config.admin_id)
    if not settings.get("notify_ban", 1):
        return
    lang = await db.get_admin_language(config.admin_id, config.default_language)
    total_blocks = await db.increment_bot_blocks()
    text = (
        f"<b>{t(lang, 'private_block_title')}</b>\n\n"
        f"{user_info_block(user, lang, header_key='block_user_info_header')}\n\n"
        f"{t(lang, 'total_blocks')}: {total_blocks}"
    )
    await notify_admins(bot, db, config, text)

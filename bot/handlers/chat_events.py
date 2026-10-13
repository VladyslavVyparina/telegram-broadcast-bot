from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.types import ChatMemberUpdated, Message

from bot.config import Config
from bot.database.db import Database
from bot.services.admin_notify import (
    bot_role_label,
    notify_group_added,
    notify_group_removed,
    notify_private_block,
)
from bot.services.group_invite import send_group_welcome

logger = logging.getLogger(__name__)
router = Router()

GROUP_TYPES = frozenset({"group", "supergroup"})
JOIN_STATUSES = frozenset({"member", "administrator", "creator"})
LEAVE_STATUSES = frozenset({"left", "kicked"})


def _member_joined(old_status: str, new_status: str) -> bool:
    return old_status in LEAVE_STATUSES and new_status in JOIN_STATUSES


async def _on_user_joined_group(
    bot: Bot,
    db: Database,
    config: Config,
    chat,
    user,
) -> None:
    if chat.type not in GROUP_TYPES:
        return
    await send_group_welcome(bot, db, chat, user, lang=config.default_language)


@router.my_chat_member()
async def on_bot_membership(
    event: ChatMemberUpdated, bot: Bot, db: Database, config: Config
) -> None:
    chat = event.chat
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    actor = event.from_user

    if chat.type == "private":
        if old_status in JOIN_STATUSES and new_status in LEAVE_STATUSES:
            await notify_private_block(bot, db, config, actor)
        return

    if chat.type not in GROUP_TYPES | {"channel"}:
        return

    joined = _member_joined(old_status, new_status)
    left = old_status in JOIN_STATUSES and new_status in LEAVE_STATUSES

    if joined and event.new_chat_member.user.id == bot.id:
        await db.upsert_chat(chat.id, chat.type, chat.title, chat.username)
        member_count = None
        try:
            member_count = await bot.get_chat_member_count(chat.id)
        except Exception:
            logger.exception("get_chat_member_count failed for %s", chat.id)
        role = bot_role_label(
            event.new_chat_member,
            await db.get_admin_language(config.admin_id, config.default_language),
        )
        await notify_group_added(
            bot,
            db,
            config,
            chat_title=chat.title,
            chat_id=chat.id,
            chat_username=chat.username,
            member_count=member_count,
            bot_role=role,
            actor=actor,
        )
    elif left and event.new_chat_member.user.id == bot.id:
        await db.deactivate_chat(chat.id)
        await notify_group_removed(
            bot,
            db,
            config,
            chat_title=chat.title,
            chat_id=chat.id,
            chat_username=chat.username,
            actor=actor,
        )


@router.chat_member()
async def on_chat_member_updated(
    event: ChatMemberUpdated, bot: Bot, db: Database, config: Config
) -> None:
    if event.chat.type not in GROUP_TYPES:
        return
    user = event.new_chat_member.user
    if user.id == bot.id:
        return
    if not _member_joined(event.old_chat_member.status, event.new_chat_member.status):
        return
    await _on_user_joined_group(bot, db, config, event.chat, user)


@router.message(F.new_chat_members)
async def on_new_chat_members(
    message: Message, bot: Bot, db: Database, config: Config
) -> None:
    if not message.chat or message.chat.type not in GROUP_TYPES:
        return
    if not message.new_chat_members:
        return
    for user in message.new_chat_members:
        if user.is_bot:
            continue
        await _on_user_joined_group(bot, db, config, message.chat, user)

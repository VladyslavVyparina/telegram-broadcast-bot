from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import Chat, User

from bot.database.db import Database

logger = logging.getLogger(__name__)


async def bot_startgroup_link(bot: Bot, db: Database) -> str | None:
    me = await bot.get_me()
    if not me.username:
        return None
    param = await db.get_cfg("bot_startgroup_param", "start")
    return f"https://t.me/{me.username}?startgroup={param}"


async def send_group_welcome(
    bot: Bot,
    db: Database,
    chat: Chat,
    user: User,
    *,
    lang: str,
) -> None:
    if user.is_bot:
        return
    if not await db.get_cfg_bool("group_welcome_on_join"):
        return

    link = await bot_startgroup_link(bot, db)
    if not link:
        return

    text = link
    try:
        await bot.send_message(chat.id, text, disable_web_page_preview=False)
    except Exception:
        logger.exception("Failed to send group welcome in chat %s", chat.id)

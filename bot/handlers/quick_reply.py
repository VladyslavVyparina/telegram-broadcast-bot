from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.types import Message

from bot.config import Config
from bot.database.db import Database
from bot.filters.admin import AdminFilter
from bot.locales import t
from bot.utils.sender import bot_send_content

router = Router()
admin = AdminFilter()


@router.message(admin, F.text.regexp(r"^/r(\d{1,2})$"))
async def admin_quick_reply(message: Message, db: Database, config: Config) -> None:
    lang = await db.get_admin_language(config.admin_id)
    if not message.reply_to_message:
        await message.answer(t(lang, "qr_help"))
        return

    match = re.match(r"^/r(\d{1,2})$", message.text.strip())
    slot = int(match.group(1))
    user_id = await db.get_user_by_forward(message.reply_to_message.message_id)
    if not user_id:
        await message.answer(t(lang, "qr_no_user"))
        return

    qr = await db.get_quick_reply(slot)
    if not qr:
        await message.answer(t(lang, "no_content"))
        return

    try:
        if qr.get("media_type") == "photo" and qr.get("file_id"):
            await bot_send_content(
                message.bot,
                db,
                user_id,
                {"content_type": "photo", "file_id": qr["file_id"], "caption": qr.get("caption")},
            )
        elif qr.get("media_type") == "video" and qr.get("file_id"):
            await bot_send_content(
                message.bot,
                db,
                user_id,
                {"content_type": "video", "file_id": qr["file_id"], "caption": qr.get("caption")},
            )
        elif qr.get("reply_text"):
            await bot_send_content(
                message.bot,
                db,
                user_id,
                {"content_type": "text", "text": qr["reply_text"]},
            )
        await message.answer(t(lang, "qr_sent"))
    except Exception:
        await message.answer(t(lang, "stat_failed"))

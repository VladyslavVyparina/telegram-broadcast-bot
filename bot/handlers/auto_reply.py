from __future__ import annotations

from aiogram import Router
from aiogram.types import Message

from bot.database.db import Database

router = Router()


@router.message()
async def handle_auto_reply(message: Message, db: Database) -> None:
    if not message.from_user or not message.text or message.text.startswith("/"):
        return
    await db.touch_user_activity(message.from_user.id)
    reply = await db.find_auto_reply(message.text)
    if reply:
        from bot.utils.sender import bot_send_content

        await bot_send_content(
            message.bot,
            db,
            message.chat.id,
            {"content_type": "text", "text": reply},
        )

from __future__ import annotations

from aiogram import Router
from aiogram.types import Message

from bot.config import Config
from bot.database.db import Database

router = Router()


@router.message()
async def forward_user_message(message: Message, db: Database, config: Config) -> None:
    user = message.from_user
    if not user or await db.is_admin(user.id, config.admin_id):
        return
    if message.text and message.text.startswith("/"):
        return
    if message.chat.type != "private":
        return

    if not await db.get_cfg_bool("bot_enabled"):
        return

    await db.touch_user_activity(user.id)
    await db.increment_messages()

    header = (
        f"👤 {user.first_name or '—'}"
        f" (@{user.username or '—'}) | <code>{user.id}</code>"
    )
    try:
        fwd = await message.forward(config.admin_id)
        if fwd:
            await db.save_user_forward(fwd.message_id, user.id)
        await message.bot.send_message(config.admin_id, header)
    except Exception:
        pass

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from aiogram import Bot
from aiogram.types import (
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot_public.database.db import Database


def _has_links(text: str | None) -> bool:
    if not text:
        return False
    return bool(re.search(r"https?://|t\.me/|@\w+", text, re.I))


async def should_protect(db: Database, content: dict[str, Any]) -> bool:
    if not await db.get_cfg_bool("content_protection"):
        return False
    ctype = content.get("content_type", "text")
    if ctype in ("photo", "video", "document", "audio", "voice", "sticker"):
        if await db.get_cfg_bool("content_exclude_media"):
            return False
    if ctype == "text":
        if await db.get_cfg_bool("content_exclude_text"):
            return False
        text = content.get("text") or ""
        if _has_links(text) and await db.get_cfg_bool("content_exclude_links"):
            return False
    else:
        caption = content.get("caption") or content.get("text") or ""
        if _has_links(caption) and await db.get_cfg_bool("content_exclude_links"):
            return False
    return True


async def _chat_type_for_delete(db: Database, chat_id: int) -> str | None:
    if chat_id > 0:
        return "private"
    chat = await db.get_chat(chat_id)
    if not chat:
        return "groups"
    ctype = chat.get("chat_type", "group")
    if ctype == "channel":
        return "channels"
    return "groups"


async def maybe_schedule_delete(
    db: Database,
    chat_id: int,
    message_id: int,
    *,
    source: str = "bot",
    has_buttons: bool = False,
    is_payment: bool = False,
    is_start: bool = False,
    is_admin: bool = False,
) -> None:
    if not await db.get_cfg_bool("auto_delete_enabled"):
        return
    if is_start and await db.get_cfg_bool("auto_delete_ex_start"):
        return
    if has_buttons and await db.get_cfg_bool("auto_delete_ex_buttons"):
        return
    if is_payment and await db.get_cfg_bool("auto_delete_ex_payment"):
        return
    if is_admin and await db.get_cfg_bool("auto_delete_ex_admin"):
        return

    scope = await _chat_type_for_delete(db, chat_id)
    scope_key = {
        "private": "auto_delete_private",
        "groups": "auto_delete_groups",
        "channels": "auto_delete_channels",
    }.get(scope or "groups", "auto_delete_groups")
    if not await db.get_cfg_bool(scope_key):
        return

    minutes = int(await db.get_cfg("auto_delete_minutes", "5"))
    delete_at = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
    await db.schedule_deletion(chat_id, message_id, delete_at, source=source)


async def bot_send_content(
    bot: Bot,
    db: Database,
    chat_id: int,
    content: dict[str, Any],
    *,
    method: str = "direct",
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | None = None,
    source: str = "bot",
    is_start: bool = False,
    is_payment: bool = False,
    is_admin: bool = False,
) -> Message | None:
    protect = await should_protect(db, content)
    kw: dict[str, Any] = {}
    if protect:
        kw["protect_content"] = True
    if reply_markup is not None:
        kw["reply_markup"] = reply_markup

    try:
        if method == "forward":
            msg = await bot.forward_message(
                chat_id=chat_id,
                from_chat_id=content["from_chat_id"],
                message_id=content["message_id"],
            )
        else:
            ctype = content.get("content_type", "text")
            if ctype == "text":
                msg = await bot.send_message(chat_id=chat_id, text=content["text"], **kw)
            elif ctype == "photo":
                msg = await bot.send_photo(
                    chat_id=chat_id,
                    photo=content["file_id"],
                    caption=content.get("caption"),
                    **kw,
                )
            elif ctype == "video":
                msg = await bot.send_video(
                    chat_id=chat_id,
                    video=content["file_id"],
                    caption=content.get("caption"),
                    **kw,
                )
            elif ctype == "document":
                msg = await bot.send_document(
                    chat_id=chat_id,
                    document=content["file_id"],
                    caption=content.get("caption"),
                    **kw,
                )
            elif ctype == "audio":
                msg = await bot.send_audio(
                    chat_id=chat_id,
                    audio=content["file_id"],
                    caption=content.get("caption"),
                    **kw,
                )
            elif ctype == "voice":
                msg = await bot.send_voice(
                    chat_id=chat_id,
                    voice=content["file_id"],
                    caption=content.get("caption"),
                    **kw,
                )
            elif ctype == "sticker":
                msg = await bot.send_sticker(chat_id=chat_id, sticker=content["file_id"], **kw)
            else:
                return None

        has_buttons = reply_markup is not None and isinstance(reply_markup, InlineKeyboardMarkup)
        await maybe_schedule_delete(
            db,
            chat_id,
            msg.message_id,
            source=source,
            has_buttons=has_buttons,
            is_payment=is_payment,
            is_start=is_start,
            is_admin=is_admin,
        )
        return msg
    except Exception:
        return None

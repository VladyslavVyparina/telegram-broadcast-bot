from __future__ import annotations

import json
import uuid
from typing import Any

from aiogram.types import Message


def new_broadcast_id() -> str:
    return f"bc_{uuid.uuid4().hex[:8]}"


def serialize_reply_markup(message: Message) -> dict[str, Any] | None:
    if not message.reply_markup:
        return None
    try:
        return message.reply_markup.model_dump()
    except Exception:
        return None


def deserialize_reply_markup(data: dict[str, Any] | None):
    if not data:
        return None
    from aiogram.types import InlineKeyboardMarkup

    try:
        return InlineKeyboardMarkup.model_validate(data)
    except Exception:
        return None


def serialize_message(message: Message, method: str = "direct") -> dict[str, Any]:
    data: dict[str, Any] = {
        "method": method,
        "content_type": "text",
        "text": None,
        "caption": None,
        "parse_mode": None,
        "file_id": None,
        "from_chat_id": None,
        "message_id": None,
    }

    if method == "forward":
        data["from_chat_id"] = message.chat.id
        data["message_id"] = message.message_id
        if message.text:
            data["content_type"] = "text"
        elif message.photo:
            data["content_type"] = "photo"
        elif message.video:
            data["content_type"] = "video"
        elif message.document:
            data["content_type"] = "document"
        elif message.sticker:
            data["content_type"] = "sticker"
        return data

    if message.text:
        data["content_type"] = "text"
        data["text"] = message.text
        data["parse_mode"] = message.html_text and "HTML" or None
    elif message.photo:
        data["content_type"] = "photo"
        data["file_id"] = message.photo[-1].file_id
        data["caption"] = message.caption
        data["parse_mode"] = "HTML" if message.caption_entities else None
    elif message.video:
        data["content_type"] = "video"
        data["file_id"] = message.video.file_id
        data["caption"] = message.caption
    elif message.document:
        data["content_type"] = "document"
        data["file_id"] = message.document.file_id
        data["caption"] = message.caption
    elif message.audio:
        data["content_type"] = "audio"
        data["file_id"] = message.audio.file_id
        data["caption"] = message.caption
    elif message.voice:
        data["content_type"] = "voice"
        data["file_id"] = message.voice.file_id
        data["caption"] = message.caption
    elif message.sticker:
        data["content_type"] = "sticker"
        data["file_id"] = message.sticker.file_id
    else:
        data["content_type"] = "unsupported"

    markup = serialize_reply_markup(message)
    if markup:
        data["reply_markup"] = markup

    return data


def interval_label_key(seconds: int) -> str:
    from bot.locales.ar import INTERVAL_LABELS

    if seconds < 300:
        seconds = 300
    return INTERVAL_LABELS.get(seconds, "interval_5m")


def content_preview(content: dict[str, Any], max_len: int = 28) -> str:
    ctype = content.get("content_type", "text")
    if ctype == "text":
        text = content.get("text") or ""
    else:
        text = content.get("caption") or ctype
    text = text.replace("\n", " ").strip()
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text or ctype


def format_display_time(iso_value: str | None, tz_name: str = "Asia/Riyadh") -> str:
    """UTC ISO timestamp → local readable time, e.g. 25.06.2026 18:54"""
    if not iso_value:
        return "—"
    try:
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo

        dt = datetime.fromisoformat(iso_value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(ZoneInfo(tz_name))
        return local.strftime("%d.%m.%Y %H:%M")
    except Exception:
        raw = iso_value.replace("T", " ")
        return raw[:16] if len(raw) > 16 else raw

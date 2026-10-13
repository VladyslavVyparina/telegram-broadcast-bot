"""Cross-clone operations: stats, broadcast, global auto-replies."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

logger = logging.getLogger(__name__)

SEND_DELAY = 0.04


@dataclass
class NetworkStats:
    total_bots: int = 0
    active_bots: int = 0
    running_bots: int = 0
    disabled_bots: int = 0
    expired_bots: int = 0
    total_users: int = 0
    total_groups: int = 0
    autopost_enabled: int = 0
    auto_replies_total: int = 0


@dataclass
class BroadcastReport:
    bots_used: int = 0
    total_targets: int = 0
    sent: int = 0
    blocked: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def _is_real_token(token: str | None) -> bool:
    return bool(token and not str(token).startswith("virtual:") and ":" in str(token))


async def _clone_query(db_path: str, sql: str, params: tuple = ()) -> list[Any]:
    path = Path(db_path)
    if not path.is_file():
        return []
    async with aiosqlite.connect(path) as conn:
        cur = await conn.execute(sql, params)
        return [row[0] for row in await cur.fetchall()]


async def _clone_targets(db_path: str, audience: str) -> list[int]:
    if audience == "private":
        sql = "SELECT user_id FROM users WHERE is_blocked=0"
    elif audience == "groups":
        sql = (
            "SELECT chat_id FROM chats WHERE is_active=1 "
            "AND chat_type IN ('group','supergroup','channel')"
        )
    else:
        sql = """
            SELECT user_id FROM users WHERE is_blocked=0
            UNION
            SELECT chat_id FROM chats WHERE is_active=1
              AND chat_type IN ('group','supergroup','channel')
        """
    return await _clone_query(db_path, sql)


async def collect_network_stats(
    children: list[dict[str, Any]],
    *,
    running_count: int = 0,
) -> NetworkStats:
    stats = NetworkStats(running_bots=running_count)
    now = datetime.now(timezone.utc).isoformat()
    stats.total_bots = len(children)

    for child in children:
        exp = child.get("expires_at") or ""
        disabled = bool(child.get("is_disabled"))
        active = not exp or exp > now

        if disabled:
            stats.disabled_bots += 1
        elif active:
            stats.active_bots += 1
        else:
            stats.expired_bots += 1

        db_path = child.get("db_path")
        if not db_path or not Path(db_path).is_file():
            continue

        users = await _clone_query(
            db_path, "SELECT COUNT(*) FROM users WHERE is_blocked=0"
        )
        groups = await _clone_query(
            db_path,
            "SELECT COUNT(*) FROM chats WHERE is_active=1 "
            "AND chat_type IN ('group','supergroup','channel')",
        )
        autopost = await _clone_query(
            db_path, "SELECT is_enabled FROM auto_post WHERE id=1"
        )
        replies = await _clone_query(db_path, "SELECT COUNT(*) FROM auto_replies")

        stats.total_users += int(users[0]) if users else 0
        stats.total_groups += int(groups[0]) if groups else 0
        if autopost and int(autopost[0]):
            stats.autopost_enabled += 1
        stats.auto_replies_total += int(replies[0]) if replies else 0

    return stats


async def _send_content(bot: Bot, chat_id: int, content: dict[str, Any]) -> str:
    try:
        if content.get("method") == "forward":
            await bot.forward_message(
                chat_id=chat_id,
                from_chat_id=content["from_chat_id"],
                message_id=content["message_id"],
            )
            return "sent"
        ctype = content.get("content_type", "text")
        if ctype == "text" and content.get("text"):
            await bot.send_message(
                chat_id, content["text"], parse_mode="HTML",
            )
            return "sent"
        if ctype == "photo" and content.get("file_id"):
            await bot.send_photo(
                chat_id,
                content["file_id"],
                caption=content.get("caption"),
                parse_mode="HTML",
            )
            return "sent"
        if ctype == "video" and content.get("file_id"):
            await bot.send_video(
                chat_id,
                content["file_id"],
                caption=content.get("caption"),
                parse_mode="HTML",
            )
            return "sent"
        if ctype == "document" and content.get("file_id"):
            await bot.send_document(
                chat_id,
                content["file_id"],
                caption=content.get("caption"),
                parse_mode="HTML",
            )
            return "sent"
        return "failed"
    except TelegramForbiddenError:
        return "blocked"
    except TelegramRetryAfter as exc:
        await asyncio.sleep(exc.retry_after)
        return await _send_content(bot, chat_id, content)
    except Exception:
        return "failed"


async def broadcast_to_clones(
    children: list[dict[str, Any]],
    *,
    audience: str,
    content: dict[str, Any],
    only_bot_ids: set[int] | None = None,
) -> BroadcastReport:
    report = BroadcastReport()

    for child in children:
        bot_id = int(child["id"])
        if only_bot_ids is not None and bot_id not in only_bot_ids:
            continue
        if child.get("is_disabled"):
            continue
        token = child.get("bot_token")
        if not _is_real_token(token):
            continue
        db_path = child.get("db_path")
        if not db_path:
            continue

        targets = await _clone_targets(db_path, audience)
        if not targets:
            continue

        report.bots_used += 1
        report.total_targets += len(targets)
        username = child.get("bot_username") or str(child.get("id"))

        bot = Bot(token=str(token))
        try:
            for chat_id in targets:
                result = await _send_content(bot, chat_id, content)
                if result == "sent":
                    report.sent += 1
                elif result == "blocked":
                    report.blocked += 1
                else:
                    report.failed += 1
                await asyncio.sleep(SEND_DELAY)
        except Exception as exc:
            report.errors.append(f"@{username}: {exc}")
            logger.exception("Broadcast failed for clone %s", child.get("id"))
        finally:
            await bot.session.close()

    return report


async def sync_auto_reply_to_clone(
    db_path: str,
    trigger: str,
    reply_text: str,
) -> bool:
    path = Path(db_path)
    if not path.is_file():
        return False
    now = datetime.now(timezone.utc).isoformat()
    trigger = trigger.strip().lower()
    async with aiosqlite.connect(path) as conn:
        await conn.execute(
            "DELETE FROM auto_replies WHERE trigger=?", (trigger,)
        )
        await conn.execute(
            "INSERT INTO auto_replies (trigger, reply_text, created_at) VALUES (?,?,?)",
            (trigger, reply_text.strip(), now),
        )
        await conn.commit()
    return True


async def delete_auto_reply_from_clone(db_path: str, trigger: str) -> bool:
    path = Path(db_path)
    if not path.is_file():
        return False
    async with aiosqlite.connect(path) as conn:
        await conn.execute(
            "DELETE FROM auto_replies WHERE trigger=?",
            (trigger.strip().lower(),),
        )
        await conn.commit()
    return True


async def sync_global_replies_to_clones(
    children: list[dict[str, Any]],
    items: list[dict[str, str]],
) -> tuple[int, int]:
    """Push platform global auto-replies to all clone DBs. Returns (bots_ok, total_rules)."""
    ok_bots = 0
    for child in children:
        if not _is_real_token(child.get("bot_token")):
            continue
        db_path = child.get("db_path")
        if not db_path:
            continue
        path = Path(db_path)
        if not path.is_file():
            continue
        async with aiosqlite.connect(path) as conn:
            await conn.execute("DELETE FROM auto_replies")
            now = datetime.now(timezone.utc).isoformat()
            for item in items:
                await conn.execute(
                    "INSERT INTO auto_replies (trigger, reply_text, created_at) VALUES (?,?,?)",
                    (item["trigger"].strip().lower(), item["reply_text"].strip(), now),
                )
            await conn.commit()
        ok_bots += 1
    return ok_bots, len(items)


async def clear_auto_replies_on_clones(children: list[dict[str, Any]]) -> int:
    cleared = 0
    for child in children:
        db_path = child.get("db_path")
        if not db_path or not Path(db_path).is_file():
            continue
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("DELETE FROM auto_replies")
            await conn.commit()
        cleared += 1
    return cleared

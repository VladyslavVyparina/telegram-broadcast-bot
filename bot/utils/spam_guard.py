"""Rate limits and safe defaults to reduce Telegram spam bans."""

from __future__ import annotations

from bot.database.db import Database

BROADCAST_DELAY_MS_DEFAULT = 150
AUTOPOST_MIN_INTERVAL_DEFAULT = 300


async def broadcast_delay_sec(db: Database) -> float:
    raw = await db.get_cfg("broadcast_delay_ms", str(BROADCAST_DELAY_MS_DEFAULT))
    try:
        ms = max(50, int(raw))
    except ValueError:
        ms = BROADCAST_DELAY_MS_DEFAULT
    return ms / 1000.0


async def min_autopost_interval(db: Database) -> int:
    if not await db.get_cfg_bool("spam_safe_mode"):
        return 60
    raw = await db.get_cfg(
        "autopost_min_interval_seconds", str(AUTOPOST_MIN_INTERVAL_DEFAULT),
    )
    try:
        return max(60, int(raw))
    except ValueError:
        return AUTOPOST_MIN_INTERVAL_DEFAULT


async def clamp_autopost_interval(db: Database, interval: int) -> int:
    return max(int(interval), await min_autopost_interval(db))

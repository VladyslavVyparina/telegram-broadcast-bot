"""Entry point for a platform child bot (separate OS process, own routers)."""
from __future__ import annotations

import asyncio
import logging
import os
import sys

from bot.app import run_bot_instance
from bot.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _load_clone_config() -> Config:
    token = os.environ.get("CLONE_BOT_TOKEN", "").strip()
    admin_raw = os.environ.get("CLONE_ADMIN_ID", "").strip()
    db_path = os.environ.get("CLONE_DATABASE_PATH", "").strip()
    if not token or not admin_raw or not db_path:
        raise ValueError(
            "CLONE_BOT_TOKEN, CLONE_ADMIN_ID, CLONE_DATABASE_PATH are required"
        )
    return Config.from_values(
        bot_token=token,
        admin_id=int(admin_raw),
        database_path=db_path,
        default_language=os.environ.get("CLONE_DEFAULT_LANGUAGE", "ar").strip() or "ar",
        timezone=os.environ.get("BOT_TIMEZONE", "Asia/Riyadh").strip() or "Asia/Riyadh",
    )


async def main() -> None:
    await run_bot_instance(_load_clone_config())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)

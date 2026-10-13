from __future__ import annotations

import asyncio
import logging

from bot.app import run_bot_instance
from bot.config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main() -> None:
    await run_bot_instance(load_config())


if __name__ == "__main__":
    asyncio.run(main())

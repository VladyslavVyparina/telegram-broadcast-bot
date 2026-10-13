from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from bot_public.database.db import PlatformDB

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ChildManager:
    """Runs each paid clone as a separate OS process (own token, routers, DB)."""

    def __init__(self, platform_db: PlatformDB) -> None:
        self.platform_db = platform_db
        self._procs: dict[int, subprocess.Popen[bytes]] = {}

    def _is_real_token(self, token: str | None) -> bool:
        return bool(token and not token.startswith("virtual:") and ":" in token)

    def _clone_env(self, child: dict[str, Any]) -> dict[str, str]:
        env = os.environ.copy()
        env["CLONE_BOT_TOKEN"] = str(child["bot_token"])
        env["CLONE_ADMIN_ID"] = str(child["owner_id"])
        env["CLONE_DATABASE_PATH"] = str(child["db_path"])
        env["CLONE_DEFAULT_LANGUAGE"] = "ar"
        env["CLONE_PLATFORM_BOT"] = os.getenv(
            "PLATFORM_BOT_USERNAME", "Ni_iF7Fibot"
        ).strip().lstrip("@")
        return env

    async def start_child(self, child: dict[str, Any]) -> bool:
        bot_id = int(child["id"])
        if child.get("is_disabled"):
            return False
        if not self._is_real_token(child.get("bot_token")):
            return False
        if not await self.platform_db.is_child_active(child.get("expires_at")):
            return False

        existing = self._procs.get(bot_id)
        if existing is not None and existing.poll() is None:
            return True
        if existing is not None:
            del self._procs[bot_id]

        log_dir = PROJECT_ROOT / "data" / "clones" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"clone_{bot_id}.log"

        try:
            log_file = open(log_path, "ab")  # noqa: SIM115
            proc = subprocess.Popen(
                [sys.executable, "-m", "bot.clone_main"],
                cwd=str(PROJECT_ROOT),
                env=self._clone_env(child),
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
        except OSError as exc:
            logger.error("Clone %s failed to start process: %s", bot_id, exc)
            return False

        self._procs[bot_id] = proc
        await asyncio.sleep(0.5)
        if proc.poll() is not None:
            logger.error(
                "Clone %s exited immediately (code %s). See %s",
                bot_id,
                proc.returncode,
                log_path,
            )
            del self._procs[bot_id]
            await self.platform_db.set_child_running(bot_id, False)
            return False
        await self.platform_db.set_child_running(bot_id, True)
        logger.info(
            "Clone %s started (pid %s) @%s (owner %s)",
            bot_id,
            proc.pid,
            child.get("bot_username"),
            child.get("owner_id"),
        )
        return True

    def is_child_running(self, bot_id: int) -> bool:
        proc = self._procs.get(bot_id)
        return proc is not None and proc.poll() is None

    async def stop_child(self, bot_id: int) -> None:
        proc = self._procs.pop(bot_id, None)
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        await self.platform_db.set_child_running(bot_id, False)
        logger.info("Clone %s stopped", bot_id)

    async def restart_child(self, child: dict[str, Any]) -> None:
        await self.stop_child(int(child["id"]))
        if await self.platform_db.is_child_active(child.get("expires_at")):
            await self.start_child(child)

    async def start_all_active(self) -> None:
        for child in await self.platform_db.get_active_child_bots():
            if self._is_real_token(child.get("bot_token")):
                await self.start_child(child)

    async def stop_expired(self) -> None:
        for child in await self.platform_db.get_expired_running_bots():
            await self.stop_child(int(child["id"]))

    async def ensure_running(self) -> None:
        for child in await self.platform_db.get_active_child_bots():
            if child.get("is_disabled"):
                continue
            if not self._is_real_token(child.get("bot_token")):
                continue
            bot_id = int(child["id"])
            proc = self._procs.get(bot_id)
            if proc is not None and proc.poll() is not None:
                logger.warning(
                    "Clone %s exited (code %s), restarting @%s",
                    bot_id,
                    proc.returncode,
                    child.get("bot_username"),
                )
                del self._procs[bot_id]
                await self.platform_db.set_child_running(bot_id, False)
            if not self.is_child_running(bot_id):
                await self.start_child(child)

    def running_count(self) -> int:
        return sum(1 for p in self._procs.values() if p.poll() is None)

    async def shutdown(self) -> None:
        for bot_id in list(self._procs):
            await self.stop_child(bot_id)

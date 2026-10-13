import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.database.db import Database
from bot.locales import t
from bot.locales.ar import INTERVAL_LABELS, TARGET_LABELS
from bot.services.broadcaster import broadcast_manager
from bot.utils.helpers import new_broadcast_id
from bot.utils.spam_guard import clamp_autopost_interval

logger = logging.getLogger(__name__)


class AutoPostScheduler:
    def __init__(self, bot: Bot, db: Database, admin_id: int) -> None:
        self.bot = bot
        self.db = db
        self.admin_id = admin_id
        self.scheduler = AsyncIOScheduler()
        self._running = False
        self._session_stats = {
            "total": 0, "sent": 0, "blocked": 0, "failed": 0, "messages": 0, "cycles": 0,
        }

    def reset_session_stats(self) -> None:
        self._session_stats = {
            "total": 0, "sent": 0, "blocked": 0, "failed": 0, "messages": 0, "cycles": 0,
        }

    def session_stats(self) -> dict[str, int]:
        return dict(self._session_stats)

    def start(self) -> None:
        self.scheduler.add_job(
            self._tick,
            "interval",
            seconds=30,
            id="autopost_tick",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("Auto-post scheduler started")

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def _tick(self) -> None:
        if self._running:
            return

        settings = await self.db.get_auto_post()
        if not settings or not settings.get("is_enabled"):
            return

        items = await self.db.list_auto_post_items()
        if not items:
            return

        now = datetime.now(timezone.utc)
        next_post_raw = settings.get("next_post_at")
        if next_post_raw:
            next_post = datetime.fromisoformat(next_post_raw.replace("Z", "+00:00"))
            if next_post.tzinfo is None:
                next_post = next_post.replace(tzinfo=timezone.utc)
            if now < next_post:
                return

        self._running = True
        try:
            await self._execute_cycle(settings, items)
        finally:
            self._running = False

    async def _execute_cycle(self, settings: dict, items: list[dict]) -> None:
        interval = await clamp_autopost_interval(
            self.db, int(settings.get("interval_seconds", 300)),
        )
        target_type = settings.get("target_type", "groups")
        targets = await self.db.get_targets(target_type)
        if not targets:
            return

        lang = await self.db.get_admin_language(self.admin_id)
        totals = {"total": 0, "sent": 0, "blocked": 0, "failed": 0}
        posted = 0

        for item in items:
            content = item.get("content")
            if not content:
                continue

            broadcast_id = new_broadcast_id()
            await self.db.create_broadcast(
                broadcast_id=broadcast_id,
                admin_id=self.admin_id,
                target_type=target_type,
                send_method="direct",
                content=content,
                total_targets=len(targets),
            )
            result = await broadcast_manager.run(
                self.bot,
                self.db,
                broadcast_id,
                targets,
                content,
                content.get("method", "direct"),
            )
            totals["total"] += result.total
            totals["sent"] += result.sent
            totals["blocked"] += result.blocked
            totals["failed"] += result.failed
            posted += 1
            if len(items) > 1:
                await asyncio.sleep(1.0)

        self._session_stats["total"] += totals["total"]
        self._session_stats["sent"] += totals["sent"]
        self._session_stats["blocked"] += totals["blocked"]
        self._session_stats["failed"] += totals["failed"]
        self._session_stats["messages"] += posted
        self._session_stats["cycles"] += 1

        now = datetime.now(timezone.utc)
        next_post_dt = datetime.fromtimestamp(
            now.timestamp() + interval, tz=timezone.utc
        ).isoformat()
        await self.db.save_auto_post(
            last_post_at=now.isoformat(),
            next_post_at=next_post_dt,
        )

    async def send_session_report(self, lang: str, *, stopped: bool = True) -> None:
        s = self._session_stats
        key = "autopost_session_stopped" if stopped else "autopost_session_done"
        try:
            await self.bot.send_message(
                self.admin_id,
                t(
                    lang,
                    key,
                    total=s["total"],
                    sent=s["sent"],
                    blocked=s["blocked"],
                    failed=s["failed"],
                    messages=s["messages"],
                    cycles=s["cycles"],
                ),
            )
        except Exception:
            logger.exception("Failed to send auto-post session report")

    async def reschedule(self) -> None:
        settings = await self.db.get_auto_post()
        if not settings or not settings.get("is_enabled"):
            return
        now = datetime.now(timezone.utc)
        interval = await clamp_autopost_interval(
            self.db, int(settings.get("interval_seconds", 300)),
        )
        next_post_dt = datetime.fromtimestamp(
            now.timestamp() + interval, tz=timezone.utc
        ).isoformat()
        await self.db.save_auto_post(next_post_at=next_post_dt)

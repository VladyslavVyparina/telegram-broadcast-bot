from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import Message

from bot.database.db import Database
from bot.utils.helpers import deserialize_reply_markup
from bot.utils.spam_guard import broadcast_delay_sec
from bot.utils.sender import bot_send_content

logger = logging.getLogger(__name__)


@dataclass
class BroadcastResult:
    total: int = 0
    sent: int = 0
    blocked: int = 0
    failed: int = 0
    duration: float = 0.0
    stopped: bool = False


class BroadcastManager:
    def __init__(self) -> None:
        self._stop_flags: dict[str, bool] = {}

    def request_stop(self, broadcast_id: str) -> None:
        self._stop_flags[broadcast_id] = True

    def is_stopped(self, broadcast_id: str) -> bool:
        return self._stop_flags.get(broadcast_id, False)

    def clear(self, broadcast_id: str) -> None:
        self._stop_flags.pop(broadcast_id, None)

    async def send_to_chat(
        self,
        bot: Bot,
        db: Database,
        chat_id: int,
        content: dict[str, Any],
        method: str,
    ) -> str:
        try:
            markup = deserialize_reply_markup(content.get("reply_markup"))
            msg = await bot_send_content(
                bot,
                db,
                chat_id,
                content,
                method=method,
                reply_markup=markup,
                source="broadcast",
            )
            if msg:
                return "sent"
            if method == "forward":
                await bot.forward_message(
                    chat_id=chat_id,
                    from_chat_id=content["from_chat_id"],
                    message_id=content["message_id"],
                )
                return "sent"
            return "failed"
        except TelegramForbiddenError:
            return "blocked"
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            return await self.send_to_chat(bot, db, chat_id, content, method)
        except Exception:
            return "failed"

    async def run(
        self,
        bot: Bot,
        db: Database,
        broadcast_id: str,
        targets: list[int],
        content: dict[str, Any],
        method: str,
        progress_message: Message | None = None,
        lang: str = "ar",
    ) -> BroadcastResult:
        from bot.locales import t
        from bot.keyboards.inline import stop_broadcast_kb

        result = BroadcastResult(total=len(targets))
        start = time.monotonic()

        delay = await broadcast_delay_sec(db)

        for chat_id in targets:
            if self.is_stopped(broadcast_id):
                result.stopped = True
                break

            status = await self.send_to_chat(bot, db, chat_id, content, method)
            if status == "sent":
                result.sent += 1
            elif status == "blocked":
                result.blocked += 1
                if chat_id > 0:
                    await db.mark_user_blocked(chat_id)
            else:
                result.failed += 1

            if result.sent % 10 == 0:
                await db.update_broadcast_stats(
                    broadcast_id, result.sent, result.blocked, result.failed
                )

            await asyncio.sleep(delay)

        result.duration = max(time.monotonic() - start, 0.001)
        status = "stopped" if result.stopped else "completed"
        await db.update_broadcast_stats(
            broadcast_id,
            result.sent,
            result.blocked,
            result.failed,
            status=status,
        )
        self.clear(broadcast_id)
        return result


broadcast_manager = BroadcastManager()


class BackgroundSchedulers:
    def __init__(self, bot: Bot, db: Database, admin_id: int) -> None:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        self.bot = bot
        self.db = db
        self.admin_id = admin_id
        self.scheduler = AsyncIOScheduler()
        self._delete_running = False
        self._inactive_running = False
        self._subscription_running = False

    def start(self) -> None:
        self.scheduler.add_job(
            self._delete_tick,
            "interval",
            seconds=30,
            id="autodelete_tick",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._inactive_tick,
            "interval",
            seconds=3600,
            id="inactive_tick",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._subscription_reminder_tick,
            "interval",
            seconds=3600,
            id="subscription_reminder_tick",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._cleanup_tick,
            "interval",
            seconds=3600,
            id="verify_cleanup_tick",
            replace_existing=True,
        )
        if not self.scheduler.running:
            self.scheduler.start()
        logger.info("Background schedulers started")

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def _delete_tick(self) -> None:
        if self._delete_running:
            return
        self._delete_running = True
        try:
            due = await self.db.get_due_deletions()
            for item in due:
                try:
                    await self.bot.delete_message(item["chat_id"], item["message_id"])
                    await self.db.increment_delete_stats()
                except Exception:
                    pass
                await self.db.remove_deletion(item["id"])
        finally:
            self._delete_running = False

    async def _inactive_tick(self) -> None:
        if self._inactive_running:
            return
        if not await self.db.get_cfg_bool("inactive_enabled"):
            return
        self._inactive_running = True
        try:
            now = datetime.now(timezone.utc)
            hour = now.hour
            start_h = int(await self.db.get_cfg("inactive_hours_start", "0"))
            end_h = int(await self.db.get_cfg("inactive_hours_end", "24"))
            if not (start_h <= hour < end_h):
                return

            reminders = await self.db.get_inactive_reminders()
            if not reminders:
                return

            users = await self.db.get_users_for_inactive_check()
            for user in users:
                uid = user["user_id"]
                if uid == self.admin_id:
                    continue
                if await self.db.is_admin(uid, self.admin_id):
                    continue
                last = user.get("last_active_at") or user.get("created_at")
                if not last:
                    continue
                last_dt = datetime.fromisoformat(last)
                inactive_days = (now - last_dt).days
                state = await self.db.get_inactive_state(uid) or {}
                step = int(state.get("reminder_step", 0))
                if step >= len(reminders):
                    continue
                reminder = reminders[step]
                if inactive_days < int(reminder["days"]):
                    continue
                if await self.db.get_cfg_bool("inactive_exclude_subs"):
                    if await self.db.has_paid_access(uid):
                        continue
                try:
                    await self.bot.send_message(uid, reminder["message_text"])
                    await self.db.set_inactive_reminder_sent(uid, step + 1)
                    await asyncio.sleep(await broadcast_delay_sec(self.db))
                except Exception:
                    blocked = int(await self.db.get_cfg("inactive_blocked", "0"))
                    await self.db.set_cfg("inactive_blocked", str(blocked + 1))
        finally:
            self._inactive_running = False

    async def _subscription_reminder_tick(self) -> None:
        if self._subscription_running:
            return
        if not await self.db.get_cfg_bool("finance_access_enabled"):
            return
        self._subscription_running = True
        try:
            from bot.locales import t
            from bot.services.paid_access import get_subscription_period, paywall_kb
            from bot.utils.helpers import format_display_time

            users = await self.db.get_users_for_expiry_reminder(hours=24)
            if not users:
                return
            price, _, months_label = await get_subscription_period(self.db)
            for row in users:
                uid = int(row["user_id"])
                if await self.db.is_admin(uid, self.admin_id):
                    continue
                days_left = await self.db.get_access_days_remaining(uid) or 0
                date_str = format_display_time(row.get("expires_at"))
                text = t(
                    "ar",
                    "paid_access_expiry_reminder",
                    days=days_left,
                    date=date_str,
                    price=price,
                    months_label=months_label,
                )
                try:
                    await self.bot.send_message(
                        uid,
                        text,
                        reply_markup=paywall_kb("ar"),
                    )
                    await self.db.mark_expiry_reminder_sent(uid)
                    await asyncio.sleep(await broadcast_delay_sec(self.db))
                except Exception:
                    pass
        finally:
            self._subscription_running = False

    async def _cleanup_tick(self) -> None:
        if await self.db.get_cfg_bool("verification_auto_clean"):
            await self.db.clean_stale_verifications(24)

"""Platform bot database."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiosqlite

CLONES_DIR = Path("data/clones")


def _parse_utc(dt_str: str) -> datetime:
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

DEFAULTS: dict[str, str] = {
    "subscription_price": "100",
    "subscription_months": "1",
    "subscription_days": "30",
    "finance_today": "0",
    "finance_total": "0",
    "finance_day": "",
    "platform_paid_mode": "1",
    "crypto_price_usdt": "20 USDT",
    "crypto_price_ton": "10 TON",
    "crypto_wallet_trc20": "TW1LEPXWVBZZPgq5eSeNRgXxzdHoSkvcrP",
    "crypto_wallet_ton": "UQA17CosTHjt8VLBWT_YGOY1EE2Qs3rkOKNmYCoKg7z5JRqN",
    "platform_bot_username": "Ni_iF7Fibot",
    "crypto_admin_username": "sftsfdrtghbot",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS platform_users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    language TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS child_bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    bot_token TEXT NOT NULL UNIQUE,
    bot_username TEXT,
    bot_name TEXT,
    db_path TEXT NOT NULL,
    expires_at TEXT,
    is_running INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    child_bot_id INTEGER,
    amount_stars INTEGER NOT NULL,
    days INTEGER NOT NULL,
    payment_type TEXT NOT NULL,
    payload TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS platform_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expiry_reminders (
    child_bot_id INTEGER PRIMARY KEY,
    sent_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wallet_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL UNIQUE,
    wallet_order_id INTEGER,
    user_id INTEGER NOT NULL,
    payment_type TEXT NOT NULL,
    child_bot_id INTEGER,
    days INTEGER NOT NULL,
    currency TEXT NOT NULL,
    amount TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    provider TEXT NOT NULL DEFAULT 'wallet_pay',
    created_at TEXT NOT NULL,
    paid_at TEXT
);

CREATE TABLE IF NOT EXISTS wallet_webhook_events (
    event_id INTEGER PRIMARY KEY,
    processed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cryptobot_webhook_events (
    update_id INTEGER PRIMARY KEY,
    processed_at TEXT NOT NULL
);
"""


class PlatformDB:
    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        CLONES_DIR.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        for key, value in DEFAULTS.items():
            await self._conn.execute(
                "INSERT OR IGNORE INTO platform_config (key, value) VALUES (?, ?)",
                (key, value),
            )
        cur = await self._conn.execute(
            "SELECT value FROM platform_config WHERE key='crypto_price_usdt'"
        )
        if not await cur.fetchone():
            legacy = await self.get_cfg("crypto_price_text", "10 USDT")
            await self._conn.execute(
                "INSERT INTO platform_config (key, value) VALUES ('crypto_price_usdt', ?)",
                ("20 USDT" if legacy in ("10 USDT", "10$", "10") else legacy,),
            )
            await self._conn.execute(
                "INSERT INTO platform_config (key, value) VALUES ('crypto_price_ton', '10 TON')"
            )
        cur = await self._conn.execute(
            "SELECT value FROM platform_config WHERE key='crypto_price_text'"
        )
        row = await cur.fetchone()
        if row and row[0] in ("10$", "10", "10 crypto"):
            await self._conn.execute(
                "UPDATE platform_config SET value='10 USDT' WHERE key='crypto_price_text'"
            )
        cur = await self._conn.execute(
            "SELECT value FROM platform_config WHERE key='crypto_admin_username'"
        )
        row = await cur.fetchone()
        if row and row[0] in ("iTi_f", "ITi_f", "@iTi_f"):
            await self._conn.execute(
                "UPDATE platform_config SET value='sftsfdrtghbot' WHERE key='crypto_admin_username'"
            )
        cur = await self._conn.execute(
            "SELECT value FROM platform_config WHERE key='platform_bot_username'"
        )
        row = await cur.fetchone()
        if row and row[0] in ("automatic_publish_bot", "@automatic_publish_bot"):
            await self._conn.execute(
                "UPDATE platform_config SET value='Ni_iF7Fibot' WHERE key='platform_bot_username'"
            )
        cur = await self._conn.execute("PRAGMA table_info(wallet_orders)")
        cols = {r[1] for r in await cur.fetchall()}
        if "provider" not in cols:
            await self._conn.execute(
                "ALTER TABLE wallet_orders ADD COLUMN provider TEXT NOT NULL DEFAULT 'wallet_pay'"
            )
        cur = await self._conn.execute("PRAGMA table_info(child_bots)")
        child_cols = {r[1] for r in await cur.fetchall()}
        if "is_disabled" not in child_cols:
            await self._conn.execute(
                "ALTER TABLE child_bots ADD COLUMN is_disabled INTEGER DEFAULT 0"
            )
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database not connected")
        return self._conn

    async def get_cfg(self, key: str, default: str = "") -> str:
        cur = await self.conn.execute(
            "SELECT value FROM platform_config WHERE key=?", (key,)
        )
        row = await cur.fetchone()
        return row[0] if row else default

    async def set_cfg(self, key: str, value: str) -> None:
        await self.conn.execute(
            "INSERT INTO platform_config (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await self.conn.commit()

    async def upsert_user(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
        *,
        language: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            """
            INSERT INTO platform_users (user_id, username, first_name, language, created_at)
            VALUES (?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=COALESCE(excluded.username, username),
                first_name=COALESCE(excluded.first_name, first_name),
                language=COALESCE(excluded.language, language)
            """,
            (user_id, username, first_name, language, now),
        )
        await self.conn.commit()

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            "SELECT * FROM platform_users WHERE user_id=?", (user_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        uname = username.strip().lstrip("@").lower()
        if not uname:
            return None
        cur = await self.conn.execute(
            "SELECT * FROM platform_users WHERE LOWER(username)=?",
            (uname,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def set_user_language(self, user_id: int, language: str) -> None:
        await self.conn.execute(
            "UPDATE platform_users SET language=? WHERE user_id=?",
            (language, user_id),
        )
        await self.conn.commit()

    async def get_user_language(self, user_id: int, default: str = "ar") -> str:
        user = await self.get_user(user_id)
        if user and user.get("language") in ("ar", "en"):
            return user["language"]
        return default

    async def subscription_days(self) -> int:
        days = await self.get_cfg("subscription_days", "30")
        if days.isdigit():
            return int(days)
        months = await self.get_cfg("subscription_months", "1")
        return max(1, int(months) if months.isdigit() else 1) * 30

    async def subscription_price(self) -> int:
        return int(await self.get_cfg("subscription_price", "100"))

    async def is_paid_mode(self) -> bool:
        return await self.get_cfg("platform_paid_mode", "1") == "1"

    async def crypto_price_usdt(self) -> str:
        from bot_public.utils.crypto_prices import normalize_usdt_price

        raw = await self.get_cfg("crypto_price_usdt", "20 USDT")
        try:
            return normalize_usdt_price(raw)
        except Exception:
            return "20 USDT"

    async def crypto_price_ton(self) -> str:
        return await self.get_cfg("crypto_price_ton", "10 TON")

    async def crypto_price_summary(self) -> str:
        return await self.crypto_price_usdt()

    async def crypto_admin_username(self) -> str:
        val = (await self.get_cfg("crypto_admin_username", "sftsfdrtghbot")).strip().lstrip("@")
        return val or "sftsfdrtghbot"

    async def platform_bot_username(self) -> str:
        return (await self.get_cfg("platform_bot_username", "Ni_iF7Fibot")).lstrip("@")

    async def grant_manual_create(self, user_id: int, days: int, *, admin_id: int) -> None:
        await self.record_payment(
            user_id, 0, days, "manual_create", payload=f"admin:{admin_id}",
        )

    async def revoke_all_access(self, child_manager: Any = None) -> int:
        """Expire all child bots (switching to paid mode). Returns count."""
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            "SELECT id FROM child_bots WHERE expires_at > ?", (now,)
        )
        rows = await cur.fetchall()
        await self.conn.execute(
            "UPDATE child_bots SET expires_at=?, updated_at=? WHERE expires_at > ?",
            (now, now, now),
        )
        await self.conn.commit()
        if child_manager:
            for row in rows:
                await child_manager.stop_child(int(row[0]))
        return len(rows)

    async def restore_all_access(self, child_manager: Any = None) -> int:
        """Extend all child bots and restart them (switching to free mode)."""
        days = await self.subscription_days()
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(days=days)).isoformat()
        cur = await self.conn.execute("SELECT id FROM child_bots")
        rows = await cur.fetchall()
        if not rows:
            return 0
        await self.conn.execute(
            "UPDATE child_bots SET expires_at=?, updated_at=?",
            (expires, now.isoformat()),
        )
        await self.conn.commit()
        if child_manager:
            for row in rows:
                child = await self.get_child_bot(int(row[0]))
                if child:
                    await child_manager.restart_child(child)
        return len(rows)

    async def is_child_active(self, expires_at: str | None) -> bool:
        if not await self.is_paid_mode():
            return True
        return self.is_active(expires_at)

    async def add_virtual_bot(
        self,
        owner_id: int,
        display_name: str,
        days: int,
        *,
        platform_username: str | None = None,
    ) -> dict[str, Any]:
        import secrets

        now = datetime.now(timezone.utc)
        expires = (now + timedelta(days=days)).isoformat()
        db_path = str(CLONES_DIR / f"clone_{owner_id}_{int(now.timestamp())}.db")
        token = f"virtual:{secrets.token_hex(16)}"
        name = display_name.strip()[:64]
        cur = await self.conn.execute(
            """
            INSERT INTO child_bots
            (owner_id, bot_token, bot_username, bot_name, db_path, expires_at, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                owner_id,
                token,
                platform_username,
                name,
                db_path,
                expires,
                now.isoformat(),
                now.isoformat(),
            ),
        )
        await self.conn.commit()
        return await self.get_child_bot(int(cur.lastrowid))  # type: ignore[arg-type]

    async def add_child_bot(
        self,
        owner_id: int,
        bot_token: str,
        bot_username: str | None,
        bot_name: str | None,
        days: int,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(days=days)).isoformat()
        db_path = str(CLONES_DIR / f"clone_{owner_id}_{int(now.timestamp())}.db")
        cur = await self.conn.execute(
            """
            INSERT INTO child_bots
            (owner_id, bot_token, bot_username, bot_name, db_path, expires_at, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                owner_id,
                bot_token,
                bot_username,
                bot_name,
                db_path,
                expires,
                now.isoformat(),
                now.isoformat(),
            ),
        )
        await self.conn.commit()
        return await self.get_child_bot(int(cur.lastrowid))  # type: ignore[arg-type]

    async def get_child_bot(self, bot_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute("SELECT * FROM child_bots WHERE id=?", (bot_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

    async def get_child_by_token(self, token: str) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            "SELECT * FROM child_bots WHERE bot_token=?", (token,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def get_user_bots(self, owner_id: int) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM child_bots WHERE owner_id=? ORDER BY id DESC",
            (owner_id,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def extend_child_bot(self, bot_id: int, days: int) -> str:
        now = datetime.now(timezone.utc)
        child = await self.get_child_bot(bot_id)
        if not child:
            raise ValueError("bot not found")
        base = now
        if child.get("expires_at"):
            current = _parse_utc(child["expires_at"])
            if current > now:
                base = current
        expires = (base + timedelta(days=days)).isoformat()
        await self.conn.execute(
            "UPDATE child_bots SET expires_at=?, updated_at=? WHERE id=?",
            (expires, now.isoformat(), bot_id),
        )
        await self.conn.execute(
            "DELETE FROM expiry_reminders WHERE child_bot_id=?", (bot_id,)
        )
        await self.conn.commit()
        return expires

    async def set_child_running(self, bot_id: int, running: bool) -> None:
        await self.conn.execute(
            "UPDATE child_bots SET is_running=? WHERE id=?",
            (1 if running else 0, bot_id),
        )
        await self.conn.commit()

    async def set_child_disabled(self, bot_id: int, disabled: bool) -> None:
        await self.conn.execute(
            "UPDATE child_bots SET is_disabled=? WHERE id=?",
            (1 if disabled else 0, bot_id),
        )
        await self.conn.commit()

    async def is_child_disabled(self, bot_id: int) -> bool:
        cur = await self.conn.execute(
            "SELECT is_disabled FROM child_bots WHERE id=?", (bot_id,)
        )
        row = await cur.fetchone()
        return bool(row and row[0])

    async def get_all_child_bots(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute("SELECT * FROM child_bots ORDER BY id DESC")
        return [dict(r) for r in await cur.fetchall()]

    async def get_global_auto_replies(self) -> list[dict[str, str]]:
        raw = await self.get_cfg("global_auto_replies", "[]")
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [
                    {"trigger": str(x["trigger"]), "reply_text": str(x["reply_text"])}
                    for x in data
                    if isinstance(x, dict) and x.get("trigger") and x.get("reply_text")
                ]
        except json.JSONDecodeError:
            pass
        return []

    async def save_global_auto_replies(self, items: list[dict[str, str]]) -> None:
        await self.set_cfg("global_auto_replies", json.dumps(items, ensure_ascii=False))

    async def add_global_auto_reply(self, trigger: str, reply_text: str) -> None:
        items = await self.get_global_auto_replies()
        trigger = trigger.strip().lower()
        items = [x for x in items if x["trigger"] != trigger]
        items.append({"trigger": trigger, "reply_text": reply_text.strip()})
        await self.save_global_auto_replies(items)

    async def clear_global_auto_replies(self) -> None:
        await self.save_global_auto_replies([])

    async def get_global_auto_reply_at(self, index: int) -> dict[str, str] | None:
        items = await self.get_global_auto_replies()
        if 0 <= index < len(items):
            return items[index]
        return None

    async def update_global_auto_reply_at(
        self,
        index: int,
        *,
        trigger: str | None = None,
        reply_text: str | None = None,
    ) -> dict[str, str] | None:
        items = await self.get_global_auto_replies()
        if not (0 <= index < len(items)):
            return None
        if trigger is not None:
            items[index]["trigger"] = trigger.strip().lower()
        if reply_text is not None:
            items[index]["reply_text"] = reply_text.strip()
        await self.save_global_auto_replies(items)
        return items[index]

    async def remove_global_auto_reply_at(self, index: int) -> dict[str, str] | None:
        items = await self.get_global_auto_replies()
        if not (0 <= index < len(items)):
            return None
        removed = items.pop(index)
        await self.save_global_auto_replies(items)
        return removed

    async def get_active_child_bots(self) -> list[dict[str, Any]]:
        if not await self.is_paid_mode():
            cur = await self.conn.execute(
                "SELECT * FROM child_bots WHERE COALESCE(is_disabled, 0)=0 ORDER BY id"
            )
            return [dict(r) for r in await cur.fetchall()]
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            "SELECT * FROM child_bots WHERE expires_at > ? AND COALESCE(is_disabled, 0)=0 ORDER BY id",
            (now,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def get_expired_running_bots(self) -> list[dict[str, Any]]:
        if not await self.is_paid_mode():
            return []
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            "SELECT * FROM child_bots WHERE expires_at <= ? AND is_running=1",
            (now,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def get_bots_needing_reminder(self, hours: int = 24) -> list[dict[str, Any]]:
        if not await self.is_paid_mode():
            return []
        now = datetime.now(timezone.utc)
        end = (now + timedelta(hours=hours)).isoformat()
        cur = await self.conn.execute(
            """
            SELECT c.* FROM child_bots c
            LEFT JOIN expiry_reminders r ON r.child_bot_id = c.id
            WHERE c.expires_at > ? AND c.expires_at <= ?
              AND r.child_bot_id IS NULL
            """,
            (now.isoformat(), end),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def mark_reminder_sent(self, bot_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            "INSERT OR REPLACE INTO expiry_reminders (child_bot_id, sent_at) VALUES (?,?)",
            (bot_id, now),
        )
        await self.conn.commit()

    async def record_payment(
        self,
        user_id: int,
        amount: int,
        days: int,
        payment_type: str,
        *,
        child_bot_id: int | None = None,
        payload: str = "",
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            """
            INSERT INTO payments
            (user_id, child_bot_id, amount_stars, days, payment_type, payload, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (user_id, child_bot_id, amount, days, payment_type, payload, now),
        )
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        fin_day = await self.get_cfg("finance_day", "")
        today_amt = int(await self.get_cfg("finance_today", "0"))
        if fin_day != today:
            today_amt = 0
            await self.set_cfg("finance_day", today)
        total = int(await self.get_cfg("finance_total", "0"))
        await self.set_cfg("finance_today", str(today_amt + amount))
        await self.set_cfg("finance_total", str(total + amount))
        await self.conn.commit()
        return int(cur.lastrowid)  # type: ignore[arg-type]

    async def get_pending_create(self, user_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            """
            SELECT * FROM payments
            WHERE user_id=? AND payment_type IN (
                'create', 'manual_create', 'crypto_create',
                'wallet_create', 'cryptobot_create'
            )
              AND child_bot_id IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def fulfill_create_payment(self, user_id: int, child_bot_id: int) -> None:
        await self.conn.execute(
            """
            UPDATE payments SET child_bot_id=?
            WHERE id = (
                SELECT id FROM payments
                WHERE user_id=? AND payment_type IN (
                    'create', 'manual_create', 'crypto_create',
                    'wallet_create', 'cryptobot_create'
                )
                  AND child_bot_id IS NULL
                ORDER BY id DESC LIMIT 1
            )
            """,
            (child_bot_id, user_id),
        )
        await self.conn.commit()

    async def create_wallet_order(
        self,
        *,
        external_id: str,
        wallet_order_id: int,
        user_id: int,
        payment_type: str,
        days: int,
        currency: str,
        amount: str,
        child_bot_id: int | None = None,
        provider: str = "wallet_pay",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            """
            INSERT INTO wallet_orders
            (external_id, wallet_order_id, user_id, payment_type, child_bot_id,
             days, currency, amount, status, provider, created_at)
            VALUES (?,?,?,?,?,?,?,?, 'pending', ?, ?)
            """,
            (
                external_id,
                wallet_order_id,
                user_id,
                payment_type,
                child_bot_id,
                days,
                currency,
                amount,
                provider,
                now,
            ),
        )
        await self.conn.commit()

    async def get_wallet_order_by_invoice(
        self,
        invoice_id: int,
        *,
        provider: str,
    ) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            """
            SELECT * FROM wallet_orders
            WHERE wallet_order_id=? AND provider=? AND status='pending'
            ORDER BY id DESC LIMIT 1
            """,
            (invoice_id, provider),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def get_pending_crypto_orders(
        self,
        provider: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            """
            SELECT * FROM wallet_orders
            WHERE status='pending' AND provider=? AND wallet_order_id IS NOT NULL
            ORDER BY id DESC LIMIT ?
            """,
            (provider, limit),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def is_cryptobot_event_processed(self, update_id: int) -> bool:
        cur = await self.conn.execute(
            "SELECT 1 FROM cryptobot_webhook_events WHERE update_id=?",
            (update_id,),
        )
        return await cur.fetchone() is not None

    async def mark_cryptobot_event_processed(self, update_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            "INSERT OR IGNORE INTO cryptobot_webhook_events (update_id, processed_at) VALUES (?,?)",
            (update_id, now),
        )
        await self.conn.commit()

    async def get_wallet_order(self, external_id: str) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            "SELECT * FROM wallet_orders WHERE external_id=?",
            (external_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def get_pending_wallet_orders(self, limit: int = 50) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            """
            SELECT * FROM wallet_orders
            WHERE status='pending' AND provider='wallet_pay' AND wallet_order_id IS NOT NULL
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def mark_wallet_order_paid(self, external_id: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            """
            UPDATE wallet_orders SET status='paid', paid_at=?
            WHERE external_id=? AND status='pending'
            """,
            (now, external_id),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def mark_wallet_order_failed(self, external_id: str) -> None:
        await self.conn.execute(
            "UPDATE wallet_orders SET status='failed' WHERE external_id=? AND status='pending'",
            (external_id,),
        )
        await self.conn.commit()

    async def is_wallet_event_processed(self, event_id: int) -> bool:
        cur = await self.conn.execute(
            "SELECT 1 FROM wallet_webhook_events WHERE event_id=?",
            (event_id,),
        )
        return await cur.fetchone() is not None

    async def mark_wallet_event_processed(self, event_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            "INSERT OR IGNORE INTO wallet_webhook_events (event_id, processed_at) VALUES (?,?)",
            (event_id, now),
        )
        await self.conn.commit()

    async def get_recent_payments(self, limit: int = 20) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            """
            SELECT p.*, u.first_name, u.username, c.bot_name, c.bot_username
            FROM payments p
            LEFT JOIN platform_users u ON u.user_id = p.user_id
            LEFT JOIN child_bots c ON c.id = p.child_bot_id
            ORDER BY p.id DESC LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def get_stats(self) -> dict[str, int]:
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute("SELECT COUNT(*) FROM child_bots")
        total = int((await cur.fetchone())[0])
        cur = await self.conn.execute(
            "SELECT COUNT(*) FROM child_bots WHERE expires_at > ?", (now,)
        )
        active = int((await cur.fetchone())[0])
        cur = await self.conn.execute("SELECT COUNT(*) FROM platform_users")
        users = int((await cur.fetchone())[0])
        return {
            "total_bots": total,
            "active_bots": active,
            "expired_bots": total - active,
            "users": users,
            "today_stars": int(await self.get_cfg("finance_today", "0")),
            "total_stars": int(await self.get_cfg("finance_total", "0")),
        }

    def days_remaining(self, expires_at: str | None) -> int:
        if not expires_at:
            return 0
        delta = _parse_utc(expires_at) - datetime.now(timezone.utc)
        if delta.total_seconds() <= 0:
            return 0
        return delta.days + (1 if delta.seconds else 0)

    def is_active(self, expires_at: str | None) -> bool:
        if not expires_at:
            return False
        return _parse_utc(expires_at) > datetime.now(timezone.utc)

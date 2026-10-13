from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite

from bot.database.defaults import DEFAULTS

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    language_code TEXT,
    is_blocked INTEGER DEFAULT 0,
    ban_reason TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    chat_type TEXT NOT NULL,
    title TEXT,
    username TEXT,
    is_active INTEGER DEFAULT 1,
    added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_settings (
    admin_id INTEGER PRIMARY KEY,
    ui_language TEXT DEFAULT 'ar',
    notify_join INTEGER DEFAULT 1,
    notify_ban INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS daily_stats (
    date TEXT PRIMARY KEY,
    new_users INTEGER DEFAULT 0,
    messages INTEGER DEFAULT 0,
    sessions INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id TEXT PRIMARY KEY,
    admin_id INTEGER NOT NULL,
    target_type TEXT NOT NULL,
    send_method TEXT NOT NULL,
    content_json TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    total_targets INTEGER DEFAULT 0,
    sent INTEGER DEFAULT 0,
    blocked INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    started_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS auto_post (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    is_enabled INTEGER DEFAULT 0,
    interval_seconds INTEGER DEFAULT 300,
    target_type TEXT DEFAULT 'groups',
    content_json TEXT,
    last_post_at TEXT,
    next_post_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS welcome_message (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    text TEXT,
    media_type TEXT,
    file_id TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS auto_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger TEXT NOT NULL UNIQUE,
    reply_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mandatory_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL UNIQUE,
    chat_type TEXT NOT NULL,
    title TEXT,
    username TEXT,
    invite_link TEXT,
    added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sub_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    is_enabled INTEGER DEFAULT 0,
    notify_on_join INTEGER DEFAULT 1,
    display_grouped INTEGER DEFAULT 1,
    verify_button INTEGER DEFAULT 0,
    verify_icon INTEGER DEFAULT 0,
    style_enabled INTEGER DEFAULT 0,
    grouped_message TEXT DEFAULT '',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS bot_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quick_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot INTEGER NOT NULL UNIQUE,
    reply_text TEXT,
    media_type TEXT,
    file_id TEXT,
    caption TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inactive_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    days INTEGER NOT NULL,
    message_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pending_users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    requested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_forwards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_msg_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduled_deletions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    delete_at TEXT NOT NULL,
    source TEXT DEFAULT 'bot',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_buttons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    url TEXT NOT NULL,
    row_pos INTEGER DEFAULT 0,
    col_pos INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bot_admins (
    user_id INTEGER PRIMARY KEY,
    added_by INTEGER,
    added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    details TEXT,
    user_id INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS finance_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    price_stars INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS finance_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER,
    order_type TEXT NOT NULL,
    amount_stars INTEGER NOT NULL,
    payload TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_access (
    user_id INTEGER PRIMARY KEY,
    expires_at TEXT,
    granted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_inactive_state (
    user_id INTEGER PRIMARY KEY,
    reminder_step INTEGER DEFAULT 0,
    last_reminder_at TEXT,
    returned_at TEXT
);

CREATE TABLE IF NOT EXISTS verification_sessions (
    user_id INTEGER PRIMARY KEY,
    mode TEXT NOT NULL,
    challenge TEXT,
    passed INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS auto_post_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    content_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

MAX_AUTOPOST_ITEMS = 10


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.execute(
            "INSERT OR IGNORE INTO auto_post (id, is_enabled) VALUES (1, 0)"
        )
        await self._conn.execute(
            "INSERT OR IGNORE INTO welcome_message (id) VALUES (1)"
        )
        await self._conn.execute(
            "INSERT OR IGNORE INTO sub_settings (id, is_enabled) VALUES (1, 0)"
        )
        for key, value in DEFAULTS.items():
            await self._conn.execute(
                "INSERT OR IGNORE INTO bot_config (key, value) VALUES (?, ?)",
                (key, value),
            )
        await self._conn.commit()
        await self._migrate()
        await self._migrate_autopost_items()
        await self._apply_safety_defaults()

    async def _apply_safety_defaults(self) -> None:
        await self.conn.execute(
            "INSERT OR IGNORE INTO bot_config (key, value) VALUES ('content_protection', '1')"
        )
        await self.conn.execute(
            "UPDATE bot_config SET value='1' WHERE key='content_protection'"
        )
        await self.conn.execute(
            "INSERT OR IGNORE INTO bot_config (key, value) VALUES ('spam_safe_mode', '1')"
        )
        if await self.get_cfg_bool("spam_safe_mode"):
            min_iv = int(
                await self.get_cfg("autopost_min_interval_seconds", "300") or "300"
            )
            await self.conn.execute(
                "UPDATE auto_post SET interval_seconds=? WHERE interval_seconds < ?",
                (min_iv, min_iv),
            )
        await self.conn.commit()

    async def _migrate_autopost_items(self) -> None:
        if await self.count_auto_post_items() > 0:
            return
        settings = await self.get_auto_post()
        if settings and settings.get("content"):
            await self.add_auto_post_item(settings["content"])

    async def _migrate(self) -> None:
        alters = [
            "ALTER TABLE sub_settings ADD COLUMN display_grouped INTEGER DEFAULT 1",
            "ALTER TABLE sub_settings ADD COLUMN verify_button INTEGER DEFAULT 0",
            "ALTER TABLE sub_settings ADD COLUMN verify_icon INTEGER DEFAULT 0",
            "ALTER TABLE sub_settings ADD COLUMN style_enabled INTEGER DEFAULT 0",
            "ALTER TABLE sub_settings ADD COLUMN grouped_message TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN last_active_at TEXT",
            "ALTER TABLE users ADD COLUMN phone TEXT",
            "ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0",
            "ALTER TABLE user_access ADD COLUMN expiry_reminder_sent INTEGER DEFAULT 0",
        ]
        for sql in alters:
            try:
                await self.conn.execute(sql)
            except Exception:
                pass
        await self.conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database not connected")
        return self._conn

    # ── Users ─────────────────────────────────────────────────────────────────

    async def upsert_user(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
        language_code: str | None,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        )
        exists = await cur.fetchone()
        if exists:
            await self.conn.execute(
                "UPDATE users SET username=?, first_name=?, language_code=? WHERE user_id=?",
                (username, first_name, language_code, user_id),
            )
            await self.conn.commit()
            return False
        await self.conn.execute(
            "INSERT INTO users (user_id, username, first_name, language_code, created_at) VALUES (?,?,?,?,?)",
            (user_id, username, first_name, language_code, now),
        )
        await self._increment_daily("new_users")
        await self.conn.commit()
        return True

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            "SELECT * FROM users WHERE user_id=?", (user_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def ban_user(self, user_id: int, reason: str | None = None) -> None:
        await self.conn.execute(
            "UPDATE users SET is_blocked=1, ban_reason=? WHERE user_id=?",
            (reason, user_id),
        )
        await self.conn.commit()

    async def unban_user(self, user_id: int) -> None:
        await self.conn.execute(
            "UPDATE users SET is_blocked=0, ban_reason=NULL WHERE user_id=?",
            (user_id,),
        )
        await self.conn.commit()

    async def mark_user_blocked(self, user_id: int) -> None:
        await self.conn.execute(
            "UPDATE users SET is_blocked=1 WHERE user_id=?", (user_id,)
        )
        await self.conn.commit()

    async def get_banned_users(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM users WHERE is_blocked=1 ORDER BY created_at DESC"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def count_users(self) -> int:
        cur = await self.conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_blocked=0"
        )
        row = await cur.fetchone()
        return int(row[0])

    async def count_banned(self) -> int:
        cur = await self.conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_blocked=1"
        )
        row = await cur.fetchone()
        return int(row[0])

    # ── Chats ─────────────────────────────────────────────────────────────────

    async def upsert_chat(
        self,
        chat_id: int,
        chat_type: str,
        title: str | None,
        username: str | None = None,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            "SELECT chat_id FROM chats WHERE chat_id=?", (chat_id,)
        )
        exists = await cur.fetchone()
        if exists:
            await self.conn.execute(
                "UPDATE chats SET chat_type=?, title=?, username=?, is_active=1 WHERE chat_id=?",
                (chat_type, title, username, chat_id),
            )
            await self.conn.commit()
            return False
        await self.conn.execute(
            "INSERT INTO chats (chat_id, chat_type, title, username, added_at) VALUES (?,?,?,?,?)",
            (chat_id, chat_type, title, username, now),
        )
        await self.conn.commit()
        return True

    async def deactivate_chat(self, chat_id: int) -> None:
        await self.conn.execute(
            "UPDATE chats SET is_active=0 WHERE chat_id=?", (chat_id,)
        )
        await self.conn.commit()

    async def count_groups(self) -> int:
        cur = await self.conn.execute(
            "SELECT COUNT(*) FROM chats WHERE is_active=1 AND chat_type IN ('group','supergroup','channel')"
        )
        row = await cur.fetchone()
        return int(row[0])

    async def count_total_chats(self) -> int:
        users = await self.count_users()
        groups = await self.count_groups()
        return users + groups

    async def increment_bot_blocks(self) -> int:
        current = int(await self.get_cfg("total_bot_blocks", "0"))
        current += 1
        await self.set_cfg("total_bot_blocks", str(current))
        return current

    async def get_targets(self, target_type: str) -> list[int]:
        if target_type == "private":
            cur = await self.conn.execute(
                "SELECT user_id FROM users WHERE is_blocked=0"
            )
        elif target_type == "groups":
            cur = await self.conn.execute(
                "SELECT chat_id FROM chats WHERE is_active=1 AND chat_type IN ('group','supergroup','channel')"
            )
        else:
            cur = await self.conn.execute(
                """
                SELECT user_id AS chat_id FROM users WHERE is_blocked=0
                UNION
                SELECT chat_id FROM chats WHERE is_active=1 AND chat_type IN ('group','supergroup','channel')
                """
            )
        rows = await cur.fetchall()
        return [row[0] for row in rows]

    # ── Admin settings ─────────────────────────────────────────────────────────

    async def get_admin_settings(
        self, admin_id: int, default_lang: str = "ar"
    ) -> dict[str, Any]:
        cur = await self.conn.execute(
            "SELECT * FROM admin_settings WHERE admin_id=?", (admin_id,)
        )
        row = await cur.fetchone()
        if row:
            return dict(row)
        return {
            "admin_id": admin_id,
            "ui_language": default_lang,
            "notify_join": 1,
            "notify_ban": 1,
        }

    async def get_admin_language(
        self, admin_id: int, default: str = "ar"
    ) -> str:
        s = await self.get_admin_settings(admin_id, default)
        lang = s.get("ui_language") or default
        return "ar" if lang == "en" else lang

    async def set_admin_language(self, admin_id: int, lang: str) -> None:
        if lang != "ar":
            lang = "ar"
        await self.conn.execute(
            """
            INSERT INTO admin_settings (admin_id, ui_language)
            VALUES (?,?)
            ON CONFLICT(admin_id) DO UPDATE SET ui_language=excluded.ui_language
            """,
            (admin_id, lang),
        )
        await self.conn.commit()

    async def toggle_notification(
        self, admin_id: int, field: str, value: bool
    ) -> None:
        await self.conn.execute(
            f"""
            INSERT INTO admin_settings (admin_id, {field})
            VALUES (?,?)
            ON CONFLICT(admin_id) DO UPDATE SET {field}=excluded.{field}
            """,
            (admin_id, int(value)),
        )
        await self.conn.commit()

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def _increment_daily(self, field: str) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await self.conn.execute(
            f"""
            INSERT INTO daily_stats (date, {field}) VALUES (?,1)
            ON CONFLICT(date) DO UPDATE SET {field}={field}+1
            """,
            (today,),
        )

    async def increment_messages(self) -> None:
        await self._increment_daily("messages")
        await self.conn.commit()

    async def increment_sessions(self) -> None:
        await self._increment_daily("sessions")
        await self.conn.commit()

    async def get_today_stats(self) -> dict[str, int]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cur = await self.conn.execute(
            "SELECT * FROM daily_stats WHERE date=?", (today,)
        )
        row = await cur.fetchone()
        if not row:
            return {"new_users": 0, "messages": 0, "sessions": 0}
        return {
            "new_users": row["new_users"],
            "messages": row["messages"],
            "sessions": row["sessions"],
        }

    # ── Broadcast ─────────────────────────────────────────────────────────────

    async def create_broadcast(
        self,
        broadcast_id: str,
        admin_id: int,
        target_type: str,
        send_method: str,
        content: dict[str, Any],
        total_targets: int,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            """
            INSERT INTO broadcasts
            (id, admin_id, target_type, send_method, content_json, total_targets, started_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                broadcast_id,
                admin_id,
                target_type,
                send_method,
                json.dumps(content, ensure_ascii=False),
                total_targets,
                now,
            ),
        )
        await self.conn.commit()

    async def update_broadcast_stats(
        self,
        broadcast_id: str,
        sent: int,
        blocked: int,
        failed: int,
        status: str | None = None,
    ) -> None:
        if status:
            finished = (
                datetime.now(timezone.utc).isoformat()
                if status != "running"
                else None
            )
            await self.conn.execute(
                """
                UPDATE broadcasts SET sent=?,blocked=?,failed=?,status=?,
                finished_at=COALESCE(?,finished_at) WHERE id=?
                """,
                (sent, blocked, failed, status, finished, broadcast_id),
            )
        else:
            await self.conn.execute(
                "UPDATE broadcasts SET sent=?,blocked=?,failed=? WHERE id=?",
                (sent, blocked, failed, broadcast_id),
            )
        await self.conn.commit()

    # ── Auto post ─────────────────────────────────────────────────────────────

    async def get_auto_post(self) -> dict[str, Any] | None:
        cur = await self.conn.execute("SELECT * FROM auto_post WHERE id=1")
        row = await cur.fetchone()
        if not row:
            return None
        data = dict(row)
        data["content"] = (
            json.loads(data.pop("content_json")) if data.get("content_json") else None
        )
        return data

    async def save_auto_post(
        self,
        *,
        is_enabled: bool | None = None,
        interval_seconds: int | None = None,
        target_type: str | None = None,
        content: dict[str, Any] | None = None,
        last_post_at: str | None = None,
        next_post_at: str | None = None,
    ) -> None:
        current = await self.get_auto_post() or {}
        now = datetime.now(timezone.utc).isoformat()
        new_content = content if content is not None else current.get("content")
        resolved_interval = interval_seconds
        if interval_seconds is not None and await self.get_cfg_bool("spam_safe_mode"):
            try:
                min_iv = int(await self.get_cfg("autopost_min_interval_seconds", "300"))
            except ValueError:
                min_iv = 300
            resolved_interval = max(interval_seconds, min_iv)
        await self.conn.execute(
            """
            UPDATE auto_post SET
                is_enabled=?, interval_seconds=?, target_type=?,
                content_json=?, last_post_at=?, next_post_at=?, updated_at=?
            WHERE id=1
            """,
            (
                int(
                    is_enabled
                    if is_enabled is not None
                    else current.get("is_enabled", 0)
                ),
                resolved_interval
                if resolved_interval is not None
                else current.get("interval_seconds", 300),
                target_type
                if target_type is not None
                else current.get("target_type", "groups"),
                json.dumps(new_content, ensure_ascii=False) if new_content else None,
                last_post_at
                if last_post_at is not None
                else current.get("last_post_at"),
                next_post_at
                if next_post_at is not None
                else current.get("next_post_at"),
                now,
            ),
        )
        await self.conn.commit()

    async def list_auto_post_items(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM auto_post_items ORDER BY sort_order, id"
        )
        rows = []
        for row in await cur.fetchall():
            data = dict(row)
            data["content"] = json.loads(data.pop("content_json"))
            rows.append(data)
        return rows

    async def get_auto_post_item(self, item_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            "SELECT * FROM auto_post_items WHERE id=?", (item_id,)
        )
        row = await cur.fetchone()
        if not row:
            return None
        data = dict(row)
        data["content"] = json.loads(data.pop("content_json"))
        return data

    async def count_auto_post_items(self) -> int:
        cur = await self.conn.execute("SELECT COUNT(*) FROM auto_post_items")
        row = await cur.fetchone()
        return int(row[0]) if row else 0

    async def add_auto_post_item(self, content: dict[str, Any]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM auto_post_items"
        )
        row = await cur.fetchone()
        sort_order = int(row[0]) if row else 0
        cur = await self.conn.execute(
            """
            INSERT INTO auto_post_items (sort_order, content_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (sort_order, json.dumps(content, ensure_ascii=False), now, now),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def update_auto_post_item(
        self, item_id: int, content: dict[str, Any]
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            """
            UPDATE auto_post_items
            SET content_json=?, updated_at=?
            WHERE id=?
            """,
            (json.dumps(content, ensure_ascii=False), now, item_id),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def delete_auto_post_item(self, item_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM auto_post_items WHERE id=?", (item_id,)
        )
        await self.conn.commit()

    # ── Welcome message ────────────────────────────────────────────────────────

    async def get_welcome_message(self) -> dict[str, Any]:
        cur = await self.conn.execute("SELECT * FROM welcome_message WHERE id=1")
        row = await cur.fetchone()
        return dict(row) if row else {}

    async def save_welcome_message(
        self,
        text: str | None = None,
        media_type: str | None = None,
        file_id: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            "UPDATE welcome_message SET text=?, media_type=?, file_id=?, updated_at=? WHERE id=1",
            (text, media_type, file_id, now),
        )
        await self.conn.commit()

    # ── Auto replies ──────────────────────────────────────────────────────────

    async def get_auto_replies(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM auto_replies ORDER BY created_at DESC"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def add_auto_reply(self, trigger: str, reply_text: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self.conn.execute(
                "INSERT INTO auto_replies (trigger, reply_text, created_at) VALUES (?,?,?)",
                (trigger.lower(), reply_text, now),
            )
            await self.conn.commit()
            return True
        except Exception:
            return False

    async def delete_auto_reply(self, reply_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM auto_replies WHERE id=?", (reply_id,)
        )
        await self.conn.commit()

    async def find_auto_reply(self, text: str) -> str | None:
        cur = await self.conn.execute(
            "SELECT reply_text FROM auto_replies WHERE ? LIKE '%' || trigger || '%'",
            (text.lower(),),
        )
        row = await cur.fetchone()
        return row[0] if row else None

    # ── Mandatory subscriptions ───────────────────────────────────────────────

    async def get_sub_settings(self) -> dict[str, Any]:
        cur = await self.conn.execute("SELECT * FROM sub_settings WHERE id=1")
        row = await cur.fetchone()
        return dict(row) if row else {"is_enabled": 0, "notify_on_join": 1}

    async def set_sub_enabled(self, value: bool) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            "UPDATE sub_settings SET is_enabled=?, updated_at=? WHERE id=1",
            (int(value), now),
        )
        await self.conn.commit()

    async def get_mandatory_subs(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM mandatory_subscriptions ORDER BY added_at"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def add_mandatory_sub(
        self,
        chat_id: int,
        chat_type: str,
        title: str | None,
        username: str | None,
        invite_link: str | None,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self.conn.execute(
                """
                INSERT INTO mandatory_subscriptions
                (chat_id, chat_type, title, username, invite_link, added_at)
                VALUES (?,?,?,?,?,?)
                """,
                (chat_id, chat_type, title, username, invite_link, now),
            )
            await self.conn.commit()
            return True
        except Exception:
            return False

    async def remove_mandatory_sub(self, sub_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM mandatory_subscriptions WHERE id=?", (sub_id,)
        )
        await self.conn.commit()

    # ── Bot config (key-value) ────────────────────────────────────────────────

    async def get_cfg(self, key: str, default: str | None = None) -> str:
        cur = await self.conn.execute(
            "SELECT value FROM bot_config WHERE key=?", (key,)
        )
        row = await cur.fetchone()
        if row:
            return row[0]
        return default if default is not None else DEFAULTS.get(key, "")

    async def get_cfg_bool(self, key: str) -> bool:
        return (await self.get_cfg(key, "0")) == "1"

    async def set_cfg(self, key: str, value: str) -> None:
        await self.conn.execute(
            """
            INSERT INTO bot_config (key, value) VALUES (?,?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, value),
        )
        await self.conn.commit()

    async def toggle_cfg(self, key: str) -> bool:
        current = await self.get_cfg_bool(key)
        new_val = not current
        await self.set_cfg(key, "1" if new_val else "0")
        return new_val

    async def get_all_cfg(self) -> dict[str, str]:
        cur = await self.conn.execute("SELECT key, value FROM bot_config")
        rows = await cur.fetchall()
        result = dict(DEFAULTS)
        result.update({row[0]: row[1] for row in rows})
        return result

    # ── Quick replies (/r1 … /r20) ────────────────────────────────────────────

    async def get_quick_replies(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM quick_replies ORDER BY slot"
        )
        return [dict(r) for r in await cur.fetchall()]

    async def get_quick_reply(self, slot: int) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            "SELECT * FROM quick_replies WHERE slot=?", (slot,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def save_quick_reply(
        self,
        slot: int,
        reply_text: str | None = None,
        media_type: str | None = None,
        file_id: str | None = None,
        caption: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            """
            INSERT INTO quick_replies (slot, reply_text, media_type, file_id, caption, created_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(slot) DO UPDATE SET
                reply_text=excluded.reply_text,
                media_type=excluded.media_type,
                file_id=excluded.file_id,
                caption=excluded.caption
            """,
            (slot, reply_text, media_type, file_id, caption, now),
        )
        await self.conn.commit()

    async def delete_quick_reply(self, slot: int) -> None:
        await self.conn.execute("DELETE FROM quick_replies WHERE slot=?", (slot,))
        await self.conn.commit()

    async def count_quick_replies(self) -> int:
        cur = await self.conn.execute("SELECT COUNT(*) FROM quick_replies")
        return int((await cur.fetchone())[0])

    # ── Inactive reminders ────────────────────────────────────────────────────

    async def get_inactive_reminders(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM inactive_reminders ORDER BY days"
        )
        return [dict(r) for r in await cur.fetchall()]

    async def add_inactive_reminder(self, days: int, message_text: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute("SELECT COUNT(*) FROM inactive_reminders")
        if int((await cur.fetchone())[0]) >= 5:
            return False
        await self.conn.execute(
            "INSERT INTO inactive_reminders (days, message_text, created_at) VALUES (?,?,?)",
            (days, message_text, now),
        )
        await self.conn.commit()
        return True

    async def delete_inactive_reminder(self, reminder_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM inactive_reminders WHERE id=?", (reminder_id,)
        )
        await self.conn.commit()

    # ── Pending users (verification) ──────────────────────────────────────────

    async def add_pending_user(
        self, user_id: int, username: str | None, first_name: str | None
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            """
            INSERT OR REPLACE INTO pending_users (user_id, username, first_name, requested_at)
            VALUES (?,?,?,?)
            """,
            (user_id, username, first_name, now),
        )
        await self.conn.commit()

    async def remove_pending_user(self, user_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM pending_users WHERE user_id=?", (user_id,)
        )
        await self.conn.commit()

    async def get_pending_users(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM pending_users ORDER BY requested_at DESC"
        )
        return [dict(r) for r in await cur.fetchall()]

    async def count_pending_users(self) -> int:
        cur = await self.conn.execute("SELECT COUNT(*) FROM pending_users")
        return int((await cur.fetchone())[0])

    # ── User forwards (for quick replies) ─────────────────────────────────────

    async def save_user_forward(
        self, admin_msg_id: int, user_id: int
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            "INSERT INTO user_forwards (admin_msg_id, user_id, created_at) VALUES (?,?,?)",
            (admin_msg_id, user_id, now),
        )
        await self.conn.commit()

    async def get_user_by_forward(self, admin_msg_id: int) -> int | None:
        cur = await self.conn.execute(
            "SELECT user_id FROM user_forwards WHERE admin_msg_id=? ORDER BY id DESC LIMIT 1",
            (admin_msg_id,),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else None

    async def update_sub_setting(self, field: str, value: int | str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            f"UPDATE sub_settings SET {field}=?, updated_at=? WHERE id=1",
            (value, now),
        )
        await self.conn.commit()

    # ── Chat lookup ───────────────────────────────────────────────────────────

    async def get_chat(self, chat_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

    # ── User activity ─────────────────────────────────────────────────────────

    async def touch_user_activity(self, user_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        state = await self.get_inactive_state(user_id)
        was_waiting = state is not None and state.get("last_reminder_at")
        await self.conn.execute(
            "UPDATE users SET last_active_at=? WHERE user_id=?",
            (now, user_id),
        )
        if was_waiting:
            await self.conn.execute(
                """
                INSERT INTO user_inactive_state (user_id, reminder_step, last_reminder_at, returned_at)
                VALUES (?, 0, NULL, ?)
                ON CONFLICT(user_id) DO UPDATE SET reminder_step=0, returned_at=excluded.returned_at
                """,
                (user_id, now),
            )
            sent = int(await self.get_cfg("inactive_sent", "0"))
            returned = int(await self.get_cfg("inactive_returned", "0"))
            await self.set_cfg("inactive_returned", str(returned + 1))
            if await self.get_cfg_bool("inactive_return_reward"):
                await self.grant_access(user_id, days=7)
        await self.conn.commit()

    async def set_user_verified(self, user_id: int, phone: str | None = None) -> None:
        await self.conn.execute(
            "UPDATE users SET verified=1, phone=COALESCE(?, phone) WHERE user_id=?",
            (phone, user_id),
        )
        await self.conn.commit()

    async def is_user_verified(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return bool(user and user.get("verified"))

    # ── Scheduled deletions ───────────────────────────────────────────────────

    async def schedule_deletion(
        self, chat_id: int, message_id: int, delete_at: str, source: str = "bot"
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            """
            INSERT INTO scheduled_deletions (chat_id, message_id, delete_at, source, created_at)
            VALUES (?,?,?,?,?)
            """,
            (chat_id, message_id, delete_at, source, now),
        )
        await self.conn.commit()

    async def get_due_deletions(self, limit: int = 50) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            """
            SELECT * FROM scheduled_deletions
            WHERE delete_at <= ? ORDER BY delete_at LIMIT ?
            """,
            (now, limit),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def remove_deletion(self, deletion_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM scheduled_deletions WHERE id=?", (deletion_id,)
        )
        await self.conn.commit()

    async def increment_delete_stats(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        total = int(await self.get_cfg("auto_delete_total", "0")) + 1
        await self.set_cfg("auto_delete_total", str(total))
        last_day = await self.get_cfg("auto_delete_day", "")
        today_count = int(await self.get_cfg("auto_delete_today", "0"))
        if last_day != today:
            today_count = 0
            await self.set_cfg("auto_delete_day", today)
        await self.set_cfg("auto_delete_today", str(today_count + 1))

    # ── Content buttons ───────────────────────────────────────────────────────

    async def get_content_buttons(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM content_buttons WHERE is_active=1 ORDER BY row_pos, col_pos, id"
        )
        return [dict(r) for r in await cur.fetchall()]

    async def count_content_buttons(self) -> int:
        cur = await self.conn.execute(
            "SELECT COUNT(*) FROM content_buttons WHERE is_active=1"
        )
        return int((await cur.fetchone())[0])

    async def add_content_button(self, label: str, url: str, row_pos: int = 0) -> None:
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            "SELECT COUNT(*) FROM content_buttons WHERE row_pos=? AND is_active=1",
            (row_pos,),
        )
        col = int((await cur.fetchone())[0])
        await self.conn.execute(
            """
            INSERT INTO content_buttons (label, url, row_pos, col_pos, created_at)
            VALUES (?,?,?,?,?)
            """,
            (label, url, row_pos, col, now),
        )
        await self.conn.commit()

    async def delete_content_button(self, button_id: int) -> None:
        await self.conn.execute(
            "UPDATE content_buttons SET is_active=0 WHERE id=?", (button_id,)
        )
        await self.conn.commit()

    async def get_content_button(self, button_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            "SELECT * FROM content_buttons WHERE id=?", (button_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    # ── Bot admins ────────────────────────────────────────────────────────────

    async def is_admin(self, user_id: int, primary_admin_id: int) -> bool:
        if user_id == primary_admin_id:
            return True
        cur = await self.conn.execute(
            "SELECT user_id FROM bot_admins WHERE user_id=?", (user_id,)
        )
        return await cur.fetchone() is not None

    async def get_bot_admins(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute("SELECT * FROM bot_admins ORDER BY added_at")
        return [dict(r) for r in await cur.fetchall()]

    async def add_bot_admin(self, user_id: int, added_by: int) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self.conn.execute(
                "INSERT INTO bot_admins (user_id, added_by, added_at) VALUES (?,?,?)",
                (user_id, added_by, now),
            )
            await self.conn.commit()
            return True
        except Exception:
            return False

    async def remove_bot_admin(self, user_id: int) -> None:
        await self.conn.execute("DELETE FROM bot_admins WHERE user_id=?", (user_id,))
        await self.conn.commit()

    # ── Activity logs ─────────────────────────────────────────────────────────

    async def log_activity(
        self, action: str, details: str | None = None, user_id: int | None = None
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            "INSERT INTO activity_logs (action, details, user_id, created_at) VALUES (?,?,?,?)",
            (action, details, user_id, now),
        )
        await self.conn.commit()

    async def get_activity_logs(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM activity_logs ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [dict(r) for r in await cur.fetchall()]

    # ── Finance ───────────────────────────────────────────────────────────────

    async def get_finance_products(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM finance_products WHERE is_active=1 ORDER BY id"
        )
        return [dict(r) for r in await cur.fetchall()]

    async def add_finance_product(
        self, title: str, description: str, price_stars: int
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            """
            INSERT INTO finance_products (title, description, price_stars, created_at)
            VALUES (?,?,?,?)
            """,
            (title, description, price_stars, now),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def delete_finance_product(self, product_id: int) -> None:
        await self.conn.execute(
            "UPDATE finance_products SET is_active=0 WHERE id=?", (product_id,)
        )
        await self.conn.commit()

    async def get_finance_product(self, product_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            "SELECT * FROM finance_products WHERE id=?", (product_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def record_finance_order(
        self,
        user_id: int,
        amount_stars: int,
        order_type: str,
        product_id: int | None = None,
        payload: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            """
            INSERT INTO finance_orders (user_id, product_id, order_type, amount_stars, payload, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (user_id, product_id, order_type, amount_stars, payload, now),
        )
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        fin_day = await self.get_cfg("finance_day", "")
        today_amt = int(await self.get_cfg("finance_today", "0"))
        if fin_day != today:
            today_amt = 0
            await self.set_cfg("finance_day", today)
        total = int(await self.get_cfg("finance_total", "0"))
        await self.set_cfg("finance_today", str(today_amt + amount_stars))
        await self.set_cfg("finance_total", str(total + amount_stars))
        await self.conn.commit()

    async def grant_access(self, user_id: int, days: int = 30) -> str:
        now = datetime.now(timezone.utc)
        cur = await self.conn.execute(
            "SELECT expires_at FROM user_access WHERE user_id=?", (user_id,)
        )
        row = await cur.fetchone()
        base = now
        if row and row[0]:
            current = datetime.fromisoformat(row[0])
            if current > now:
                base = current
        expires = (base + timedelta(days=days)).isoformat()
        await self.conn.execute(
            """
            INSERT INTO user_access (user_id, expires_at, granted_at, expiry_reminder_sent)
            VALUES (?,?,?,0)
            ON CONFLICT(user_id) DO UPDATE SET
                expires_at=excluded.expires_at,
                expiry_reminder_sent=0
            """,
            (user_id, expires, now.isoformat()),
        )
        subs = await self.count_paid_subscribers()
        await self.set_cfg("finance_subscribers", str(subs))
        await self.conn.commit()
        return expires

    async def get_access_expires_at(self, user_id: int) -> str | None:
        cur = await self.conn.execute(
            "SELECT expires_at FROM user_access WHERE user_id=?", (user_id,)
        )
        row = await cur.fetchone()
        return row[0] if row and row[0] else None

    async def get_access_days_remaining(self, user_id: int) -> int | None:
        expires = await self.get_access_expires_at(user_id)
        if not expires:
            return None
        delta = datetime.fromisoformat(expires) - datetime.now(timezone.utc)
        if delta.total_seconds() <= 0:
            return 0
        return delta.days + (1 if delta.seconds > 0 else 0)

    async def get_users_for_expiry_reminder(self, hours: int = 24) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(hours=hours)
        cur = await self.conn.execute(
            """
            SELECT user_id, expires_at FROM user_access
            WHERE expires_at > ?
              AND expires_at <= ?
              AND COALESCE(expiry_reminder_sent, 0) = 0
            """,
            (now.isoformat(), window_end.isoformat()),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def mark_expiry_reminder_sent(self, user_id: int) -> None:
        await self.conn.execute(
            "UPDATE user_access SET expiry_reminder_sent=1 WHERE user_id=?",
            (user_id,),
        )
        await self.conn.commit()

    async def count_paid_subscribers(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cur = await self.conn.execute(
            "SELECT COUNT(*) FROM user_access WHERE expires_at > ?", (now,)
        )
        return int((await cur.fetchone())[0])

    async def has_paid_access(self, user_id: int) -> bool:
        expires = await self.get_access_expires_at(user_id)
        if not expires:
            return False
        return datetime.fromisoformat(expires) > datetime.now(timezone.utc)

    # ── Inactive state ────────────────────────────────────────────────────────

    async def get_inactive_state(self, user_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            "SELECT * FROM user_inactive_state WHERE user_id=?", (user_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def set_inactive_reminder_sent(self, user_id: int, step: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            """
            INSERT INTO user_inactive_state (user_id, reminder_step, last_reminder_at)
            VALUES (?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET reminder_step=excluded.reminder_step, last_reminder_at=excluded.last_reminder_at
            """,
            (user_id, step, now),
        )
        sent = int(await self.get_cfg("inactive_sent", "0"))
        await self.set_cfg("inactive_sent", str(sent + 1))
        await self.conn.commit()

    async def get_users_for_inactive_check(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT user_id, last_active_at, created_at FROM users WHERE is_blocked=0"
        )
        return [dict(r) for r in await cur.fetchall()]

    async def get_inactive_reminder(self, reminder_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            "SELECT * FROM inactive_reminders WHERE id=?", (reminder_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    # ── Verification sessions ─────────────────────────────────────────────────

    async def save_verification_session(
        self, user_id: int, mode: str, challenge: str, expires_minutes: int = 30
    ) -> None:
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(minutes=expires_minutes)).isoformat()
        await self.conn.execute(
            """
            INSERT INTO verification_sessions (user_id, mode, challenge, created_at, expires_at)
            VALUES (?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                mode=excluded.mode, challenge=excluded.challenge,
                passed=0, created_at=excluded.created_at, expires_at=excluded.expires_at
            """,
            (user_id, mode, challenge, now.isoformat(), expires),
        )
        await self.conn.commit()

    async def get_verification_session(self, user_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute(
            "SELECT * FROM verification_sessions WHERE user_id=?", (user_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def mark_verification_passed(self, user_id: int) -> None:
        await self.conn.execute(
            "UPDATE verification_sessions SET passed=1 WHERE user_id=?", (user_id,)
        )
        await self.set_user_verified(user_id)
        await self.conn.commit()

    async def clear_verification_session(self, user_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM verification_sessions WHERE user_id=?", (user_id,)
        )
        await self.conn.commit()

    async def clean_stale_verifications(self, hours: int = 24) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        cur = await self.conn.execute(
            "DELETE FROM verification_sessions WHERE created_at < ? AND passed=0",
            (cutoff,),
        )
        await self.conn.execute(
            "DELETE FROM pending_users WHERE requested_at < ?", (cutoff,)
        )
        await self.conn.commit()
        return cur.rowcount


"""SQLite persistence for the web contributor portal (users, sessions, machines)."""

from __future__ import annotations

import secrets
import time
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS portal_users (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    auth_method TEXT NOT NULL,
    created_at REAL NOT NULL,
    last_seen REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS portal_sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    FOREIGN KEY(user_id) REFERENCES portal_users(id)
);

CREATE TABLE IF NOT EXISTS portal_machines (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    worker_name TEXT NOT NULL,
    scheduler_url TEXT NOT NULL,
    max_vram_mb INTEGER NOT NULL DEFAULT 0,
    max_cpu_percent REAL NOT NULL DEFAULT 50,
    dedicated_ram_mb INTEGER NOT NULL DEFAULT 0,
    dedicated_disk_mb INTEGER NOT NULL DEFAULT 0,
    dedicated_cpu_cores REAL NOT NULL DEFAULT 0,
    start_token TEXT NOT NULL UNIQUE,
    notes TEXT,
    created_at REAL NOT NULL,
    last_bootstrap_at REAL,
    FOREIGN KEY(user_id) REFERENCES portal_users(id)
);

CREATE TABLE IF NOT EXISTS portal_chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(user_id) REFERENCES portal_users(id)
);

CREATE TABLE IF NOT EXISTS portal_suggestions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'suggestion',
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(user_id) REFERENCES portal_users(id)
);

CREATE INDEX IF NOT EXISTS idx_portal_sessions_user ON portal_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_portal_machines_user ON portal_machines(user_id);
CREATE INDEX IF NOT EXISTS idx_portal_machines_token ON portal_machines(start_token);
CREATE INDEX IF NOT EXISTS idx_portal_chat_created ON portal_chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_portal_suggestions_created ON portal_suggestions(created_at);
"""

CHAT_RETENTION = 250
CHAT_BODY_MAX = 1000
SUGGESTION_BODY_MAX = 4000
SUGGESTION_CATEGORIES = frozenset({"suggestion", "bug", "review"})
SUGGESTION_STATUSES = frozenset({"open", "read", "done"})


class PortalStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if not self._db:
            raise RuntimeError("PortalStore not connected")
        return self._db

    async def upsert_user(self, display_name: str, auth_method: str) -> dict[str, Any]:
        now = time.time()
        name = display_name.strip()[:64]
        cur = await self.db.execute(
            "SELECT * FROM portal_users WHERE lower(display_name)=lower(?) LIMIT 1",
            (name,),
        )
        row = await cur.fetchone()
        if row:
            await self.db.execute(
                "UPDATE portal_users SET last_seen=?, auth_method=? WHERE id=?",
                (now, auth_method, row["id"]),
            )
            await self.db.commit()
            return await self.get_user(row["id"])  # type: ignore[return-value]
        user_id = str(uuid.uuid4())
        await self.db.execute(
            """
            INSERT INTO portal_users (id, display_name, auth_method, created_at, last_seen)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, name, auth_method, now, now),
        )
        await self.db.commit()
        return await self.get_user(user_id)  # type: ignore[return-value]

    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        cur = await self.db.execute("SELECT * FROM portal_users WHERE id=?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

    async def create_session(self, user_id: str, ttl_sec: int) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        await self.db.execute(
            """
            INSERT INTO portal_sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, now, now + ttl_sec),
        )
        await self.db.commit()
        return token

    async def get_session_user(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None
        now = time.time()
        cur = await self.db.execute(
            """
            SELECT u.* FROM portal_sessions s
            JOIN portal_users u ON u.id = s.user_id
            WHERE s.token=? AND s.expires_at > ?
            """,
            (token, now),
        )
        row = await cur.fetchone()
        if not row:
            return None
        await self.db.execute(
            "UPDATE portal_users SET last_seen=? WHERE id=?",
            (now, row["id"]),
        )
        await self.db.commit()
        return dict(row)

    async def delete_session(self, token: str) -> None:
        await self.db.execute("DELETE FROM portal_sessions WHERE token=?", (token,))
        await self.db.commit()

    async def create_machine(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        machine_id = str(uuid.uuid4())
        start_token = secrets.token_urlsafe(24)
        now = time.time()
        await self.db.execute(
            """
            INSERT INTO portal_machines (
                id, user_id, worker_name, scheduler_url, max_vram_mb, max_cpu_percent,
                dedicated_ram_mb, dedicated_disk_mb, dedicated_cpu_cores,
                start_token, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                machine_id,
                user_id,
                (data.get("worker_name") or "worker")[:80],
                (data.get("scheduler_url") or "").rstrip("/"),
                int(data.get("max_vram_mb") or 0),
                float(data.get("max_cpu_percent") or 50),
                int(data.get("dedicated_ram_mb") or 0),
                int(data.get("dedicated_disk_mb") or 0),
                float(data.get("dedicated_cpu_cores") or 0),
                start_token,
                data.get("notes"),
                now,
            ),
        )
        await self.db.commit()
        return await self.get_machine(machine_id)  # type: ignore[return-value]

    async def get_machine(self, machine_id: str) -> dict[str, Any] | None:
        cur = await self.db.execute("SELECT * FROM portal_machines WHERE id=?", (machine_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

    async def update_machine_caps(
        self, machine_id: str, user_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update dedication caps for a machine owned by ``user_id``.

        Returns the updated machine, or raises ``PermissionError`` if the machine
        exists but belongs to another user. Returns ``None`` if the machine id
        is unknown.
        """
        row = await self.get_machine(machine_id)
        if not row:
            return None
        if str(row.get("user_id") or "") != str(user_id):
            raise PermissionError("only the machine owner can change offer caps")
        max_vram = int(
            data["max_vram_mb"] if data.get("max_vram_mb") is not None else row["max_vram_mb"]
        )
        max_cpu = float(
            data["max_cpu_percent"]
            if data.get("max_cpu_percent") is not None
            else row["max_cpu_percent"]
        )
        ded_ram = int(
            data["dedicated_ram_mb"]
            if data.get("dedicated_ram_mb") is not None
            else row["dedicated_ram_mb"]
        )
        ded_disk = int(
            data["dedicated_disk_mb"]
            if data.get("dedicated_disk_mb") is not None
            else row["dedicated_disk_mb"]
        )
        ded_cpu = float(
            data["dedicated_cpu_cores"]
            if data.get("dedicated_cpu_cores") is not None
            else row["dedicated_cpu_cores"]
        )
        worker_name = row["worker_name"]
        if data.get("worker_name"):
            worker_name = str(data["worker_name"]).strip()[:80] or worker_name
        notes = row.get("notes")
        if "notes" in data:
            notes = data.get("notes")
        await self.db.execute(
            """
            UPDATE portal_machines SET
                worker_name=?,
                max_vram_mb=?,
                max_cpu_percent=?,
                dedicated_ram_mb=?,
                dedicated_disk_mb=?,
                dedicated_cpu_cores=?,
                notes=?
            WHERE id=? AND user_id=?
            """,
            (
                worker_name,
                max_vram,
                max_cpu,
                ded_ram,
                ded_disk,
                ded_cpu,
                notes,
                machine_id,
                user_id,
            ),
        )
        await self.db.commit()
        return await self.get_machine(machine_id)

    async def list_machines(self, user_id: str | None = None) -> list[dict[str, Any]]:
        if user_id:
            cur = await self.db.execute(
                "SELECT * FROM portal_machines WHERE user_id=? ORDER BY created_at DESC",
                (user_id,),
            )
        else:
            cur = await self.db.execute(
                "SELECT * FROM portal_machines ORDER BY created_at DESC"
            )
        return [dict(r) for r in await cur.fetchall()]

    async def bootstrap_token(self, start_token: str) -> dict[str, Any] | None:
        cur = await self.db.execute(
            "SELECT * FROM portal_machines WHERE start_token=?",
            (start_token,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        await self.db.execute(
            "UPDATE portal_machines SET last_bootstrap_at=? WHERE id=?",
            (time.time(), row["id"]),
        )
        user = await self.get_user(row["user_id"])
        await self.db.commit()
        machine = dict(row)
        machine["contributor_name"] = (user or {}).get("display_name") or ""
        machine["discord_user"] = (user or {}).get("display_name") or ""
        return machine

    async def list_recent_users(self, within_sec: int = 300) -> list[dict[str, Any]]:
        """Users with portal activity in the last ``within_sec`` seconds."""
        cutoff = time.time() - max(30, within_sec)
        cur = await self.db.execute(
            """
            SELECT id, display_name, auth_method, last_seen
            FROM portal_users
            WHERE last_seen >= ?
            ORDER BY last_seen DESC
            LIMIT 40
            """,
            (cutoff,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def add_chat_message(self, user_id: str, display_name: str, body: str) -> dict[str, Any]:
        text = (body or "").strip()
        if not text:
            raise ValueError("message body required")
        if len(text) > CHAT_BODY_MAX:
            text = text[:CHAT_BODY_MAX]
        name = (display_name or "member").strip()[:64] or "member"
        now = time.time()
        cur = await self.db.execute(
            """
            INSERT INTO portal_chat_messages (user_id, display_name, body, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, name, text, now),
        )
        await self.db.commit()
        msg_id = int(cur.lastrowid or 0)
        # Cap retention — keep newest N
        await self.db.execute(
            """
            DELETE FROM portal_chat_messages
            WHERE id NOT IN (
                SELECT id FROM portal_chat_messages ORDER BY id DESC LIMIT ?
            )
            """,
            (CHAT_RETENTION,),
        )
        await self.db.commit()
        return {
            "id": msg_id,
            "user_id": user_id,
            "display_name": name,
            "body": text,
            "created_at": now,
        }

    async def list_chat_messages(
        self, *, since_id: int = 0, limit: int = 80
    ) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit or 80), 200))
        if since_id > 0:
            cur = await self.db.execute(
                """
                SELECT id, user_id, display_name, body, created_at
                FROM portal_chat_messages
                WHERE id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (int(since_id), lim),
            )
        else:
            cur = await self.db.execute(
                """
                SELECT id, user_id, display_name, body, created_at
                FROM portal_chat_messages
                ORDER BY id DESC
                LIMIT ?
                """,
                (lim,),
            )
            rows = [dict(r) for r in await cur.fetchall()]
            rows.reverse()
            return rows
        return [dict(r) for r in await cur.fetchall()]

    async def add_suggestion(
        self, user_id: str, display_name: str, body: str, category: str = "suggestion"
    ) -> dict[str, Any]:
        text = (body or "").strip()
        if not text:
            raise ValueError("suggestion body required")
        if len(text) > SUGGESTION_BODY_MAX:
            text = text[:SUGGESTION_BODY_MAX]
        cat = (category or "suggestion").strip().lower()
        if cat not in SUGGESTION_CATEGORIES:
            cat = "suggestion"
        name = (display_name or "member").strip()[:64] or "member"
        now = time.time()
        sid = str(uuid.uuid4())
        await self.db.execute(
            """
            INSERT INTO portal_suggestions (
                id, user_id, display_name, category, body, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
            """,
            (sid, user_id, name, cat, text, now, now),
        )
        await self.db.commit()
        return await self.get_suggestion(sid)  # type: ignore[return-value]

    async def get_suggestion(self, suggestion_id: str) -> dict[str, Any] | None:
        cur = await self.db.execute(
            "SELECT * FROM portal_suggestions WHERE id=?",
            (suggestion_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def list_suggestions(
        self, *, status: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit or 100), 300))
        if status and status in SUGGESTION_STATUSES:
            cur = await self.db.execute(
                """
                SELECT * FROM portal_suggestions
                WHERE status=?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (status, lim),
            )
        else:
            cur = await self.db.execute(
                """
                SELECT * FROM portal_suggestions
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (lim,),
            )
        return [dict(r) for r in await cur.fetchall()]

    async def set_suggestion_status(
        self, suggestion_id: str, status: str
    ) -> dict[str, Any] | None:
        st = (status or "").strip().lower()
        if st not in SUGGESTION_STATUSES:
            raise ValueError(f"status must be one of {sorted(SUGGESTION_STATUSES)}")
        row = await self.get_suggestion(suggestion_id)
        if not row:
            return None
        now = time.time()
        await self.db.execute(
            "UPDATE portal_suggestions SET status=?, updated_at=? WHERE id=?",
            (st, now, suggestion_id),
        )
        await self.db.commit()
        return await self.get_suggestion(suggestion_id)

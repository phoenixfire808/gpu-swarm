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

CREATE INDEX IF NOT EXISTS idx_portal_sessions_user ON portal_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_portal_machines_user ON portal_machines(user_id);
CREATE INDEX IF NOT EXISTS idx_portal_machines_token ON portal_machines(start_token);
"""


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

"""SQLite persistence for workers and jobs."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS workers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    discord_user TEXT,
    host TEXT,
    gpus_json TEXT NOT NULL DEFAULT '[]',
    free_vram_mb INTEGER NOT NULL DEFAULT 0,
    total_vram_mb INTEGER NOT NULL DEFAULT 0,
    max_vram_mb INTEGER NOT NULL DEFAULT 0,
    max_cpu_percent REAL NOT NULL DEFAULT 50,
    cpu_cores INTEGER NOT NULL DEFAULT 0,
    ram_total_mb INTEGER NOT NULL DEFAULT 0,
    ram_available_mb INTEGER NOT NULL DEFAULT 0,
    max_ram_mb INTEGER NOT NULL DEFAULT 0,
    disk_free_mb INTEGER NOT NULL DEFAULT 0,
    disk_total_mb INTEGER NOT NULL DEFAULT 0,
    disk_path TEXT,
    max_disk_mb INTEGER NOT NULL DEFAULT 0,
    dedicated_ram_mb INTEGER NOT NULL DEFAULT 0,
    dedicated_disk_mb INTEGER NOT NULL DEFAULT 0,
    dedicated_cpu_cores REAL NOT NULL DEFAULT 0,
    contributor_name TEXT,
    status TEXT NOT NULL DEFAULT 'online',
    last_heartbeat REAL NOT NULL,
    registered_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'queued',
    require_gpu INTEGER NOT NULL DEFAULT 0,
    min_vram_mb INTEGER NOT NULL DEFAULT 0,
    submitted_by TEXT,
    worker_id TEXT,
    result_json TEXT,
    error TEXT,
    created_at REAL NOT NULL,
    leased_at REAL,
    completed_at REAL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_workers_heartbeat ON workers(last_heartbeat);
"""

# Columns added after initial deploy — applied via ALTER for existing DBs.
_WORKER_MIGRATIONS: list[tuple[str, str]] = [
    ("cpu_cores", "ALTER TABLE workers ADD COLUMN cpu_cores INTEGER NOT NULL DEFAULT 0"),
    ("ram_total_mb", "ALTER TABLE workers ADD COLUMN ram_total_mb INTEGER NOT NULL DEFAULT 0"),
    (
        "ram_available_mb",
        "ALTER TABLE workers ADD COLUMN ram_available_mb INTEGER NOT NULL DEFAULT 0",
    ),
    ("max_ram_mb", "ALTER TABLE workers ADD COLUMN max_ram_mb INTEGER NOT NULL DEFAULT 0"),
    ("disk_free_mb", "ALTER TABLE workers ADD COLUMN disk_free_mb INTEGER NOT NULL DEFAULT 0"),
    ("disk_total_mb", "ALTER TABLE workers ADD COLUMN disk_total_mb INTEGER NOT NULL DEFAULT 0"),
    ("disk_path", "ALTER TABLE workers ADD COLUMN disk_path TEXT"),
    ("max_disk_mb", "ALTER TABLE workers ADD COLUMN max_disk_mb INTEGER NOT NULL DEFAULT 0"),
    ("dedicated_ram_mb", "ALTER TABLE workers ADD COLUMN dedicated_ram_mb INTEGER NOT NULL DEFAULT 0"),
    ("dedicated_disk_mb", "ALTER TABLE workers ADD COLUMN dedicated_disk_mb INTEGER NOT NULL DEFAULT 0"),
    (
        "dedicated_cpu_cores",
        "ALTER TABLE workers ADD COLUMN dedicated_cpu_cores REAL NOT NULL DEFAULT 0",
    ),
    ("contributor_name", "ALTER TABLE workers ADD COLUMN contributor_name TEXT"),
    ("llm_ready", "ALTER TABLE workers ADD COLUMN llm_ready INTEGER NOT NULL DEFAULT 0"),
]


class Store:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._migrate_workers()
        await self._db.commit()

    async def _migrate_workers(self) -> None:
        cur = await self.db.execute("PRAGMA table_info(workers)")
        cols = {row[1] for row in await cur.fetchall()}
        for name, sql in _WORKER_MIGRATIONS:
            if name not in cols:
                await self.db.execute(sql)

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if not self._db:
            raise RuntimeError("Store not connected")
        return self._db

    async def register_worker(self, data: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        worker_id = data.get("id") or str(uuid.uuid4())
        gpus = data.get("gpus") or []
        free = int(data.get("free_vram_mb") or sum(g.get("memory_free_mb", 0) for g in gpus))
        total = int(data.get("total_vram_mb") or sum(g.get("memory_total_mb", 0) for g in gpus))
        max_ram = int(data.get("max_ram_mb") or data.get("dedicated_ram_mb") or 0)
        max_disk = int(data.get("max_disk_mb") or data.get("dedicated_disk_mb") or 0)
        ded_ram = int(data.get("dedicated_ram_mb") or max_ram or 0)
        ded_disk = int(data.get("dedicated_disk_mb") or max_disk or 0)
        await self.db.execute(
            """
            INSERT INTO workers (
                id, name, discord_user, host, gpus_json, free_vram_mb, total_vram_mb,
                max_vram_mb, max_cpu_percent,
                cpu_cores, ram_total_mb, ram_available_mb, max_ram_mb,
                disk_free_mb, disk_total_mb, disk_path, max_disk_mb,
                dedicated_ram_mb, dedicated_disk_mb, dedicated_cpu_cores, contributor_name,
                llm_ready,
                status, last_heartbeat, registered_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'online', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                discord_user=excluded.discord_user,
                host=excluded.host,
                gpus_json=excluded.gpus_json,
                free_vram_mb=excluded.free_vram_mb,
                total_vram_mb=excluded.total_vram_mb,
                max_vram_mb=excluded.max_vram_mb,
                max_cpu_percent=excluded.max_cpu_percent,
                cpu_cores=excluded.cpu_cores,
                ram_total_mb=excluded.ram_total_mb,
                ram_available_mb=excluded.ram_available_mb,
                max_ram_mb=excluded.max_ram_mb,
                disk_free_mb=excluded.disk_free_mb,
                disk_total_mb=excluded.disk_total_mb,
                disk_path=excluded.disk_path,
                max_disk_mb=excluded.max_disk_mb,
                dedicated_ram_mb=excluded.dedicated_ram_mb,
                dedicated_disk_mb=excluded.dedicated_disk_mb,
                dedicated_cpu_cores=excluded.dedicated_cpu_cores,
                contributor_name=excluded.contributor_name,
                llm_ready=excluded.llm_ready,
                status='online',
                last_heartbeat=excluded.last_heartbeat
            """,
            (
                worker_id,
                data.get("name") or "worker",
                data.get("discord_user"),
                data.get("host"),
                json.dumps(gpus),
                free,
                total,
                int(data.get("max_vram_mb") or 0),
                float(data.get("max_cpu_percent") if data.get("max_cpu_percent") is not None else 50),
                int(data.get("cpu_cores") or 0),
                int(data.get("ram_total_mb") or 0),
                int(data.get("ram_available_mb") or 0),
                max_ram,
                int(data.get("disk_free_mb") or 0),
                int(data.get("disk_total_mb") or 0),
                data.get("disk_path"),
                max_disk,
                ded_ram,
                ded_disk,
                float(data.get("dedicated_cpu_cores") or 0),
                data.get("contributor_name"),
                1 if data.get("llm_ready") else 0,
                now,
                now,
            ),
        )
        await self.db.commit()
        return await self.get_worker(worker_id)  # type: ignore[return-value]

    async def heartbeat(self, worker_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        row = await self.get_worker(worker_id)
        if not row:
            return None
        gpus = data.get("gpus")
        free = data.get("free_vram_mb")
        total = data.get("total_vram_mb")
        status = data.get("status") or "online"
        if gpus is None:
            gpus_json = json.dumps(row.get("gpus") or [])
            free = free if free is not None else row["free_vram_mb"]
            total = total if total is not None else row["total_vram_mb"]
        else:
            gpus_json = json.dumps(gpus)
            free = int(free if free is not None else sum(g.get("memory_free_mb", 0) for g in gpus))
            total = int(total if total is not None else sum(g.get("memory_total_mb", 0) for g in gpus))

        # Host metrics: keep previous values when older workers omit fields
        cpu_cores = data.get("cpu_cores")
        ram_total = data.get("ram_total_mb")
        ram_avail = data.get("ram_available_mb")
        max_vram = data.get("max_vram_mb")
        max_ram = data.get("max_ram_mb")
        if max_ram is None and data.get("dedicated_ram_mb") is not None:
            max_ram = data.get("dedicated_ram_mb")
        disk_free = data.get("disk_free_mb")
        disk_total = data.get("disk_total_mb")
        disk_path = data.get("disk_path")
        max_disk = data.get("max_disk_mb")
        if max_disk is None and data.get("dedicated_disk_mb") is not None:
            max_disk = data.get("dedicated_disk_mb")
        max_cpu = data.get("max_cpu_percent")
        ded_ram = data.get("dedicated_ram_mb")
        ded_disk = data.get("dedicated_disk_mb")
        ded_cpu = data.get("dedicated_cpu_cores")
        contributor = data.get("contributor_name")
        llm_ready = data.get("llm_ready")

        await self.db.execute(
            """
            UPDATE workers SET
                gpus_json=?, free_vram_mb=?, total_vram_mb=?, status=?, last_heartbeat=?,
                cpu_cores=COALESCE(?, cpu_cores),
                ram_total_mb=COALESCE(?, ram_total_mb),
                ram_available_mb=COALESCE(?, ram_available_mb),
                max_vram_mb=COALESCE(?, max_vram_mb),
                max_ram_mb=COALESCE(?, max_ram_mb),
                disk_free_mb=COALESCE(?, disk_free_mb),
                disk_total_mb=COALESCE(?, disk_total_mb),
                disk_path=COALESCE(?, disk_path),
                max_disk_mb=COALESCE(?, max_disk_mb),
                max_cpu_percent=COALESCE(?, max_cpu_percent),
                dedicated_ram_mb=COALESCE(?, dedicated_ram_mb),
                dedicated_disk_mb=COALESCE(?, dedicated_disk_mb),
                dedicated_cpu_cores=COALESCE(?, dedicated_cpu_cores),
                contributor_name=COALESCE(?, contributor_name),
                llm_ready=COALESCE(?, llm_ready)
            WHERE id=?
            """,
            (
                gpus_json,
                int(free),
                int(total),
                status,
                time.time(),
                int(cpu_cores) if cpu_cores is not None else None,
                int(ram_total) if ram_total is not None else None,
                int(ram_avail) if ram_avail is not None else None,
                int(max_vram) if max_vram is not None else None,
                int(max_ram) if max_ram is not None else None,
                int(disk_free) if disk_free is not None else None,
                int(disk_total) if disk_total is not None else None,
                disk_path,
                int(max_disk) if max_disk is not None else None,
                float(max_cpu) if max_cpu is not None else None,
                int(ded_ram) if ded_ram is not None else None,
                int(ded_disk) if ded_disk is not None else None,
                float(ded_cpu) if ded_cpu is not None else None,
                contributor,
                (1 if llm_ready else 0) if llm_ready is not None else None,
                worker_id,
            ),
        )
        await self.db.commit()
        return await self.get_worker(worker_id)

    async def get_worker(self, worker_id: str) -> dict[str, Any] | None:
        cur = await self.db.execute("SELECT * FROM workers WHERE id=?", (worker_id,))
        row = await cur.fetchone()
        return _worker_row(row) if row else None

    async def list_workers(self, stale_sec: int = 45) -> list[dict[str, Any]]:
        now = time.time()
        cur = await self.db.execute("SELECT * FROM workers ORDER BY last_heartbeat DESC")
        rows = await cur.fetchall()
        out = []
        for row in rows:
            w = _worker_row(row)
            age = now - float(w["last_heartbeat"])
            w["online"] = age <= stale_sec and w["status"] != "stopped"
            w["heartbeat_age_sec"] = round(age, 1)
            out.append(w)
        return out

    async def submit_job(self, data: dict[str, Any]) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = time.time()
        await self.db.execute(
            """
            INSERT INTO jobs (
                id, job_type, payload_json, status, require_gpu, min_vram_mb,
                submitted_by, created_at
            ) VALUES (?, ?, ?, 'queued', ?, ?, ?, ?)
            """,
            (
                job_id,
                data["job_type"],
                json.dumps(data.get("payload") or {}),
                1 if data.get("require_gpu") else 0,
                int(data.get("min_vram_mb") or 0),
                data.get("submitted_by"),
                now,
            ),
        )
        await self.db.commit()
        return await self.get_job(job_id)  # type: ignore[return-value]

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        cur = await self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        row = await cur.fetchone()
        return _job_row(row) if row else None

    async def lease_job(self, worker_id: str, caps: dict[str, Any]) -> dict[str, Any] | None:
        worker = await self.get_worker(worker_id)
        if not worker:
            return None
        free_vram = int(caps.get("free_vram_mb", worker["free_vram_mb"]))
        # Never schedule beyond the worker's own advertised soft cap.
        worker_max_vram = int(worker.get("max_vram_mb") or 0)
        if worker_max_vram > 0:
            free_vram = min(free_vram, worker_max_vram)
        has_gpu = bool(caps.get("has_gpu", bool(worker.get("gpus"))))
        llm_ready = bool(caps.get("llm_ready"))
        ram_avail = int(
            caps.get("ram_available_mb", worker.get("ram_available_mb") or 0)
        )
        worker_max_ram = int(worker.get("max_ram_mb") or worker.get("dedicated_ram_mb") or 0)
        if worker_max_ram > 0:
            ram_avail = min(ram_avail, worker_max_ram)
        disk_free = int(caps.get("disk_free_mb", worker.get("disk_free_mb") or 0))
        worker_max_disk = int(worker.get("max_disk_mb") or worker.get("dedicated_disk_mb") or 0)
        if worker_max_disk > 0:
            disk_free = min(disk_free, worker_max_disk)
        cur = await self.db.execute(
            """
            SELECT * FROM jobs
            WHERE status='queued'
              AND (require_gpu=0 OR (?=1 AND min_vram_mb <= ?))
            ORDER BY created_at ASC
            LIMIT 8
            """,
            (1 if has_gpu else 0, free_vram),
        )
        rows = await cur.fetchall()
        if not rows:
            return None
        chosen = None
        for row in rows:
            jtype = str(row["job_type"] or "")
            if jtype == "llm_chat" and not llm_ready:
                continue
            job_preview = _job_row(row)
            payload = job_preview.get("payload") or {}
            # Ignore/skip jobs that demand more RAM/disk than this worker offers.
            min_ram = int(payload.get("min_ram_mb") or payload.get("required_ram_mb") or 0)
            min_disk = int(payload.get("min_disk_mb") or payload.get("required_disk_mb") or 0)
            if min_ram > 0 and ram_avail > 0 and min_ram > ram_avail:
                continue
            if min_disk > 0 and disk_free > 0 and min_disk > disk_free:
                continue
            if worker_max_vram > 0 and int(job_preview.get("min_vram_mb") or 0) > worker_max_vram:
                continue
            chosen = row
            break
        if not chosen:
            return None
        job_id = chosen["id"]
        now = time.time()
        await self.db.execute(
            """
            UPDATE jobs SET status='running', worker_id=?, leased_at=?
            WHERE id=? AND status='queued'
            """,
            (worker_id, now, job_id),
        )
        await self.db.commit()
        job = await self.get_job(job_id)
        if job and job["status"] == "running" and job["worker_id"] == worker_id:
            await self.db.execute(
                "UPDATE workers SET status='busy', last_heartbeat=? WHERE id=?",
                (now, worker_id),
            )
            await self.db.commit()
            return job
        return None

    async def complete_job(self, job_id: str, worker_id: str, result: Any) -> dict[str, Any] | None:
        job = await self.get_job(job_id)
        if not job or job["worker_id"] != worker_id:
            return None
        await self.db.execute(
            """
            UPDATE jobs SET status='completed', result_json=?, error=NULL, completed_at=?
            WHERE id=?
            """,
            (json.dumps(result), time.time(), job_id),
        )
        await self.db.execute(
            "UPDATE workers SET status='online', last_heartbeat=? WHERE id=?",
            (time.time(), worker_id),
        )
        await self.db.commit()
        return await self.get_job(job_id)

    async def fail_job(self, job_id: str, worker_id: str, error: str) -> dict[str, Any] | None:
        job = await self.get_job(job_id)
        if not job or job["worker_id"] != worker_id:
            return None
        await self.db.execute(
            """
            UPDATE jobs SET status='failed', error=?, completed_at=?
            WHERE id=?
            """,
            (error[:4000], time.time(), job_id),
        )
        await self.db.execute(
            "UPDATE workers SET status='online', last_heartbeat=? WHERE id=?",
            (time.time(), worker_id),
        )
        await self.db.commit()
        return await self.get_job(job_id)

    async def status_summary(self, stale_sec: int = 45) -> dict[str, Any]:
        workers = await self.list_workers(stale_sec)
        online = [w for w in workers if w["online"]]
        accepting = [
            w
            for w in online
            if str(w.get("status") or "").lower() in ("online", "busy")
        ]
        cur = await self.db.execute(
            """
            SELECT status, COUNT(*) AS n FROM jobs GROUP BY status
            """
        )
        counts = {row["status"]: row["n"] for row in await cur.fetchall()}
        gpu_names: list[str] = []
        for w in accepting:
            for g in w.get("gpus") or []:
                name = g.get("name")
                if name:
                    gpu_names.append(f"{w['name']}: {name}")
        return {
            "workers_total": len(workers),
            "workers_online": len(accepting),
            "workers_registered": len(online),
            "free_vram_mb": sum(int(w.get("free_vram_mb") or 0) for w in accepting),
            "total_vram_mb": sum(int(w.get("total_vram_mb") or 0) for w in accepting),
            "cpu_cores": sum(int(w.get("cpu_cores") or 0) for w in accepting),
            "ram_available_mb": sum(int(w.get("ram_available_mb") or 0) for w in accepting),
            "ram_total_mb": sum(int(w.get("ram_total_mb") or 0) for w in accepting),
            "disk_free_mb": sum(int(w.get("disk_free_mb") or 0) for w in accepting),
            "dedicated_ram_mb": sum(int(w.get("dedicated_ram_mb") or 0) for w in accepting),
            "dedicated_disk_mb": sum(int(w.get("dedicated_disk_mb") or 0) for w in accepting),
            "dedicated_cpu_cores": round(
                sum(float(w.get("dedicated_cpu_cores") or 0) for w in accepting), 2
            ),
            "gpus": gpu_names,
            "jobs": {
                "queued": counts.get("queued", 0),
                "running": counts.get("running", 0),
                "completed": counts.get("completed", 0),
                "failed": counts.get("failed", 0),
            },
            "workers": online,
            "workers_accepting_jobs": accepting,
        }


def _worker_row(row: aiosqlite.Row) -> dict[str, Any]:
    d = dict(row)
    try:
        d["gpus"] = json.loads(d.pop("gpus_json") or "[]")
    except json.JSONDecodeError:
        d["gpus"] = []
        d.pop("gpus_json", None)
    for key, default in (
        ("cpu_cores", 0),
        ("ram_total_mb", 0),
        ("ram_available_mb", 0),
        ("max_ram_mb", 0),
        ("disk_free_mb", 0),
        ("disk_total_mb", 0),
        ("max_disk_mb", 0),
        ("dedicated_ram_mb", 0),
        ("dedicated_disk_mb", 0),
        ("dedicated_cpu_cores", 0.0),
    ):
        d.setdefault(key, default)
    d.setdefault("disk_path", None)
    d.setdefault("contributor_name", None)
    d["llm_ready"] = bool(d.get("llm_ready"))
    # Keep portal aliases populated even if only max_* was stored
    if not d.get("dedicated_ram_mb") and d.get("max_ram_mb"):
        d["dedicated_ram_mb"] = d["max_ram_mb"]
    if not d.get("dedicated_disk_mb") and d.get("max_disk_mb"):
        d["dedicated_disk_mb"] = d["max_disk_mb"]
    return d


def _job_row(row: aiosqlite.Row) -> dict[str, Any]:
    d = dict(row)
    try:
        d["payload"] = json.loads(d.pop("payload_json") or "{}")
    except json.JSONDecodeError:
        d["payload"] = {}
        d.pop("payload_json", None)
    result_raw = d.pop("result_json", None)
    if result_raw:
        try:
            d["result"] = json.loads(result_raw)
        except json.JSONDecodeError:
            d["result"] = result_raw
    else:
        d["result"] = None
    d["require_gpu"] = bool(d.get("require_gpu"))
    return d

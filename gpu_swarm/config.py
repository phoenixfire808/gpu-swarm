"""Shared configuration loaded from env / .env."""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    raw = _env(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = _env(key)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass
class SchedulerConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    db_path: Path = ROOT / "data" / "swarm.db"
    worker_stale_sec: int = 45


@dataclass
class WorkerConfig:
    scheduler_url: str = "http://127.0.0.1:8766"
    worker_name: str = ""
    max_vram_mb: int = 0  # 0 = no soft cap beyond free VRAM
    max_cpu_percent: float = 50.0
    max_ram_mb: int = 0  # capacity ad (not a distributed RAM pool yet)
    max_disk_mb: int = 0  # capacity ad (not a distributed filesystem yet)
    dedicated_cpu_cores: float = 0.0
    discord_user: str = ""
    contributor_name: str = ""
    heartbeat_sec: float = 10.0
    poll_sec: float = 2.0
    preferred_gpu: int | None = None
    start_token: str = ""
    portal_url: str = "http://127.0.0.1:8767"


@dataclass
class PortalConfig:
    host: str = "0.0.0.0"
    port: int = 8767
    db_path: Path = ROOT / "data" / "portal.db"
    scheduler_url: str = "http://127.0.0.1:8766"
    pool_password: str = ""
    invite_codes: tuple[str, ...] = ()
    session_ttl_sec: int = 60 * 60 * 24 * 14
    public_url: str = ""


def scheduler_config() -> SchedulerConfig:
    db = _env("GPU_SWARM_DB") or str(ROOT / "data" / "swarm.db")
    return SchedulerConfig(
        host=_env("GPU_SWARM_HOST", "127.0.0.1") or "127.0.0.1",
        port=_env_int("GPU_SWARM_PORT", 8766),
        db_path=Path(db),
        worker_stale_sec=_env_int("GPU_SWARM_WORKER_STALE_SEC", 45),
    )


def worker_config() -> WorkerConfig:
    name = _env("GPU_SWARM_WORKER_NAME") or f"{socket.gethostname()}-gpu"
    pref = _env("GPU_SWARM_PREFERRED_GPU")
    preferred: int | None = None
    if pref != "":
        try:
            preferred = int(pref)
        except ValueError:
            preferred = None
    # Accept dedicated_* aliases from portal-generated env
    ram = _env_int("GPU_SWARM_MAX_RAM_MB", 0) or _env_int("GPU_SWARM_DEDICATED_RAM_MB", 0)
    disk = _env_int("GPU_SWARM_MAX_DISK_MB", 0) or _env_int("GPU_SWARM_DEDICATED_DISK_MB", 0)
    if disk <= 0:
        # Desktop joiner uses GB; convert to MB for the worker soft cap
        disk_gb = _env_float("GPU_SWARM_MAX_DISK_GB", 0.0)
        if disk_gb > 0:
            disk = int(disk_gb * 1024)
    return WorkerConfig(
        scheduler_url=_env("GPU_SWARM_SCHEDULER_URL", "http://127.0.0.1:8766")
        or "http://127.0.0.1:8766",
        worker_name=name,
        max_vram_mb=_env_int("GPU_SWARM_MAX_VRAM_MB", 0),
        max_cpu_percent=_env_float("GPU_SWARM_MAX_CPU_PERCENT", 50.0),
        max_ram_mb=ram,
        max_disk_mb=disk,
        dedicated_cpu_cores=_env_float("GPU_SWARM_DEDICATED_CPU_CORES", 0.0),
        discord_user=_env("GPU_SWARM_DISCORD_USER"),
        contributor_name=_env("GPU_SWARM_CONTRIBUTOR_NAME"),
        heartbeat_sec=_env_float("GPU_SWARM_HEARTBEAT_SEC", 10.0),
        poll_sec=_env_float("GPU_SWARM_POLL_SEC", 2.0),
        preferred_gpu=preferred,
        start_token=_env("GPU_SWARM_START_TOKEN"),
        portal_url=_env("GPU_SWARM_PORTAL_URL", "http://127.0.0.1:8767")
        or "http://127.0.0.1:8767",
    )


def portal_config() -> PortalConfig:
    codes_raw = _env("GPU_SWARM_INVITE_CODES")
    codes = tuple(c.strip() for c in codes_raw.split(",") if c.strip()) if codes_raw else ()
    db = _env("GPU_SWARM_PORTAL_DB") or str(ROOT / "data" / "portal.db")
    sched = (_env("GPU_SWARM_SCHEDULER_URL") or "http://127.0.0.1:8766").rstrip("/")
    return PortalConfig(
        host=_env("GPU_SWARM_PORTAL_HOST", "0.0.0.0") or "0.0.0.0",
        port=_env_int("GPU_SWARM_PORTAL_PORT", 8767),
        db_path=Path(db),
        scheduler_url=sched,
        pool_password=_env("GPU_SWARM_POOL_PASSWORD"),
        invite_codes=codes,
        session_ttl_sec=_env_int("GPU_SWARM_PORTAL_SESSION_TTL_SEC", 60 * 60 * 24 * 14),
        public_url=_env("GPU_SWARM_PORTAL_PUBLIC_URL"),
    )


def discord_token() -> str:
    return _env("DISCORD_BOT_TOKEN")

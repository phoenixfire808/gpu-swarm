"""Real host resource inventory (CPU / RAM / disk). No mocks."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from gpu_swarm.config import ROOT


def _work_dir() -> Path:
    """Directory whose drive free-space we advertise (worker work / project root)."""
    override = os.environ.get("GPU_SWARM_WORK_DIR", "").strip()
    if override:
        return Path(override)
    return ROOT


def query_host() -> dict[str, Any]:
    """
    Live host metrics for worker advertise / heartbeat.

    Stable JSON field names (portal / desktop / Discord consumers):
      cpu_cores, ram_total_mb, ram_available_mb, disk_free_mb, disk_path
    """
    try:
        import psutil
    except ImportError as exc:
        raise RuntimeError(
            "psutil is required for host metrics (pip install psutil)"
        ) from exc

    cores = int(psutil.cpu_count(logical=True) or 0)
    mem = psutil.virtual_memory()
    ram_total_mb = int(mem.total // (1024 * 1024))
    ram_available_mb = int(mem.available // (1024 * 1024))

    work = _work_dir()
    try:
        work.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    usage = psutil.disk_usage(str(work))
    disk_free_mb = int(usage.free // (1024 * 1024))
    disk_total_mb = int(usage.total // (1024 * 1024))

    return {
        "cpu_cores": cores,
        "ram_total_mb": ram_total_mb,
        "ram_available_mb": ram_available_mb,
        "disk_free_mb": disk_free_mb,
        "disk_total_mb": disk_total_mb,
        "disk_path": str(work.resolve()),
    }

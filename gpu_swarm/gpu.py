"""Real GPU inventory via nvidia-smi (no mocks). CPU-only hosts return empty inventory."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any


def nvidia_smi_available() -> bool:
    return shutil.which("nvidia-smi") is not None


def query_gpus() -> list[dict[str, Any]]:
    """Return live GPU inventory from nvidia-smi. Empty list if unavailable (CPU-only OK)."""
    if not nvidia_smi_available():
        return []
    query = (
        "index,name,uuid,memory.total,memory.free,memory.used,"
        "utilization.gpu,utilization.memory,temperature.gpu,driver_version"
    )
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={query}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    gpus: list[dict[str, Any]] = []
    for line in proc.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 10:
            continue
        gpus.append(
            {
                "index": int(parts[0]),
                "name": parts[1],
                "uuid": parts[2],
                "memory_total_mb": _num(parts[3]),
                "memory_free_mb": _num(parts[4]),
                "memory_used_mb": _num(parts[5]),
                "utilization_gpu_pct": _num(parts[6]),
                "utilization_memory_pct": _num(parts[7]),
                "temperature_c": _num(parts[8]),
                "driver_version": parts[9],
            }
        )
    return gpus


def inventory_summary() -> dict[str, Any]:
    """Advertise GPUs when present; otherwise cpu-only with gpu_available=false."""
    smi = nvidia_smi_available()
    gpus = query_gpus()
    gpu_count = len(gpus)
    return {
        "gpus": gpus,
        "gpu_count": gpu_count,
        "free_vram_mb": sum(g["memory_free_mb"] for g in gpus),
        "total_vram_mb": sum(g["memory_total_mb"] for g in gpus),
        "names": [g["name"] for g in gpus],
        "nvidia_smi": smi,
        "gpu_available": gpu_count > 0,
        "has_gpu": gpu_count > 0,
        "mode": "gpu" if gpu_count > 0 else "cpu-only",
    }


def _num(raw: str) -> int:
    try:
        return int(float(raw))
    except ValueError:
        return 0

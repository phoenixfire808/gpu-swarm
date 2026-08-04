"""Persistent settings for the GPU Pool desktop joiner app."""

from __future__ import annotations

import json
import os
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from gpu_swarm.config import ROOT

SETTINGS_PATH = ROOT / "data" / "joiner_settings.json"
DEFAULT_SCHEDULER_URL = "http://100.85.165.84:8766"
DEFAULT_LOCAL_SCHEDULER_URL = "http://127.0.0.1:8766"
DEFAULT_PORTAL_URL = "http://100.85.165.84:8767/portal"
AGENT_VMS_DEFAULT = Path(r"C:\Users\Drew\Projects\agent-vms")


@dataclass
class JoinerSettings:
    scheduler_url: str = DEFAULT_SCHEDULER_URL
    worker_name: str = ""
    discord_user: str = ""
    max_vram_mb: int = 0
    max_cpu_percent: float = 50.0
    max_ram_mb: int = 0  # 0 = advertise detected free/soft-unbounded
    max_disk_gb: float = 0.0  # SSD/HDD contribution soft cap
    portal_url: str = DEFAULT_PORTAL_URL
    wizard_completed: bool = False
    agent_vms_path: str = str(AGENT_VMS_DEFAULT)

    def __post_init__(self) -> None:
        if not self.worker_name:
            self.worker_name = f"{socket.gethostname()}-gpu"


def load_settings() -> JoinerSettings:
    if not SETTINGS_PATH.exists():
        return JoinerSettings()
    try:
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return JoinerSettings()
    if not isinstance(raw, dict):
        return JoinerSettings()
    base = JoinerSettings()
    data = asdict(base)
    for key in data:
        if key in raw:
            data[key] = raw[key]
    return JoinerSettings(**data)


def save_settings(settings: JoinerSettings) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(asdict(settings), indent=2) + "\n",
        encoding="utf-8",
    )


def detect_tailscale_ipv4() -> str | None:
    """Return Tailscale IPv4 if available."""
    import shutil
    import subprocess

    exe = shutil.which("tailscale")
    if not exe:
        # Common Windows install path
        candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tailscale" / "tailscale.exe"
        exe = str(candidate) if candidate.exists() else None
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    ip = (proc.stdout or "").strip().splitlines()
    if not ip:
        return None
    value = ip[0].strip()
    return value or None


def default_scheduler_url_for_host() -> str:
    """Prefer Tailscale URL when this machine has Tailscale; else local."""
    ts = detect_tailscale_ipv4()
    if ts:
        return f"http://{ts}:8766"
    return DEFAULT_LOCAL_SCHEDULER_URL


def agent_vms_present(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path or AGENT_VMS_DEFAULT)
    vagrantfile = p / "Vagrantfile"
    return {
        "path": str(p),
        "exists": p.is_dir(),
        "has_vagrantfile": vagrantfile.is_file(),
        "ready": p.is_dir() and vagrantfile.is_file(),
    }


def python_deps_status() -> dict[str, Any]:
    missing: list[str] = []
    for mod in ("httpx", "dotenv", "fastapi", "uvicorn", "customtkinter"):
        try:
            __import__("dotenv" if mod == "dotenv" else mod)
        except ImportError:
            missing.append(mod)
    return {"ok": not missing, "missing": missing}

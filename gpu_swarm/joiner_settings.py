"""Persistent settings for the GPU Pool desktop joiner app."""

from __future__ import annotations

import json
import os
import socket
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from gpu_swarm.config import ROOT

SETTINGS_PATH = ROOT / "data" / "joiner_settings.json"
DEFAULT_SCHEDULER_URL = "http://100.85.165.84:8766"
DEFAULT_LOCAL_SCHEDULER_URL = "http://127.0.0.1:8766"
DEFAULT_PORTAL_URL = "http://100.85.165.84:8767/portal"
DEFAULT_LOCAL_PORTAL_URL = "http://127.0.0.1:8767/portal"
# Safe to show in UI — never display the pool password from .env.
PORTAL_INVITE_CODE = "glitch-factor"
AGENT_VMS_DEFAULT = Path(r"C:\Users\Drew\Projects\agent-vms")

# Modules required for the desktop joiner + worker path (not Discord bot).
REQUIRED_MODULES: tuple[tuple[str, str], ...] = (
    ("httpx", "httpx"),
    ("dotenv", "python-dotenv"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("customtkinter", "customtkinter"),
    ("psutil", "psutil"),
    ("pydantic", "pydantic"),
    ("aiosqlite", "aiosqlite"),
)


@dataclass
class JoinerSettings:
    scheduler_url: str = DEFAULT_SCHEDULER_URL
    worker_name: str = ""
    discord_user: str = ""
    max_vram_mb: int = 0
    max_cpu_percent: float = 50.0
    max_ram_mb: int = 0  # 0 = advertise detected free/soft-unbounded
    max_disk_gb: float = 0.0  # SSD/HDD contribution soft cap
    portal_url: str = DEFAULT_LOCAL_PORTAL_URL
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


def portal_url_candidates() -> list[str]:
    """Ordered portal URLs to try (local first when on host, then Tailscale)."""
    urls: list[str] = []
    for u in (DEFAULT_LOCAL_PORTAL_URL, DEFAULT_PORTAL_URL):
        if u not in urls:
            urls.append(u)
    ts = detect_tailscale_ipv4()
    if ts:
        ts_url = f"http://{ts}:8767/portal"
        if ts_url not in urls:
            urls.append(ts_url)
    return urls


def agent_vms_present(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path or AGENT_VMS_DEFAULT)
    vagrantfile = p / "Vagrantfile"
    return {
        "path": str(p),
        "exists": p.is_dir(),
        "has_vagrantfile": vagrantfile.is_file(),
        "ready": p.is_dir() and vagrantfile.is_file(),
    }


def detect_python_runtime() -> dict[str, Any]:
    """Describe the interpreter running this process (the joiner itself)."""
    major, minor, micro = sys.version_info[:3]
    ok = (major, minor) >= (3, 10)
    fix = ""
    if not ok:
        fix = (
            "Install Python 3.10+ from https://www.python.org/downloads/windows/ "
            "and check 'Add python.exe to PATH', then re-run start-gpu-pool-app.cmd"
        )
    return {
        "ok": ok,
        "executable": sys.executable,
        "version": f"{major}.{minor}.{micro}",
        "version_info": [major, minor, micro],
        "message": f"Python {major}.{minor}.{micro} @ {sys.executable}",
        "fix": fix,
    }


def python_deps_status() -> dict[str, Any]:
    missing: list[str] = []
    present: list[str] = []
    for mod, pip_name in REQUIRED_MODULES:
        try:
            __import__(mod)
            present.append(pip_name)
        except ImportError:
            missing.append(pip_name)
    return {
        "ok": not missing,
        "missing": missing,
        "present": present,
        "fix": (
            f"Click Install in the wizard, or run:\n"
            f'  "{sys.executable}" -m pip install -r requirements.txt'
            if missing
            else ""
        ),
    }

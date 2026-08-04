"""Persistent settings for the GPU Pool desktop joiner app."""

from __future__ import annotations

import json
import os
import socket
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from gpu_swarm.paths import ROOT, is_frozen

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
    """Describe the interpreter running this process + isolated pip Python status."""
    try:
        from gpu_swarm.portable_python import python_runtime_report

        report = python_runtime_report()
    except Exception:  # noqa: BLE001
        report = {}

    if is_frozen():
        return {
            "ok": True,
            "executable": sys.executable,
            "version": "bundled",
            "version_info": list(sys.version_info[:3]),
            "frozen": True,
            "message": report.get("message")
            or f"GPU Pool Windows runtime @ {sys.executable}",
            "fix": report.get("fix") or "",
            "conflict_hint": report.get("conflict_hint") or "",
            "pip_python": report.get("pip_python") or "",
            "pip_source": report.get("pip_source") or "",
            "portable_present": bool(report.get("portable_present")),
            "venv_present": bool(report.get("venv_present")),
            "report": report,
        }
    major, minor, micro = sys.version_info[:3]
    app_ok = (major, minor) >= (3, 10)
    pip_ok = bool(report.get("pip_ok")) if report else app_ok
    # App can launch on 3.10+; pip work prefers isolated venv when system is broken.
    ok = app_ok or pip_ok
    fix = report.get("fix") or ""
    if not app_ok and not fix:
        fix = (
            "System Python is below 3.10 or broken. Click “Bootstrap portable Python” "
            "to install an isolated CPython 3.12 + venv under %LOCALAPPDATA%\\GPUPool\\ "
            "(do not fight global site-packages)."
        )
    conflict = report.get("conflict_hint") or ""
    if not app_ok and not conflict:
        conflict = (
            "Python version conflict: this machine’s interpreter is too old or broken. "
            "GPU Pool will bootstrap portable Python instead of using global site-packages."
        )
    msg = report.get("message") or f"Python {major}.{minor}.{micro} @ {sys.executable}"
    if conflict and not app_ok:
        msg = f"NEEDS PORTABLE PYTHON — {msg}"
    return {
        "ok": ok,
        "executable": sys.executable,
        "version": f"{major}.{minor}.{micro}",
        "version_info": [major, minor, micro],
        "frozen": False,
        "message": msg,
        "fix": fix,
        "conflict_hint": conflict,
        "pip_python": report.get("pip_python") or "",
        "pip_source": report.get("pip_source") or "",
        "portable_present": bool(report.get("portable_present")),
        "venv_present": bool(report.get("venv_present")),
        "report": report,
    }


def python_deps_status() -> dict[str, Any]:
    if is_frozen():
        # UI + worker path are bundled; torch stays optional/out-of-band.
        return {
            "ok": True,
            "missing": [],
            "present": [name for _, name in REQUIRED_MODULES],
            "frozen": True,
            "message": "Desktop runtime bundled in GPUPool.exe (torch optional, not shipped).",
            "fix": "",
        }
    missing: list[str] = []
    present: list[str] = []
    for mod, pip_name in REQUIRED_MODULES:
        try:
            __import__(mod)
            present.append(pip_name)
        except ImportError:
            missing.append(pip_name)
    try:
        from gpu_swarm.portable_python import resolve_pip_python, venv_python_exe

        pip_py = resolve_pip_python() or sys.executable
        in_venv = venv_python_exe().is_file() and str(venv_python_exe()) == pip_py
    except Exception:  # noqa: BLE001
        pip_py = sys.executable
        in_venv = False
    fix = ""
    if missing:
        if in_venv:
            fix = (
                f'Click Install in the wizard (uses isolated venv):\n'
                f'  "{pip_py}" -m pip install -r requirements.txt'
            )
        else:
            fix = (
                "Click Install in the wizard. Preferred: Bootstrap portable Python first, "
                "then install into %LOCALAPPDATA%\\GPUPool\\venv (never global site-packages).\n"
                f'Fallback: "{pip_py}" -m pip install -r requirements.txt'
            )
    return {
        "ok": not missing,
        "missing": missing,
        "present": present,
        "frozen": False,
        "pip_python": pip_py,
        "isolated_venv": in_venv,
        "fix": fix,
    }

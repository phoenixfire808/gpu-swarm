"""
Stable backend API for the GPU Pool desktop app.

Worker 1 (UI) and Worker 2 (this module) coordinate on these names.
Prefer: get_gpus, save_config, test_scheduler, start_worker, stop_worker, get_status.
Worker1 also uses: detect_gpus, load/save_joiner_settings, fetch_scheduler_status, etc.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from gpu_swarm.config import ROOT
from gpu_swarm.joiner_settings import (
    DEFAULT_LOCAL_PORTAL_URL,
    DEFAULT_LOCAL_SCHEDULER_URL,
    DEFAULT_PORTAL_URL,
    DEFAULT_SCHEDULER_URL,
    PORTAL_INVITE_CODE,
    JoinerSettings,
    agent_vms_present,
    default_scheduler_url_for_host,
    detect_python_runtime,
    detect_tailscale_ipv4,
    load_settings,
    portal_url_candidates,
    python_deps_status,
    save_settings,
)

__all__ = [
    "JoinerSettings",
    "WorkerRuntimeStatus",
    "PORTAL_INVITE_CODE",
    # Task / UI contract
    "get_gpus",
    "load_config",
    "save_config",
    "test_scheduler",
    "start_worker",
    "stop_worker",
    "get_status",
    # Worker1 aliases
    "check_nvidia",
    "check_python",
    "check_python_deps",
    "check_torch_cuda",
    "detect_gpus",
    "detect_host_resources",
    "fetch_scheduler_status",
    "get_discord_helper_text",
    "get_agent_vms_info",
    "get_default_scheduler_url",
    "get_portal_hints",
    "get_portal_url",
    "get_tailscale_ipv4",
    "install_requirements",
    "install_torch_cuda",
    "is_worker_running",
    "load_joiner_settings",
    "open_portal_url",
    "resolve_portal_url",
    "save_joiner_settings",
    "wait_for_worker_online",
    "worker_runtime_status",
]

PID_FILE = ROOT / "data" / "joiner_worker.pid"
LOG_FILE = ROOT / "data" / "joiner_worker.log"
JOINER_WORKER_ID_FILE = ROOT / "data" / "joiner_worker_id.txt"
ENV_FILE = ROOT / ".env"

# Keys we may sync into .env — never touch Discord/bot secrets.
_SAFE_ENV_KEYS = (
    "GPU_SWARM_SCHEDULER_URL",
    "GPU_SWARM_WORKER_NAME",
    "GPU_SWARM_DISCORD_USER",
    "GPU_SWARM_MAX_VRAM_MB",
    "GPU_SWARM_MAX_CPU_PERCENT",
    "GPU_SWARM_MAX_RAM_MB",
    "GPU_SWARM_MAX_DISK_GB",
)

_FORBIDDEN_ENV_KEYS = frozenset(
    {
        "DISCORD_BOT_TOKEN",
        "DISCORD_CLIENT_ID",
        "DISCORD_GUILD_ID",
        "DISCORD_BOT_TOKEN_PASTE",
    }
)


@dataclass
class WorkerRuntimeStatus:
    running: bool = False
    connected: bool = False
    worker_id: str = ""
    worker_name: str = ""
    last_heartbeat: str = ""
    gpus_advertised: list[str] = field(default_factory=list)
    free_vram_mb: int = 0
    total_vram_mb: int = 0
    cpu_cores: int = 0
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    disk_free_mb: int = 0
    detail: str = ""
    pid: int | None = None


_worker_proc: subprocess.Popen[str] | None = None
_worker_log_handle: Any | None = None


def load_joiner_settings() -> JoinerSettings:
    return load_settings()


def save_joiner_settings(settings: JoinerSettings) -> None:
    save_settings(settings)
    _sync_env_file(settings)


def load_config() -> JoinerSettings:
    """Alias: load persisted joiner config."""
    return load_joiner_settings()


def save_config(config: JoinerSettings | dict[str, Any] | None = None, **kwargs: Any) -> JoinerSettings:
    """
    Persist VRAM/CPU caps, scheduler URL, worker name (JSON + safe .env keys).
    Never overwrites DISCORD_BOT_TOKEN or other Discord secrets.
    """
    base = load_joiner_settings()
    data = asdict(base)
    if isinstance(config, JoinerSettings):
        data.update(asdict(config))
    elif isinstance(config, dict):
        for key, value in config.items():
            if key in data:
                data[key] = value
    for key, value in kwargs.items():
        if key in data:
            data[key] = value
    settings = JoinerSettings(**data)
    save_joiner_settings(settings)
    return settings


def get_default_scheduler_url() -> str:
    return default_scheduler_url_for_host() or DEFAULT_SCHEDULER_URL


def get_portal_url(settings: JoinerSettings | None = None) -> str:
    """Browser portal URL (easiest remote join path). Prefer a live URL."""
    if settings and settings.portal_url:
        return settings.portal_url.strip()
    s = load_joiner_settings()
    saved = (s.portal_url or "").strip()
    if saved:
        return saved
    return resolve_portal_url().get("url") or DEFAULT_LOCAL_PORTAL_URL


def resolve_portal_url(timeout: float = 2.5) -> dict[str, Any]:
    """
    Probe candidate portal URLs and return the first that responds.
    Prefers local http://127.0.0.1:8767/portal when live; Tailscale is a share hint.
    Never returns or reads the pool password.
    """
    import httpx

    attempts: list[dict[str, Any]] = []
    for candidate in portal_url_candidates():
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                r = client.get(candidate)
            ok = r.status_code < 500
            attempts.append({"url": candidate, "ok": ok, "status": r.status_code})
            if ok:
                return {
                    "ok": True,
                    "url": candidate,
                    "local_url": DEFAULT_LOCAL_PORTAL_URL,
                    "tailscale_url": DEFAULT_PORTAL_URL,
                    "invite_code": PORTAL_INVITE_CODE,
                    "attempts": attempts,
                    "message": f"Portal reachable at {candidate}",
                }
        except Exception as exc:  # noqa: BLE001
            attempts.append({"url": candidate, "ok": False, "error": str(exc)})

    return {
        "ok": False,
        "url": DEFAULT_LOCAL_PORTAL_URL,
        "local_url": DEFAULT_LOCAL_PORTAL_URL,
        "tailscale_url": DEFAULT_PORTAL_URL,
        "invite_code": PORTAL_INVITE_CODE,
        "attempts": attempts,
        "message": (
            "Portal not reachable. Start it with start-portal.cmd "
            f"then open {DEFAULT_LOCAL_PORTAL_URL}"
        ),
        "fix": (
            f"1) Run start-portal.cmd on Drew's host\n"
            f"2) Open {DEFAULT_LOCAL_PORTAL_URL} (same machine) or "
            f"{DEFAULT_PORTAL_URL} (Tailscale)\n"
            f"3) Sign in with invite code: {PORTAL_INVITE_CODE}"
        ),
    }


def get_portal_hints() -> dict[str, Any]:
    """UI-safe portal onboarding hints (invite code only — never pool password)."""
    resolved = resolve_portal_url()
    return {
        "invite_code": PORTAL_INVITE_CODE,
        "local_url": DEFAULT_LOCAL_PORTAL_URL,
        "tailscale_url": DEFAULT_PORTAL_URL,
        "url": resolved.get("url") or DEFAULT_LOCAL_PORTAL_URL,
        "reachable": bool(resolved.get("ok")),
        "message": resolved.get("message") or "",
        "fix": resolved.get("fix") or "",
        "auth_note": (
            f"Browser portal login: invite code `{PORTAL_INVITE_CODE}` "
            "(or the shared pool password from .env — not shown here)."
        ),
    }


def open_portal_url(url: str | None = None) -> dict[str, Any]:
    """Open the web portal in the default browser (deep-link to a live URL when possible)."""
    import webbrowser

    if url and url.strip():
        target = url.strip()
    else:
        resolved = resolve_portal_url()
        target = (resolved.get("url") or get_portal_url()).strip()
    if not target:
        return {"ok": False, "message": "Empty portal URL", "invite_code": PORTAL_INVITE_CODE}
    try:
        webbrowser.open(target)
        return {
            "ok": True,
            "message": f"Opened {target} — invite code: {PORTAL_INVITE_CODE}",
            "url": target,
            "invite_code": PORTAL_INVITE_CODE,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "message": str(exc),
            "url": target,
            "invite_code": PORTAL_INVITE_CODE,
            "fix": f"Open manually: {target}",
        }


def get_tailscale_ipv4() -> str | None:
    return detect_tailscale_ipv4()


def detect_host_resources() -> dict[str, Any]:
    """
    Real host RAM + disk totals (no mocks).
    Used by UI sliders for dedication caps.
    """
    import os

    total_ram_mb = 0
    avail_ram_mb = 0
    total_disk_gb = 0.0
    free_disk_gb = 0.0
    error = ""

    try:
        import psutil  # type: ignore

        vm = psutil.virtual_memory()
        total_ram_mb = int(vm.total // (1024 * 1024))
        avail_ram_mb = int(vm.available // (1024 * 1024))
        disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
        total_disk_gb = round(disk.total / (1024**3), 1)
        free_disk_gb = round(disk.free / (1024**3), 1)
    except ImportError:
        # Windows fallback without forcing a psutil reinstall
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                total_ram_mb = int(stat.ullTotalPhys // (1024 * 1024))
                avail_ram_mb = int(stat.ullAvailPhys // (1024 * 1024))
        except Exception as exc:  # noqa: BLE001
            error = f"RAM detect failed: {exc}"
        try:
            import shutil as _shutil

            root = os.environ.get("SystemDrive", "C:") + "\\"
            usage = _shutil.disk_usage(root)
            total_disk_gb = round(usage.total / (1024**3), 1)
            free_disk_gb = round(usage.free / (1024**3), 1)
        except Exception as exc:  # noqa: BLE001
            error = (error + "; " if error else "") + f"Disk detect failed: {exc}"
    except Exception as exc:  # noqa: BLE001
        error = str(exc)

    return {
        "ok": total_ram_mb > 0 or total_disk_gb > 0,
        "total_ram_mb": total_ram_mb,
        "avail_ram_mb": avail_ram_mb,
        "total_disk_gb": total_disk_gb,
        "free_disk_gb": free_disk_gb,
        "error": error,
    }


def check_nvidia() -> dict[str, Any]:
    """Return nvidia-smi availability + short message (real check, no mocks)."""
    from gpu_swarm.gpu import nvidia_smi_available

    path = shutil.which("nvidia-smi")
    ok = nvidia_smi_available()
    return {
        "ok": ok,
        "path": path or "",
        "message": "nvidia-smi found" if ok else "nvidia-smi not found — install NVIDIA drivers",
    }


def detect_gpus() -> dict[str, Any]:
    """Live GPU inventory via nvidia-smi."""
    from gpu_swarm.gpu import inventory_summary

    try:
        inv = inventory_summary()
        return {
            "ok": True,
            "gpus": inv["gpus"],
            "gpu_count": inv["gpu_count"],
            "free_vram_mb": inv["free_vram_mb"],
            "total_vram_mb": inv["total_vram_mb"],
            "names": inv["names"],
            "nvidia_smi": inv["nvidia_smi"],
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "gpus": [],
            "gpu_count": 0,
            "free_vram_mb": 0,
            "total_vram_mb": 0,
            "names": [],
            "nvidia_smi": False,
            "error": str(exc),
        }


def get_gpus() -> list[dict[str, Any]]:
    """Stable API: list of live GPU dicts from nvidia-smi (empty if unavailable)."""
    result = detect_gpus()
    if not result.get("ok"):
        return []
    return list(result.get("gpus") or [])


def check_python() -> dict[str, Any]:
    """Detect the Python runtime powering this app."""
    return detect_python_runtime()


def check_python_deps() -> dict[str, Any]:
    return python_deps_status()


def check_torch_cuda() -> dict[str, Any]:
    """Optional CUDA PyTorch presence (not required to join the pool)."""
    try:
        import torch  # type: ignore
    except ImportError:
        return {
            "ok": False,
            "installed": False,
            "cuda": False,
            "version": "",
            "message": "PyTorch not installed (optional — needed for CUDA compute jobs)",
            "fix": "Use the Install CUDA PyTorch button (large download; consent required).",
        }
    cuda = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
    ver = str(getattr(torch, "__version__", "?"))
    return {
        "ok": True,
        "installed": True,
        "cuda": cuda,
        "version": ver,
        "message": f"torch {ver} — CUDA {'available' if cuda else 'not available'}",
        "fix": (
            ""
            if cuda
            else "CPU-only torch detected. Install a CUDA build if you want GPU compute jobs."
        ),
    }


def install_requirements(*, force: bool = False) -> dict[str, Any]:
    """
    Install from requirements.txt only when deps are missing (avoid reinstall loops).
    Pass force=True to repair/upgrade from requirements.txt.
    """
    status = check_python_deps()
    if status.get("ok") and not force:
        return {
            "ok": True,
            "message": "Dependencies already satisfied — skipped full reinstall.",
            "skipped": True,
            "missing": [],
        }
    req = ROOT / "requirements.txt"
    if not req.is_file():
        return {
            "ok": False,
            "message": f"Missing {req}",
            "fix": "Restore requirements.txt in the repo root.",
        }
    missing = status.get("missing") or []
    cmd = [sys.executable, "-m", "pip", "install", "--user", "-r", str(req)]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
            cwd=str(ROOT),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "message": str(exc),
            "fix": f'Run manually: "{sys.executable}" -m pip install --user -r requirements.txt',
        }
    ok = proc.returncode == 0
    tail = ((proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else ""))[-1200:]
    after = check_python_deps()
    if ok and after.get("ok"):
        return {
            "ok": True,
            "message": tail or "Installed requirements successfully.",
            "code": proc.returncode,
            "missing_before": missing,
        }
    still = after.get("missing") or missing
    return {
        "ok": False,
        "message": tail or "pip failed",
        "code": proc.returncode,
        "missing": still,
        "fix": (
            f"Still missing: {', '.join(still)}\n"
            f'Fix: "{sys.executable}" -m pip install --user -r "{req}"'
        ),
    }


def install_torch_cuda(*, index_url: str = "https://download.pytorch.org/whl/cu124") -> dict[str, Any]:
    """
    Optional large download — only call after explicit user consent in the UI.
    Installs torch/torchvision/torchaudio from the CUDA wheel index.
    """
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--user",
        "torch",
        "torchvision",
        "torchaudio",
        "--index-url",
        index_url,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
            cwd=str(ROOT),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "message": str(exc),
            "fix": " ".join(cmd),
        }
    ok = proc.returncode == 0
    tail = ((proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else ""))[-1200:]
    status = check_torch_cuda()
    if ok:
        return {
            "ok": True,
            "message": tail or "PyTorch install finished.",
            "torch": status,
            "code": proc.returncode,
        }
    return {
        "ok": False,
        "message": tail or "PyTorch install failed",
        "code": proc.returncode,
        "fix": (
            f'Retry: "{sys.executable}" -m pip install --user torch torchvision torchaudio '
            f"--index-url {index_url}"
        ),
        "torch": status,
    }


def fetch_scheduler_status(scheduler_url: str | None = None, timeout: float = 5.0) -> dict[str, Any]:
    """GET /status from scheduler. Real HTTP — no mocks."""
    import httpx

    base = (scheduler_url or load_joiner_settings().scheduler_url or "").rstrip("/")
    if not base:
        return {"ok": False, "error": "Empty scheduler URL", "data": None, "url": ""}
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(f"{base}/status")
            r.raise_for_status()
            data = r.json()
        return {"ok": True, "error": "", "data": data, "url": base}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "data": None, "url": base}


def test_scheduler(url: str | None = None, timeout: float = 5.0) -> dict[str, Any]:
    """
    Connectivity test against scheduler /status.
    Tries: explicit url → saved config → Tailscale default → 127.0.0.1:8766.
    """
    candidates: list[str] = []
    if url:
        candidates.append(url.rstrip("/"))
    settings = load_joiner_settings()
    if settings.scheduler_url:
        candidates.append(settings.scheduler_url.rstrip("/"))
    candidates.append(get_default_scheduler_url().rstrip("/"))
    if DEFAULT_SCHEDULER_URL.rstrip("/") not in candidates:
        candidates.append(DEFAULT_SCHEDULER_URL.rstrip("/"))
    if DEFAULT_LOCAL_SCHEDULER_URL.rstrip("/") not in candidates:
        candidates.append(DEFAULT_LOCAL_SCHEDULER_URL.rstrip("/"))

    seen: set[str] = set()
    attempts: list[dict[str, Any]] = []
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        result = fetch_scheduler_status(candidate, timeout=timeout)
        attempts.append(
            {
                "url": candidate,
                "ok": bool(result.get("ok")),
                "error": result.get("error") or "",
            }
        )
        if result.get("ok"):
            return {
                "ok": True,
                "url": candidate,
                "error": "",
                "data": result.get("data"),
                "attempts": attempts,
                "tailscale_ipv4": get_tailscale_ipv4(),
            }

    return {
        "ok": False,
        "url": candidates[0] if candidates else "",
        "error": attempts[-1]["error"] if attempts else "No scheduler URL to try",
        "data": None,
        "attempts": attempts,
        "tailscale_ipv4": get_tailscale_ipv4(),
    }


def is_worker_running() -> bool:
    global _worker_proc
    if _worker_proc is not None:
        code = _worker_proc.poll()
        if code is None:
            return True
        _worker_proc = None
        _clear_pid_file()
        return False

    pid = _read_pid_file()
    if pid is None:
        return False
    if _pid_alive(pid):
        return True
    _clear_pid_file()
    return False


def start_worker(
    settings: JoinerSettings | None = None,
    *,
    wait_online_sec: float = 8.0,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Start contribution worker subprocess with joiner env caps."""
    global _worker_proc, _worker_log_handle
    if is_worker_running():
        pid = _worker_proc.pid if _worker_proc else _read_pid_file()
        return {"ok": False, "message": "Worker already running", "pid": pid}

    settings = settings or load_joiner_settings()
    save_joiner_settings(settings)

    # Preflight: scheduler reachable
    sched = test_scheduler(settings.scheduler_url)
    if not sched.get("ok"):
        return {
            "ok": False,
            "message": f"Scheduler unreachable: {sched.get('error') or 'unknown'}",
            "pid": None,
            "fix": (
                f"1) Confirm scheduler is running on Drew's host\n"
                f"2) Test URL: {settings.scheduler_url}\n"
                f"3) Same-machine fallback: {DEFAULT_LOCAL_SCHEDULER_URL}\n"
                f"4) Tailscale members: {DEFAULT_SCHEDULER_URL}"
            ),
            "scheduler": sched,
        }

    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["GPU_SWARM_SCHEDULER_URL"] = settings.scheduler_url.rstrip("/")
    env["GPU_SWARM_WORKER_NAME"] = settings.worker_name
    env["GPU_SWARM_DISCORD_USER"] = settings.discord_user or ""
    env["GPU_SWARM_MAX_VRAM_MB"] = str(int(settings.max_vram_mb or 0))
    env["GPU_SWARM_MAX_CPU_PERCENT"] = str(float(settings.max_cpu_percent))
    env["GPU_SWARM_MAX_RAM_MB"] = str(int(getattr(settings, "max_ram_mb", 0) or 0))
    env["GPU_SWARM_MAX_DISK_GB"] = str(float(getattr(settings, "max_disk_gb", 0) or 0))
    disk_mb = int(float(getattr(settings, "max_disk_gb", 0) or 0) * 1024)
    if disk_mb > 0:
        env["GPU_SWARM_MAX_DISK_MB"] = str(disk_mb)
    # Separate id file so desktop joiner does not clash with start-worker.cmd
    env["GPU_SWARM_WORKER_ID_FILE"] = str(JOINER_WORKER_ID_FILE)

    cmd = [
        sys.executable,
        "-m",
        "gpu_swarm",
        "worker",
        "--name",
        settings.worker_name,
        "--scheduler-url",
        settings.scheduler_url.rstrip("/"),
        "--max-vram-mb",
        str(int(settings.max_vram_mb or 0)),
        "--max-cpu-percent",
        str(float(settings.max_cpu_percent)),
        "--max-ram-mb",
        str(int(getattr(settings, "max_ram_mb", 0) or 0)),
        "--max-disk-mb",
        str(disk_mb),
    ]
    if settings.discord_user:
        cmd.extend(["--discord-user", settings.discord_user])

    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _worker_log_handle is not None:
            try:
                _worker_log_handle.close()
            except Exception:  # noqa: BLE001
                pass
        _worker_log_handle = open(LOG_FILE, "a", encoding="utf-8")  # noqa: SIM115
        _worker_log_handle.write(
            f"\n--- start {time.strftime('%Y-%m-%d %H:%M:%S')} name={settings.worker_name} ---\n"
        )
        _worker_log_handle.flush()
        _worker_proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=_worker_log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
        )
    except OSError as exc:
        _worker_proc = None
        return {
            "ok": False,
            "message": str(exc),
            "pid": None,
            "fix": f"Could not spawn worker. Check Python: {sys.executable}",
        }

    _write_pid_file(_worker_proc.pid)
    time.sleep(0.5)
    if _worker_proc.poll() is not None:
        code = _worker_proc.returncode
        _worker_proc = None
        _clear_pid_file()
        log_tail = _tail_log(40)
        return {
            "ok": False,
            "message": f"Worker exited immediately (code={code}). See {LOG_FILE}",
            "pid": None,
            "log": str(LOG_FILE),
            "log_tail": log_tail,
            "fix": f"Open {LOG_FILE} for the exact traceback, then fix and Join again.",
        }

    online = wait_for_worker_online(settings, timeout_sec=wait_online_sec)
    if online.get("ok"):
        return {
            "ok": True,
            "message": f"Joined pool as {settings.worker_name}",
            "pid": _worker_proc.pid if _worker_proc else None,
            "log": str(LOG_FILE),
            "worker_name": settings.worker_name,
            "scheduler_url": settings.scheduler_url.rstrip("/"),
            "runtime": online.get("runtime"),
        }

    return {
        "ok": True,
        "message": (
            f"Worker started (pid={_worker_proc.pid if _worker_proc else '?'}) but not "
            f"visible on scheduler yet: {online.get('detail') or 'waiting'}"
        ),
        "pid": _worker_proc.pid if _worker_proc else None,
        "log": str(LOG_FILE),
        "worker_name": settings.worker_name,
        "scheduler_url": settings.scheduler_url.rstrip("/"),
        "warning": online.get("detail") or "not registered yet",
        "fix": (
            "Worker process is running. Wait a few seconds and Refresh status. "
            f"If it never appears, check {LOG_FILE}."
        ),
    }


def wait_for_worker_online(
    settings: JoinerSettings | None = None,
    *,
    timeout_sec: float = 8.0,
) -> dict[str, Any]:
    """Poll local process + scheduler until this worker shows online/busy."""
    settings = settings or load_joiner_settings()
    deadline = time.time() + max(0.5, timeout_sec)
    last: WorkerRuntimeStatus | None = None
    while time.time() < deadline:
        last = worker_runtime_status(settings)
        if last.running and last.connected:
            return {"ok": True, "runtime": asdict(last), "detail": last.detail}
        time.sleep(0.5)
    detail = last.detail if last else "timeout"
    return {
        "ok": False,
        "runtime": asdict(last) if last else None,
        "detail": detail,
    }


def _tail_log(lines: int = 40) -> str:
    if not LOG_FILE.is_file():
        return ""
    try:
        text = LOG_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    parts = text.splitlines()
    return "\n".join(parts[-lines:])


def stop_worker() -> dict[str, Any]:
    """Stop app-managed worker process cleanly (does not touch host start-worker.cmd)."""
    global _worker_proc, _worker_log_handle

    proc = _worker_proc
    pid = proc.pid if proc and proc.poll() is None else _read_pid_file()

    if proc is None and pid is None:
        _clear_pid_file()
        return {"ok": True, "message": "Worker was not running"}

    if proc is None and pid is not None:
        # Adopt PID from file (UI restarted) and stop it.
        try:
            _signal_stop_pid(pid)
        except OSError as exc:
            _clear_pid_file()
            return {"ok": False, "message": str(exc)}
        _clear_pid_file()
        return {"ok": True, "message": f"Worker stopped (pid={pid})"}

    assert proc is not None
    try:
        _graceful_stop(proc)
    except OSError as exc:
        return {"ok": False, "message": str(exc)}
    finally:
        _worker_proc = None
        _clear_pid_file()
        if _worker_log_handle is not None:
            try:
                _worker_log_handle.flush()
            except Exception:  # noqa: BLE001
                pass

    return {"ok": True, "message": "Worker stopped", "pid": pid}


def worker_runtime_status(settings: JoinerSettings | None = None) -> WorkerRuntimeStatus:
    """Combine local process state with scheduler /status for this worker name."""
    running = is_worker_running()
    pid = _worker_proc.pid if _worker_proc and running else (_read_pid_file() if running else None)
    st = WorkerRuntimeStatus(running=running, pid=pid)
    settings = settings or load_joiner_settings()
    st.worker_name = settings.worker_name

    if JOINER_WORKER_ID_FILE.is_file():
        st.worker_id = JOINER_WORKER_ID_FILE.read_text(encoding="utf-8").strip()

    fetched = fetch_scheduler_status(settings.scheduler_url)
    if not fetched.get("ok") or not fetched.get("data"):
        st.connected = False
        st.detail = fetched.get("error") or "Scheduler unreachable"
        return st

    data = fetched["data"]
    workers = data.get("workers") or []
    mine = None
    for w in workers:
        if st.worker_id and w.get("id") == st.worker_id:
            mine = w
            break
        if w.get("name") == settings.worker_name:
            mine = w
            break

    if mine:
        st.connected = str(mine.get("status", "")).lower() in ("online", "busy")
        st.worker_id = mine.get("id") or st.worker_id
        st.worker_name = mine.get("name") or st.worker_name
        hb = mine.get("last_heartbeat")
        st.last_heartbeat = str(hb) if hb is not None else ""
        st.free_vram_mb = int(mine.get("free_vram_mb") or 0)
        st.total_vram_mb = int(mine.get("total_vram_mb") or 0)
        st.cpu_cores = int(mine.get("cpu_cores") or 0)
        st.ram_total_mb = int(mine.get("ram_total_mb") or 0)
        st.ram_available_mb = int(mine.get("ram_available_mb") or 0)
        st.disk_free_mb = int(mine.get("disk_free_mb") or 0)
        gpus = mine.get("gpus") or []
        if gpus and isinstance(gpus[0], dict):
            st.gpus_advertised = [g.get("name", "?") for g in gpus]
        elif isinstance(gpus, list):
            st.gpus_advertised = [str(g) for g in gpus]
        st.detail = f"status={mine.get('status')}"
    else:
        st.connected = False
        st.detail = "Not registered on scheduler yet" if running else "Not in pool"
        st.free_vram_mb = int(data.get("free_vram_mb") or 0)
        st.total_vram_mb = int(data.get("total_vram_mb") or 0)
        st.cpu_cores = int(data.get("cpu_cores") or 0)
        st.ram_total_mb = int(data.get("ram_total_mb") or 0)
        st.ram_available_mb = int(data.get("ram_available_mb") or 0)
        st.disk_free_mb = int(data.get("disk_free_mb") or 0)

    return st


def get_status() -> dict[str, Any]:
    """Stable API: local worker + scheduler snapshot for the UI status panel."""
    settings = load_joiner_settings()
    runtime = worker_runtime_status(settings)
    sched = fetch_scheduler_status(settings.scheduler_url)
    gpus = detect_gpus()
    return {
        "worker": {
            "running": runtime.running,
            "connected": runtime.connected,
            "worker_id": runtime.worker_id,
            "worker_name": runtime.worker_name,
            "last_heartbeat": runtime.last_heartbeat,
            "gpus_advertised": runtime.gpus_advertised,
            "free_vram_mb": runtime.free_vram_mb,
            "total_vram_mb": runtime.total_vram_mb,
            "cpu_cores": runtime.cpu_cores,
            "ram_total_mb": runtime.ram_total_mb,
            "ram_available_mb": runtime.ram_available_mb,
            "disk_free_mb": runtime.disk_free_mb,
            "detail": runtime.detail,
            "pid": runtime.pid,
        },
        "scheduler": {
            "ok": bool(sched.get("ok")),
            "url": sched.get("url") or settings.scheduler_url,
            "error": sched.get("error") or "",
            "data": sched.get("data"),
        },
        "local_gpus": gpus,
        "host_resources": detect_host_resources(),
        "config": asdict(settings),
        "nvidia": check_nvidia(),
        "portal_url": get_portal_url(settings),
        "tailscale_ipv4": get_tailscale_ipv4(),
    }


def get_discord_helper_text() -> str:
    hints = get_portal_hints()
    return (
        "Glitch Factor — GPU Pool Discord commands\n"
        "\n"
        "  /pool         Pool overview (workers + VRAM + host metrics)\n"
        "  /workers      List workers\n"
        "  /contribute   How to contribute / soft caps\n"
        "  /submit_probe Submit a live GPU probe job\n"
        "  /submit_compute  CUDA matmul probe\n"
        "  /job_status   Check a job by id\n"
        "\n"
        "Easiest remote path: open the web portal in a browser.\n"
        f"  Local:     {hints['local_url']}\n"
        f"  Tailscale: {hints['tailscale_url']}\n"
        f"  Invite:    {hints['invite_code']}  (pool password stays in .env — not shown)\n"
        "\n"
        "This desktop app is the power-user native joiner (local caps + Join/Leave).\n"
        "CLI path: see DISCORD_MEMBER_QUICKSTART.md\n"
        "Do not expose the scheduler to the public internet."
    )


def get_agent_vms_info(path: str | None = None) -> dict[str, Any]:
    """Optional advanced: agent-vms desktop workspaces (not GPU passthrough)."""
    info = agent_vms_present(path)
    info["note"] = (
        "agent-vms is for full Linux desktop workspaces (VirtualBox + Vagrant). "
        "It is optional/advanced. VirtualBox on Windows does not reliably offer "
        "NVIDIA GPU passthrough — contribute with the native host worker + VRAM caps instead."
    )
    return info


# --- internals -----------------------------------------------------------------


def _sync_env_file(settings: JoinerSettings) -> None:
    """Update only safe GPU_SWARM_* keys in .env; never touch Discord secrets."""
    if not ENV_FILE.exists():
        return
    try:
        original = ENV_FILE.read_text(encoding="utf-8")
    except OSError:
        return

    updates = {
        "GPU_SWARM_SCHEDULER_URL": settings.scheduler_url.rstrip("/"),
        "GPU_SWARM_WORKER_NAME": settings.worker_name,
        "GPU_SWARM_DISCORD_USER": settings.discord_user or "",
        "GPU_SWARM_MAX_VRAM_MB": str(int(settings.max_vram_mb or 0)),
        "GPU_SWARM_MAX_CPU_PERCENT": str(float(settings.max_cpu_percent)),
        "GPU_SWARM_MAX_RAM_MB": str(int(getattr(settings, "max_ram_mb", 0) or 0)),
        "GPU_SWARM_MAX_DISK_GB": str(float(getattr(settings, "max_disk_gb", 0) or 0)),
    }
    for key in _FORBIDDEN_ENV_KEYS:
        updates.pop(key, None)

    lines = original.splitlines(keepends=True)
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in _FORBIDDEN_ENV_KEYS:
            out.append(line)
            continue
        if key in updates:
            nl = "\n" if line.endswith("\n") else ""
            out.append(f"{key}={updates[key]}{nl}")
            seen.add(key)
        else:
            out.append(line)

    for key in _SAFE_ENV_KEYS:
        if key not in seen and key in updates:
            if out and not out[-1].endswith("\n"):
                out[-1] = out[-1] + "\n"
            out.append(f"{key}={updates[key]}\n")

    new_text = "".join(out)
    if new_text != original:
        # Safety: Discord token line must still be present unchanged if it was.
        if "DISCORD_BOT_TOKEN=" in original:
            old_tok = _env_line_value(original, "DISCORD_BOT_TOKEN")
            new_tok = _env_line_value(new_text, "DISCORD_BOT_TOKEN")
            if old_tok != new_tok:
                return  # abort write — never risk token mutation
        try:
            ENV_FILE.write_text(new_text, encoding="utf-8")
        except OSError:
            return


def _env_line_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        if line.startswith(prefix) or line.lstrip().startswith(prefix):
            return line.split("=", 1)[1]
    return None


def _write_pid_file(pid: int) -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(pid), encoding="utf-8")


def _read_pid_file() -> int | None:
    if not PID_FILE.is_file():
        return None
    try:
        raw = PID_FILE.read_text(encoding="utf-8").strip()
        return int(raw) if raw else None
    except (OSError, ValueError):
        return None


def _clear_pid_file() -> None:
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            # OpenProcess + wait with timeout 0 — use tasklist-free ctypes check via os.kill(0)
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _graceful_stop(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        try:
            os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
        except OSError:
            proc.terminate()
        try:
            proc.wait(timeout=8)
            return
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
            return
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)


def _signal_stop_pid(pid: int) -> None:
    if sys.platform == "win32":
        try:
            os.kill(pid, signal.CTRL_BREAK_EVENT)
            deadline = time.time() + 8
            while time.time() < deadline and _pid_alive(pid):
                time.sleep(0.25)
            if _pid_alive(pid):
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
            return
        except OSError:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                check=False,
                timeout=10,
            )
            return
    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + 8
    while time.time() < deadline and _pid_alive(pid):
        time.sleep(0.25)
    if _pid_alive(pid):
        os.kill(pid, signal.SIGKILL)

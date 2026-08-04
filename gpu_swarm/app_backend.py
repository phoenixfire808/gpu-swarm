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

from gpu_swarm.paths import BUNDLE_ROOT, ROOT, is_frozen
from gpu_swarm.win_subprocess import popen_kwargs, run_kwargs
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
    "workspace_status",
    "workspace_resource_plan",
    "open_workspace",
    "halt_workspace",
    "apply_workspace_caps",
    "open_workspace_rdp",
    "ADVANCED_VM_DOC",
    "get_default_scheduler_url",
    "get_portal_hints",
    "get_portal_url",
    "get_tailscale_ipv4",
    "install_requirements",
    "install_torch_cuda",
    "install_joiner_deps",
    "install_prereqs",
    "check_prereqs",
    "script_paths",
    "is_worker_running",
    "load_joiner_settings",
    "open_portal_url",
    "resolve_portal_url",
    "save_joiner_settings",
    "wait_for_worker_online",
    "worker_runtime_status",
    # Utilize (consume) pool
    "list_allowed_jobs",
    "submit_job",
    "get_job",
    "wait_for_job",
    "pool_status",
    "get_utilize_helper_text",
    "get_connect_from_code_text",
    "get_friends_connect_text",
    "get_share_pack",
    "get_public_access_info",
    "auto_detect_scheduler_url",
    "validate_scheduler_url",
    "load_public_endpoints",
    "connect_urls_for_ui",
    "get_public_access_info",
    "scheduler_reachability_hint",
    "open_repo_doc",
    "discord_slash_for_job",
    "CONNECTING_DOC",
    "CODING_AGENT_EXAMPLE",
    "LOCAL_OFFLOAD_DOC",
    "LOCAL_MODEL_DOC",
    "PRIVATE_NETWORK_BLURB",
    "FRIENDS_CONNECT_STEPS",
    "start_local_endpoint",
    "stop_local_endpoint",
    "local_endpoint_status",
    "local_endpoint_available",
    "get_local_endpoint_env_line",
    "DEFAULT_LOCAL_ENDPOINT_URL",
    "DEFAULT_OPENAI_BASE_URL",
    "DEFAULT_LOCAL_ENDPOINT_PORT",
    # Portable Python + diagnostics (friend installs)
    "ensure_portable_python",
    "python_runtime_report",
    "bootstrap_portable_python",
    "collect_diagnostics",
    "write_error_log",
    "submit_diagnostics",
    "copy_diagnostics_text",
    "zip_error_log",
]

PID_FILE = ROOT / "data" / "joiner_worker.pid"
LOG_FILE = ROOT / "data" / "joiner_worker.log"
JOINER_WORKER_ID_FILE = ROOT / "data" / "joiner_worker_id.txt"
LOCAL_ENDPOINT_PID_FILE = ROOT / "data" / "local_endpoint.pid"
LOCAL_ENDPOINT_LOG_FILE = ROOT / "data" / "local_endpoint.log"
ENV_FILE = ROOT / ".env"
DEFAULT_LOCAL_ENDPOINT_PORT = 8080
DEFAULT_LOCAL_ENDPOINT_URL = f"http://127.0.0.1:{DEFAULT_LOCAL_ENDPOINT_PORT}"
DEFAULT_OPENAI_BASE_URL = f"{DEFAULT_LOCAL_ENDPOINT_URL}/v1"

# Member-facing copy — public tunnel preferred when live; Tailscale optional.
PRIVATE_NETWORK_BLURB = (
    "When the host runs start-public-access.cmd, friends use the public HTTPS portal — "
    "no Tailscale needed (invite code still required). Tailscale remains an optional private path."
)
FRIENDS_CONNECT_STEPS = (
    "1) Run GPU Pool → wizard → Install network & workspace tools (or scripts\\install-prereqs.cmd)",
    "2) Prefer the public portal URL from a pool member (no Tailscale) OR finish Tailscale login",
    f"3) Open portal (public link or {DEFAULT_PORTAL_URL}) or continue in the app",
    f"4) Sign in with invite code {PORTAL_INVITE_CODE} + your display name",
    "5) Home → Contribute or Utilize (Workspace optional — needs VirtualBox+Vagrant)",
)


def load_public_endpoints() -> dict[str, Any] | None:
    """Prefer normalized endpoints view; fall back to raw tunnel file."""
    try:
        from gpu_swarm.endpoints import load_public_endpoints as _norm

        pub = _norm()
        if pub:
            return pub
    except Exception:  # noqa: BLE001
        pass
    try:
        from gpu_swarm.public_endpoints import load_public_endpoints as _raw

        return _raw()
    except Exception:  # noqa: BLE001
        return None


def validate_scheduler_url(url: str) -> dict[str, Any]:
    from gpu_swarm.endpoints import validate_scheduler_url as _v

    return _v(url)


def auto_detect_scheduler_url(
    explicit: str | None = None,
    *,
    timeout: float = 2.5,
    probe: bool = True,
) -> dict[str, Any]:
    """Installer first-run: public_endpoints → Tailscale → localhost."""
    from gpu_swarm.endpoints import auto_detect_scheduler_url as _auto

    saved = load_joiner_settings().scheduler_url
    return _auto(explicit, saved=saved, timeout=timeout, probe=probe)


def connect_urls_for_ui() -> dict[str, Any]:
    from gpu_swarm.endpoints import connect_urls_for_ui as _urls

    return _urls()


def get_public_access_info() -> dict[str, Any]:
    """UI-safe public tunnel endpoints (from data/public_endpoints.json)."""
    pub = load_public_endpoints()
    if not pub:
        return {
            "active": False,
            "no_tailscale_needed": False,
            "portal_path": "",
            "pool_api_public_url": "",
            "portal_public_url": "",
            "message": "Public tunnel off — host: run start-public-access.cmd",
        }
    return {
        "active": True,
        "no_tailscale_needed": True,
        "portal_path": pub.get("portal_path") or "",
        "pool_api_public_url": pub.get("pool_api_public_url") or "",
        "portal_public_url": pub.get("portal_public_url") or "",
        "invite_code": PORTAL_INVITE_CODE,
        "note": pub.get("note") or PRIVATE_NETWORK_BLURB,
        "message": f"Public access ON — no Tailscale needed · {pub.get('portal_path')}",
    }


def scheduler_reachability_hint(
    *,
    ok: bool,
    url: str = "",
    error: str = "",
    tailscale_ipv4: str | None = None,
) -> str:
    """Actionable status text when testing the scheduler (public /pool-api, Tailscale, or LAN)."""
    pub = get_public_access_info()
    if ok:
        if "trycloudflare.com" in (url or "") or "/pool-api" in (url or ""):
            return f"Reachable via public tunnel (no Tailscale) · {url}"
        return f"Reachable on Tailscale/LAN · {url or DEFAULT_SCHEDULER_URL}"
    ts = tailscale_ipv4 if tailscale_ipv4 is not None else detect_tailscale_ipv4()
    lines = [
        "Cannot reach the scheduler yet.",
        "",
        PRIVATE_NETWORK_BLURB,
        "",
        "Do this:",
    ]
    if pub.get("active"):
        lines.append(f"1) Public portal (no Tailscale): {pub.get('portal_path')}")
        lines.append(f"2) Public pool API: {pub.get('pool_api_public_url')}")
        lines.append(f"3) Invite: {PORTAL_INVITE_CODE}")
        lines.append(f"4) Same PC as the host: {DEFAULT_LOCAL_SCHEDULER_URL}")
    else:
        lines.append("1) Ask the host for the public portal link (start-public-access.cmd), or")
        lines.append("2) Install Tailscale and join the private pool network")
        lines.append(f"3) Members Tailscale: {DEFAULT_SCHEDULER_URL}")
        lines.append(f"4) Same PC as the host: {DEFAULT_LOCAL_SCHEDULER_URL}")
        lines.append(f"5) Portal: {DEFAULT_PORTAL_URL} · invite: {PORTAL_INVITE_CODE}")
    if not ts and not pub.get("active"):
        lines.append("Tip: no Tailscale on this machine — use the host’s public portal URL instead.")
    elif ts:
        lines.append(f"This machine Tailscale IPv4: {ts}")
    if url:
        lines.append(f"Tried: {url}")
    if error:
        lines.append(f"Last error: {error}")
    return "\n".join(lines)


def get_share_pack() -> dict[str, Any]:
    """Copyable invite blurb + URLs for Share / Invite others (no secrets)."""
    from gpu_swarm.share_invite import build_share_pack

    return build_share_pack()


def get_friends_connect_text() -> str:
    """Short card text: how friends reach the pool (public first when live)."""
    pub = get_public_access_info()
    steps = list(FRIENDS_CONNECT_STEPS)
    if pub.get("active"):
        steps = [
            f"1) Open public portal (no Tailscale): {pub.get('portal_path')}",
            f"2) Sign in with invite {PORTAL_INVITE_CODE} + your display name",
            "3) Utilize (laptop/no GPU OK) or Contribute CPU with VRAM=0",
            f"4) Optional SDK: GPU_SWARM_SCHEDULER_URL={pub.get('pool_api_public_url')}",
            "5) Tailscale is optional while this tunnel is running",
        ]
    body = (
        "How friends connect\n"
        "\n"
        + "\n".join(steps)
        + "\n\n"
        + (pub.get("message") if pub.get("active") else PRIVATE_NETWORK_BLURB)
        + "\n"
    )
    if pub.get("active"):
        body += f"Public portal: {pub.get('portal_path')}\n"
        body += f"Pool API:      {pub.get('pool_api_public_url')}\n"
    body += f"Tailscale sched: {DEFAULT_SCHEDULER_URL}\n"
    body += f"Tailscale portal: {DEFAULT_PORTAL_URL}\n"
    return body

# One-stop wizard helper scripts (Windows). Prefer these paths from the UI/CLI.
SCRIPTS_DIR = BUNDLE_ROOT / "scripts"
SCRIPT_CHECK_PREREQS = SCRIPTS_DIR / "check_prereqs.ps1"
SCRIPT_INSTALL_JOINER_DEPS = SCRIPTS_DIR / "install_joiner_deps.ps1"
SCRIPT_INSTALL_PREREQS = SCRIPTS_DIR / "install-prereqs.ps1"
SCRIPT_CHECK_PREREQS_CMD = SCRIPTS_DIR / "check_prereqs.cmd"
SCRIPT_INSTALL_JOINER_DEPS_CMD = SCRIPTS_DIR / "install_joiner_deps.cmd"
SCRIPT_INSTALL_PREREQS_CMD = SCRIPTS_DIR / "install-prereqs.cmd"
CONNECTING_DOC = BUNDLE_ROOT / "CONNECTING.md"
LOCAL_MODEL_DOC = BUNDLE_ROOT / "LOCAL_MODEL.md"
ADVANCED_VM_DOC = BUNDLE_ROOT / "ADVANCED_VM.md"
CODING_AGENT_EXAMPLE = BUNDLE_ROOT / "examples" / "coding_agent_pool.py"
LOCAL_OFFLOAD_DOC = BUNDLE_ROOT / "examples" / "ollama_or_local_offload.md"

# Keys we may sync into .env — never touch Discord/bot secrets.
_SAFE_ENV_KEYS = (
    "GPU_SWARM_SCHEDULER_URL",
    "GPU_SWARM_WORKER_NAME",
    "GPU_SWARM_DISCORD_USER",
    "GPU_SWARM_MAX_VRAM_MB",
    "GPU_SWARM_MAX_CPU_PERCENT",
    "GPU_SWARM_MAX_RAM_MB",
    "GPU_SWARM_MAX_DISK_GB",
    "GPU_SWARM_HOST_PROTECT",
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
_local_endpoint_proc: subprocess.Popen[str] | None = None
_local_endpoint_log_handle: Any | None = None


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
    """Best-effort default without probing (public /pool-api → Tailscale → local)."""
    pub = get_public_access_info()
    if pub.get("active") and pub.get("pool_api_public_url"):
        return str(pub["pool_api_public_url"]).rstrip("/")
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
    ordered: list[str] = []
    pub = get_public_access_info()
    if pub.get("active") and pub.get("portal_path"):
        ordered.append(str(pub["portal_path"]))
    try:
        from gpu_swarm.endpoints import portal_url_candidates_extended

        for c in portal_url_candidates_extended():
            if c["url"] not in ordered:
                ordered.append(c["url"])
    except Exception:  # noqa: BLE001
        pass
    for legacy in portal_url_candidates():
        if legacy not in ordered:
            ordered.append(legacy)
    for candidate in ordered:
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
            f"1) Run start-portal.cmd on the host\n"
            f"2) Open {DEFAULT_LOCAL_PORTAL_URL} (same machine) or "
            f"{DEFAULT_PORTAL_URL} (Tailscale)\n"
            f"3) Sign in with invite code: {PORTAL_INVITE_CODE}"
        ),
    }


def get_portal_hints() -> dict[str, Any]:
    """UI-safe portal onboarding hints (invite code only — never pool password)."""
    resolved = resolve_portal_url()
    pub = get_public_access_info()
    preferred = ""
    if pub.get("active") and pub.get("portal_path"):
        preferred = str(pub["portal_path"])
    return {
        "invite_code": PORTAL_INVITE_CODE,
        "local_url": DEFAULT_LOCAL_PORTAL_URL,
        "tailscale_url": DEFAULT_PORTAL_URL,
        "public_url": preferred,
        "pool_api_public_url": pub.get("pool_api_public_url") or "",
        "no_tailscale_needed": bool(pub.get("active")),
        "public_access": pub,
        "url": preferred or resolved.get("url") or DEFAULT_LOCAL_PORTAL_URL,
        "reachable": bool(resolved.get("ok") or pub.get("active")),
        "message": (
            pub.get("message")
            if pub.get("active")
            else (resolved.get("message") or "")
        ),
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
        "required": False,
        "message": (
            "nvidia-smi found"
            if ok
            else "No NVIDIA — OK. Utilize the pool or contribute CPU (gpu_available=false)."
        ),
        "fix": (
            ""
            if ok
            else "Install NVIDIA drivers only if you want to Contribute a GPU. "
            "Laptops without a GPU should use Utilize-first."
        ),
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
    """Detect the Python runtime powering this app (+ portable/venv status)."""
    return detect_python_runtime()


def check_python_deps() -> dict[str, Any]:
    return python_deps_status()


def python_runtime_report() -> dict[str, Any]:
    from gpu_swarm.portable_python import python_runtime_report as _report

    return _report()


def ensure_portable_python(
    *,
    force_download: bool = False,
    with_venv: bool = True,
    with_requirements: bool = False,
    dry_run: bool = False,
    on_progress: Any | None = None,
) -> dict[str, Any]:
    """Bootstrap isolated CPython + venv under %LOCALAPPDATA%\\GPUPool\\."""
    from gpu_swarm.portable_python import ensure_portable_python as _ensure

    return _ensure(
        force_download=force_download,
        with_venv=with_venv,
        with_requirements=with_requirements,
        dry_run=dry_run,
        on_progress=on_progress,
    )


def bootstrap_portable_python(
    *,
    dry_run: bool = False,
    with_requirements: bool = True,
    on_progress: Any | None = None,
) -> dict[str, Any]:
    """Wizard/EXE entry: ensure portable Python + venv (+ optional requirements)."""
    return ensure_portable_python(
        force_download=False,
        with_venv=True,
        with_requirements=with_requirements and not dry_run,
        dry_run=dry_run,
        on_progress=on_progress,
    )


def collect_diagnostics(
    *,
    wizard_step: str | None = None,
    scheduler_url: str = "",
    portal_url: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from gpu_swarm.diagnostics import collect_diagnostics as _collect

    return _collect(
        wizard_step=wizard_step,
        scheduler_url=scheduler_url,
        portal_url=portal_url,
        extra=extra,
    )


def write_error_log(
    *,
    wizard_step: str | None = None,
    scheduler_url: str = "",
    portal_url: str = "",
    extra: dict[str, Any] | None = None,
    include_traceback: str | None = None,
    reason: str = "error",
) -> dict[str, Any]:
    from gpu_swarm.diagnostics import write_error_log as _write

    return _write(
        wizard_step=wizard_step,
        scheduler_url=scheduler_url,
        portal_url=portal_url,
        extra=extra,
        include_traceback=include_traceback,
        reason=reason,
    )


def submit_diagnostics(
    *,
    portal_url: str = "",
    log_path: str = "",
    text: str = "",
    display_name: str = "",
    invite_code: str = "",
) -> dict[str, Any]:
    from gpu_swarm.diagnostics import submit_diagnostics as _submit
    from gpu_swarm.joiner_settings import PORTAL_INVITE_CODE as _INVITE

    settings = load_joiner_settings()
    return _submit(
        portal_url=portal_url or settings.portal_url or DEFAULT_PORTAL_URL,
        log_path=log_path or None,
        text=text or None,
        display_name=display_name or settings.discord_user or settings.worker_name,
        invite_code=invite_code or _INVITE,
    )


def copy_diagnostics_text(
    *,
    wizard_step: str | None = None,
    scheduler_url: str = "",
    portal_url: str = "",
    write_file: bool = True,
) -> dict[str, Any]:
    """Collect diagnostics; optionally write error-*.log; return text for clipboard."""
    settings = load_joiner_settings()
    if write_file:
        written = write_error_log(
            wizard_step=wizard_step,
            scheduler_url=scheduler_url or settings.scheduler_url,
            portal_url=portal_url or settings.portal_url,
            reason="manual",
        )
        return {
            "ok": bool(written.get("ok")),
            "text": written.get("text") or "",
            "path": written.get("path") or "",
            "message": written.get("message") or "Diagnostics ready",
        }
    from gpu_swarm.diagnostics import collect_diagnostics as _collect
    from gpu_swarm.diagnostics import format_diagnostics_text

    payload = _collect(
        wizard_step=wizard_step,
        scheduler_url=scheduler_url or settings.scheduler_url,
        portal_url=portal_url or settings.portal_url,
    )
    text = format_diagnostics_text(payload)
    return {"ok": True, "text": text, "path": "", "message": "Diagnostics text ready"}


def zip_error_log(log_path: str) -> dict[str, Any]:
    from gpu_swarm.diagnostics import zip_error_log as _zip

    return _zip(log_path)


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


def install_requirements(
    *,
    force: bool = False,
    on_progress: Any | None = None,
) -> dict[str, Any]:
    """
    Install from requirements.txt only when deps are missing (avoid reinstall loops).
    Prefers isolated venv under %LOCALAPPDATA%\\GPUPool\\venv (never global site-packages
    when portable bootstrap is available). Pass force=True to repair/upgrade.
    """
    from gpu_swarm.portable_python import (
        STEP_INSTALL_DEPS,
        _emit,
        install_requirements_into_venv,
        resolve_pip_python,
        venv_python_exe,
    )

    if is_frozen():
        _emit(
            on_progress,
            "GPUPool.exe already includes the app runtime — skipping pip install.",
            percent=100,
            skipped=True,
        )
        return {
            "ok": True,
            "message": (
                "GPUPool.exe already bundles the desktop + worker runtime. "
                "Optional CUDA torch uses portable Python under %LOCALAPPDATA%\\GPUPool\\ "
                "(Bootstrap portable Python, then Install CUDA PyTorch)."
            ),
            "skipped": True,
            "frozen": True,
            "missing": [],
        }
    status = check_python_deps()
    if status.get("ok") and not force:
        _emit(
            on_progress,
            "Dependencies already installed — skipping reinstall.",
            percent=100,
            skipped=True,
        )
        return {
            "ok": True,
            "message": "Dependencies already satisfied — skipped full reinstall.",
            "skipped": True,
            "missing": [],
        }
    req = BUNDLE_ROOT / "requirements-joiner.txt"
    if not req.is_file():
        req = BUNDLE_ROOT / "requirements.txt"
    if not req.is_file():
        req = ROOT / "requirements-joiner.txt"
    if not req.is_file():
        req = ROOT / "requirements.txt"
    if not req.is_file():
        return {
            "ok": False,
            "message": f"Missing requirements-joiner.txt / requirements.txt",
            "fix": "Restore requirements-joiner.txt in the repo root.",
        }
    missing = status.get("missing") or []
    pip_py = resolve_pip_python() or sys.executable
    use_venv = venv_python_exe().is_file() and Path(pip_py).resolve() == venv_python_exe().resolve()

    # Prefer streaming installer into isolated venv (visible package progress).
    if use_venv:
        result = install_requirements_into_venv(
            requirements=req,
            dry_run=False,
            on_progress=on_progress,
        )
        after = check_python_deps()
        if result.get("ok") and after.get("ok"):
            return {
                "ok": True,
                "message": result.get("message") or "Installed requirements successfully.",
                "code": result.get("code"),
                "missing_before": missing,
                "pip_python": pip_py,
                "isolated_venv": True,
            }
        still = after.get("missing") or missing
        return {
            "ok": False,
            "message": result.get("message") or "pip failed",
            "code": result.get("code"),
            "missing": still,
            "pip_python": pip_py,
            "fix": result.get("fix")
            or (
                f"Still missing: {', '.join(still)}\n"
                "If system Python is broken, Bootstrap portable Python first.\n"
                f'Fix: "{pip_py}" -m pip install -r "{req}"'
            ),
        }

    # System Python fallback: stream pip so the wizard log stays alive.
    _emit(on_progress, f"{STEP_INSTALL_DEPS} (system Python)", percent=0)
    cmd = [pip_py, "-m", "pip", "install", "--user", "-r", str(req), "--progress-bar", "on"]
    lines: list[str] = []
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(ROOT),
            **popen_kwargs(),
        )
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip()
            if line:
                lines.append(line)
                _emit(on_progress, STEP_INSTALL_DEPS, package=line[:90], line=line)
        code = proc.wait(timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "message": str(exc),
            "fix": (
                "Bootstrap portable Python, then retry Install. "
                f'Manual: "{pip_py}" -m pip install -r requirements.txt'
            ),
        }
    ok = code == 0
    tail = "\n".join(lines)[-1200:]
    after = check_python_deps()
    if ok and after.get("ok"):
        _emit(on_progress, "Dependencies installed.", percent=100)
        return {
            "ok": True,
            "message": tail or "Installed requirements successfully.",
            "code": code,
            "missing_before": missing,
            "pip_python": pip_py,
            "isolated_venv": False,
        }
    still = after.get("missing") or missing
    return {
        "ok": False,
        "message": tail or "pip failed",
        "code": code,
        "missing": still,
        "pip_python": pip_py,
        "fix": (
            f"Still missing: {', '.join(still)}\n"
            "If system Python is broken, Bootstrap portable Python first.\n"
            f'Fix: "{pip_py}" -m pip install --user -r "{req}"'
        ),
    }


def _resolve_system_python() -> str | None:
    """Find a non-frozen Python 3.10+ for optional pip installs (venv > portable > system)."""
    from gpu_swarm.portable_python import resolve_pip_python

    return resolve_pip_python()


def install_torch_cuda(
    *,
    index_url: str = "https://download.pytorch.org/whl/cu124",
    on_progress: Any | None = None,
) -> dict[str, Any]:
    """
    Optional large download — only call after explicit user consent in the UI.
    Installs torch/torchvision/torchaudio from the CUDA wheel index into the
    isolated venv when available (never into the frozen EXE).
    """
    from gpu_swarm.portable_python import _emit, resolve_pip_python, venv_python_exe

    py = resolve_pip_python()
    if is_frozen() and not py:
        # Auto-bootstrap portable Python so friends don't need a system install.
        _emit(on_progress, "Preparing portable Python for CUDA torch…", percent=5)
        boot = ensure_portable_python(
            with_venv=True,
            with_requirements=False,
            dry_run=False,
            on_progress=on_progress,
        )
        if boot.get("ok") and not boot.get("dry_run"):
            py = resolve_pip_python()
        if not py:
            return {
                "ok": False,
                "message": "CUDA torch is not bundled in GPUPool.exe (too large).",
                "fix": (
                    "Click “Bootstrap portable Python” first (installs isolated CPython under "
                    "%LOCALAPPDATA%\\GPUPool\\), then retry Install CUDA PyTorch.\n"
                    "Probe jobs and pool join work without torch; pytorch_cuda_probe needs it."
                ),
                "frozen": True,
                "bootstrap": boot,
            }
    if not py:
        py = sys.executable
    use_venv = venv_python_exe().is_file() and Path(py).resolve() == venv_python_exe().resolve()
    _emit(
        on_progress,
        "Downloading CUDA PyTorch (large — several GB; keep this window open)…",
        percent=10,
        package="torch",
    )
    cmd = [py, "-m", "pip", "install"]
    if not use_venv:
        cmd.append("--user")
    cmd.extend(
        [
            "torch",
            "torchvision",
            "torchaudio",
            "--index-url",
            index_url,
            "--progress-bar",
            "on",
        ]
    )
    lines: list[str] = []
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(ROOT),
            **popen_kwargs(),
        )
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip()
            if not line:
                continue
            lines.append(line)
            pkg = "torch"
            low = line.lower()
            for name in ("torchvision", "torchaudio", "torch"):
                if name in low:
                    pkg = name
                    break
            _emit(
                on_progress,
                "Installing CUDA PyTorch…",
                package=pkg,
                line=line[:120],
            )
        code = proc.wait(timeout=1800)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "message": str(exc),
            "fix": " ".join(cmd),
        }
    ok = code == 0
    tail = "\n".join(lines)[-1200:]
    status = check_torch_cuda()
    if ok:
        _emit(on_progress, "CUDA PyTorch install finished.", percent=100)
        return {
            "ok": True,
            "message": tail or "PyTorch install finished.",
            "torch": status,
            "code": code,
        }
    return {
        "ok": False,
        "message": tail or "PyTorch install failed",
        "code": code,
        "fix": (
            f'Retry: "{py}" -m pip install'
            f'{" --user" if not use_venv else ""} torch torchvision torchaudio '
            f"--index-url {index_url}"
        ),
        "torch": status,
    }


def script_paths() -> dict[str, str]:
    """Documented paths the wizard / operators can invoke on Windows."""
    return {
        "scripts_dir": str(SCRIPTS_DIR),
        "check_prereqs_ps1": str(SCRIPT_CHECK_PREREQS),
        "check_prereqs_cmd": str(SCRIPT_CHECK_PREREQS_CMD),
        "install_joiner_deps_ps1": str(SCRIPT_INSTALL_JOINER_DEPS),
        "install_joiner_deps_cmd": str(SCRIPT_INSTALL_JOINER_DEPS_CMD),
        "install_prereqs_ps1": str(SCRIPT_INSTALL_PREREQS),
        "install_prereqs_cmd": str(SCRIPT_INSTALL_PREREQS_CMD),
    }


def _run_powershell(script: Path, args: list[str] | None = None, timeout: float = 600.0) -> dict[str, Any]:
    """Run a repo PowerShell helper; return ok/code/stdout/stderr (never touches Discord)."""
    if not script.is_file():
        return {
            "ok": False,
            "code": 127,
            "stdout": "",
            "stderr": f"Missing script: {script}",
            "script": str(script),
        }
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]
    if args:
        cmd.extend(args)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=str(ROOT),
            **run_kwargs(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "code": -1, "stdout": "", "stderr": str(exc), "script": str(script)}
    return {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "script": str(script),
    }


def _parse_json_tail(text: str) -> Any | None:
    blob = (text or "").strip()
    if not blob:
        return None
    # Scripts may print progress lines before the JSON object.
    start = blob.find("{")
    end = blob.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return json.loads(blob[start : end + 1])
    except json.JSONDecodeError:
        return None


def check_prereqs(
    scheduler_url: str | None = None,
    *,
    min_disk_gb: float = 5.0,
    prefer_script: bool = True,
) -> dict[str, Any]:
    """
    One-stop prereq probe: python, nvidia-smi, scheduler reachable, disk space.
    Prefer scripts/check_prereqs.ps1; fall back to in-process checks.
    """
    if not scheduler_url:
        detected = auto_detect_scheduler_url(probe=True, timeout=2.0)
        url = (detected.get("url") or DEFAULT_LOCAL_SCHEDULER_URL).rstrip("/")
    else:
        url = scheduler_url.rstrip('/')

    if prefer_script and SCRIPT_CHECK_PREREQS.is_file():
        raw = _run_powershell(
            SCRIPT_CHECK_PREREQS,
            args=["-SchedulerUrl", url, "-MinDiskGb", str(min_disk_gb), "-Json"],
            timeout=60.0,
        )
        parsed = _parse_json_tail(raw.get("stdout") or "")
        if isinstance(parsed, dict):
            parsed.setdefault("source", "scripts/check_prereqs.ps1")
            parsed.setdefault("script", script_paths())
            parsed["nvidia_required"] = False
            return parsed

    # In-process fallback (same fields; real probes)
    py_ok = True
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    nvidia = check_nvidia()
    sched = fetch_scheduler_status(url, timeout=5.0)
    host = detect_host_resources()
    free_gb = float(host.get("free_disk_gb") or 0)
    disk_ok = free_gb >= float(min_disk_gb)
    overall = bool(py_ok and sched.get("ok") and disk_ok)  # NVIDIA optional
    gpus_raw = detect_gpus().get("gpus") or []
    gpu_names = [
        (g.get("name", str(g)) if isinstance(g, dict) else str(g)) for g in gpus_raw
    ]
    return {
        "ok": overall,
        "repo_root": str(ROOT),
        "python": {"ok": py_ok, "exe": sys.executable, "version": py_ver, "path": sys.executable},
        "nvidia_smi": {
            "ok": bool(nvidia.get("ok")),
            "path": nvidia.get("path") or "",
            "message": nvidia.get("message") or "",
            "gpus": gpu_names,
        },
        "scheduler": {
            "ok": bool(sched.get("ok")),
            "url": sched.get("url") or url,
            "message": "Scheduler reachable" if sched.get("ok") else (sched.get("error") or "unreachable"),
        },
        "disk": {
            "ok": disk_ok,
            "free_gb": free_gb,
            "total_gb": float(host.get("total_disk_gb") or 0),
            "min_disk_gb": min_disk_gb,
            "message": f"Disk {'OK' if disk_ok else 'LOW'}: {free_gb} GiB free",
        },
        "source": "app_backend.check_prereqs",
        "script": script_paths(),
    }


def install_prereqs(
    *,
    detect_only: bool = False,
    skip_tailscale: bool = False,
    skip_virtualbox: bool = False,
    skip_vagrant: bool = False,
    connect_tailscale: bool = False,
    prefer_script: bool = True,
    timeout: float = 1800.0,
) -> dict[str, Any]:
    """
    Detect/install Tailscale + optional VirtualBox/Vagrant (Workspace).
    Prefer scripts/install-prereqs.ps1. Never reads or writes Discord secrets.
    Tailscale auth key only via process env TS_AUTHKEY / GPU_SWARM_TAILSCALE_AUTHKEY.
    """
    if prefer_script and SCRIPT_INSTALL_PREREQS.is_file():
        args: list[str] = ["-Json"]
        if detect_only:
            args.append("-DetectOnly")
        if skip_tailscale:
            args.append("-SkipTailscale")
        if skip_virtualbox:
            args.append("-SkipVirtualBox")
        if skip_vagrant:
            args.append("-SkipVagrant")
        if connect_tailscale:
            args.append("-ConnectTailscale")
        raw = _run_powershell(SCRIPT_INSTALL_PREREQS, args=args, timeout=timeout)
        parsed = _parse_json_tail(raw.get("stdout") or "")
        if isinstance(parsed, dict):
            parsed.setdefault("source", "scripts/install-prereqs.ps1")
            parsed.setdefault("script", script_paths())
            parsed["raw_code"] = raw.get("code")
            # Surface progress text for the wizard log (JSON stripped from tip).
            stdout = raw.get("stdout") or ""
            tip = stdout
            brace = tip.rfind("{")
            if brace > 0:
                tip = tip[:brace].strip()
            if tip:
                parsed["log_text"] = tip[-4000:]
            return parsed
        return {
            "ok": bool(raw.get("ok")),
            "message": (raw.get("stderr") or raw.get("stdout") or "install-prereqs failed")[-800:],
            "code": raw.get("code"),
            "source": "scripts/install-prereqs.ps1",
            "script": script_paths(),
            "log_text": (raw.get("stdout") or "")[-4000:],
        }

    return {
        "ok": False,
        "message": f"Missing {SCRIPT_INSTALL_PREREQS} — clone full repo or run from source",
        "source": "app_backend.install_prereqs",
    }


def install_joiner_deps(
    *,
    with_torch_cuda: bool = False,
    force: bool = False,
    prefer_script: bool = True,
    timeout: float = 900.0,
) -> dict[str, Any]:
    """
    Idempotent joiner dependency install.
    Prefer scripts/install_joiner_deps.ps1; fall back to install_requirements().
    Optional torch CUDA is only installed when with_torch_cuda=True.
    """
    if prefer_script and SCRIPT_INSTALL_JOINER_DEPS.is_file():
        args: list[str] = []
        if with_torch_cuda:
            args.append("-WithTorchCuda")
        if force:
            args.append("-Force")
        raw = _run_powershell(SCRIPT_INSTALL_JOINER_DEPS, args=args, timeout=timeout)
        parsed = _parse_json_tail(raw.get("stdout") or "")
        if isinstance(parsed, dict):
            parsed.setdefault("source", "scripts/install_joiner_deps.ps1")
            parsed.setdefault("script", script_paths())
            parsed["raw_code"] = raw.get("code")
            return parsed
        if raw.get("ok"):
            return {
                "ok": True,
                "message": (raw.get("stdout") or "")[-800:] or "install script OK",
                "source": "scripts/install_joiner_deps.ps1",
                "script": script_paths(),
            }
        return {
            "ok": False,
            "message": (raw.get("stderr") or raw.get("stdout") or "install script failed")[-800:],
            "code": raw.get("code"),
            "source": "scripts/install_joiner_deps.ps1",
            "script": script_paths(),
        }

    base = install_requirements()
    result: dict[str, Any] = {
        "ok": bool(base.get("ok")),
        "message": base.get("message"),
        "skipped": base.get("skipped"),
        "actions": ["install_requirements_fallback"],
        "with_torch_cuda": with_torch_cuda,
        "source": "app_backend.install_requirements",
        "script": script_paths(),
    }
    if with_torch_cuda:
        try:
            import torch  # type: ignore

            cuda_ok = bool(torch.cuda.is_available())
            result["torch"] = {"ok": cuda_ok, "message": f"torch {torch.__version__} cuda={cuda_ok}"}
            if not cuda_ok:
                result["ok"] = False
                result["message"] = (
                    (result.get("message") or "")
                    + " | torch present but CUDA unavailable — re-run scripts/install_joiner_deps.ps1 -WithTorchCuda"
                )
        except ImportError:
            result["ok"] = False
            result["torch"] = {"ok": False, "message": "torch not installed"}
            result["message"] = (
                (result.get("message") or "")
                + " | torch missing — run scripts/install_joiner_deps.ps1 -WithTorchCuda"
            )
    return result

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
    Tries: explicit → env → public_endpoints (/pool-api) → saved → Tailscale → localhost.
    """
    from gpu_swarm.endpoints import scheduler_url_candidates

    if url:
        v = validate_scheduler_url(url)
        if not v.get("ok"):
            ts = get_tailscale_ipv4()
            return {
                "ok": False,
                "url": url,
                "error": v.get("error") or "Incorrect Scheduler URL Environment Variable",
                "data": None,
                "attempts": [{"url": url, "ok": False, "error": v.get("error") or ""}],
                "tailscale_ipv4": ts,
                "suggested": v.get("suggested") or "",
                "hint": v.get("hint")
                or scheduler_reachability_hint(ok=False, url=url, tailscale_ipv4=ts),
            }

    settings = load_joiner_settings()
    candidates = [
        c["url"]
        for c in scheduler_url_candidates(url, include_saved=settings.scheduler_url or None)
    ]
    pub = get_public_access_info()
    if pub.get("active") and pub.get("pool_api_public_url"):
        candidates.insert(0, str(pub["pool_api_public_url"]).rstrip("/"))

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
            ts = get_tailscale_ipv4()
            if candidate != (settings.scheduler_url or "").rstrip("/"):
                try:
                    settings.scheduler_url = candidate
                    save_joiner_settings(settings)
                except Exception:  # noqa: BLE001
                    pass
            return {
                "ok": True,
                "url": candidate,
                "error": "",
                "data": result.get("data"),
                "attempts": attempts,
                "tailscale_ipv4": ts,
                "hint": scheduler_reachability_hint(ok=True, url=candidate, tailscale_ipv4=ts),
            }

    ts = get_tailscale_ipv4()
    fail_url = candidates[0] if candidates else ""
    fail_err = attempts[-1]["error"] if attempts else "No scheduler URL to try"
    return {
        "ok": False,
        "url": fail_url,
        "error": fail_err,
        "data": None,
        "attempts": attempts,
        "tailscale_ipv4": ts,
        "hint": scheduler_reachability_hint(
            ok=False, url=fail_url, error=fail_err, tailscale_ipv4=ts
        ),
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


def _diagnostics_for_join_failure(
    *,
    message: str,
    settings: JoinerSettings,
    fix: str = "",
    wizard_step: str = "Join",
    log_tail: str = "",
    exc: BaseException | None = None,
) -> dict[str, Any]:
    """Write submitable error-*.log when join/install fails."""
    try:
        from gpu_swarm.diagnostics import record_failure_and_write

        return record_failure_and_write(
            message=message,
            wizard_step=wizard_step,
            scheduler_url=settings.scheduler_url,
            portal_url=settings.portal_url,
            fix=fix,
            log_tail=log_tail,
            exc=exc,
        )
    except Exception as diag_exc:  # noqa: BLE001
        return {"ok": False, "message": f"diagnostics unavailable: {diag_exc}"}


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
        hint = sched.get("hint") or scheduler_reachability_hint(
            ok=False,
            url=settings.scheduler_url,
            error=str(sched.get("error") or ""),
            tailscale_ipv4=sched.get("tailscale_ipv4"),
        )
        diag = _diagnostics_for_join_failure(
            message="scheduler unreachable",
            settings=settings,
            fix=hint,
            wizard_step="Join",
        )
        return {
            "ok": False,
            "message": "Cannot reach Tailscale/LAN scheduler yet (install/login Tailscale + join the private pool network).",
            "pid": None,
            "fix": hint,
            "scheduler": sched,
            "diagnostics": diag,
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
    host_protect = bool(getattr(settings, "host_protect", True))
    env["GPU_SWARM_HOST_PROTECT"] = "1" if host_protect else "0"
    disk_mb = int(float(getattr(settings, "max_disk_gb", 0) or 0) * 1024)
    if disk_mb > 0:
        env["GPU_SWARM_MAX_DISK_MB"] = str(disk_mb)
    # Separate id file so desktop joiner does not clash with start-worker.cmd
    env["GPU_SWARM_WORKER_ID_FILE"] = str(JOINER_WORKER_ID_FILE)

    if is_frozen():
        # Re-launch this EXE in worker mode (same bundle; no system Python required).
        cmd = [
            sys.executable,
            "--worker",
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
    else:
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
    cmd.append("--host-protect" if host_protect else "--no-host-protect")
    if settings.discord_user:
        cmd.extend(["--discord-user", settings.discord_user])

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
            **popen_kwargs(new_group=True),
        )
    except OSError as exc:
        _worker_proc = None
        fix = (
            f"Could not spawn worker. Check Python: {sys.executable}. "
            "If system Python is broken, Bootstrap portable Python in the wizard."
        )
        diag = _diagnostics_for_join_failure(
            message=str(exc),
            settings=settings,
            fix=fix,
            wizard_step="Join",
            exc=exc,
        )
        return {
            "ok": False,
            "message": str(exc),
            "pid": None,
            "fix": fix,
            "diagnostics": diag,
        }

    _write_pid_file(_worker_proc.pid)
    time.sleep(0.5)
    if _worker_proc.poll() is not None:
        code = _worker_proc.returncode
        _worker_proc = None
        _clear_pid_file()
        log_tail = _tail_log(40)
        fix = f"Open {LOG_FILE} for the exact traceback, then fix and Join again."
        diag = _diagnostics_for_join_failure(
            message=f"Worker exited immediately (code={code})",
            settings=settings,
            fix=fix,
            wizard_step="Join",
            log_tail=log_tail,
        )
        return {
            "ok": False,
            "message": f"Worker exited immediately (code={code}). See {LOG_FILE}",
            "pid": None,
            "log": str(LOG_FILE),
            "log_tail": log_tail,
            "fix": fix,
            "diagnostics": diag,
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


def list_allowed_jobs() -> list[dict[str, Any]]:
    """Safe allowlisted job catalog for Utilize UI (no arbitrary shell)."""
    from gpu_swarm import ALLOWED_JOB_TYPES

    catalog = [
        {
            "job_type": "probe",
            "title": "GPU probe",
            "summary": "Live nvidia-smi inventory from an online worker. Proves network + lease path.",
            "require_gpu": False,
            "discord": "/submit_probe",
            "safe": True,
        },
        {
            "job_type": "pytorch_cuda_probe",
            "title": "CUDA matmul probe",
            "summary": "Small real PyTorch CUDA matmul on a worker GPU (falls back to CPU note if no CUDA).",
            "require_gpu": True,
            "discord": "/submit_compute",
            "safe": True,
            "payload_defaults": {"matrix_size": 1024},
        },
        {
            "job_type": "llm_chat",
            "title": "Local model chat (via pool)",
            "summary": (
                "Chat completions on a contributor worker that runs Ollama / OpenAI-compatible "
                "runtime. Prefer the Local Pool Endpoint (Connect → Start local model endpoint)."
            ),
            "require_gpu": False,
            "discord": "(use local endpoint / SDK)",
            "safe": True,
            "payload_defaults": {
                "model": "gpu-pool",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 256,
            },
        },
    ]
    return [j for j in catalog if j["job_type"] in ALLOWED_JOB_TYPES]


def pool_status(scheduler_url: str | None = None, timeout: float = 5.0) -> dict[str, Any]:
    """Utilize view: workers online, GPUs, CPU/RAM/disk ads, job counts."""
    fetched = fetch_scheduler_status(scheduler_url, timeout=timeout)
    data = fetched.get("data") or {}
    workers = data.get("workers") or []
    online = [w for w in workers if w.get("online") or str(w.get("status", "")).lower() in ("online", "busy")]
    ok = bool(fetched.get("ok"))
    url = fetched.get("url") or ""
    err = fetched.get("error") or ""
    ts = get_tailscale_ipv4()
    return {
        "ok": ok,
        "url": url,
        "error": err,
        "tailscale_ipv4": ts,
        "hint": scheduler_reachability_hint(ok=ok, url=url, error=err, tailscale_ipv4=ts),
        "private_network": PRIVATE_NETWORK_BLURB,
        "workers_online": int(data.get("workers_online") or len(online)),
        "workers_total": int(data.get("workers_total") or len(workers)),
        "free_vram_mb": int(data.get("free_vram_mb") or 0),
        "total_vram_mb": int(data.get("total_vram_mb") or 0),
        "cpu_cores": int(data.get("cpu_cores") or 0),
        "ram_available_mb": int(data.get("ram_available_mb") or 0),
        "ram_total_mb": int(data.get("ram_total_mb") or 0),
        "disk_free_mb": int(data.get("disk_free_mb") or 0),
        "dedicated_ram_mb": int(data.get("dedicated_ram_mb") or 0),
        "dedicated_disk_mb": int(data.get("dedicated_disk_mb") or 0),
        "gpus": list(data.get("gpus") or []),
        "jobs": dict(data.get("jobs") or {}),
        "workers": workers,
        "capacity_note": data.get("capacity_note")
        or (
            "v1 contributes compute to JOBS (GPU/CPU). RAM/SSD figures are capacity "
            "advertisements — not a literal distributed filesystem yet."
        ),
        "allowed_jobs": list_allowed_jobs(),
    }


def submit_job(
    job_type: str,
    *,
    scheduler_url: str | None = None,
    payload: dict[str, Any] | None = None,
    submitted_by: str | None = None,
    min_vram_mb: int = 0,
    require_gpu: bool | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """POST allowlisted job to live scheduler. Real HTTP — no mocks."""
    import httpx
    from gpu_swarm import ALLOWED_JOB_TYPES

    jt = (job_type or "").strip()
    if jt not in ALLOWED_JOB_TYPES:
        return {
            "ok": False,
            "error": f"job_type not allowlisted. Allowed: {sorted(ALLOWED_JOB_TYPES)}",
            "job": None,
        }

    settings = load_joiner_settings()
    base = (scheduler_url or settings.scheduler_url or DEFAULT_LOCAL_SCHEDULER_URL).rstrip("/")
    body_payload = dict(payload or {})
    if jt == "pytorch_cuda_probe" and "matrix_size" not in body_payload:
        body_payload["matrix_size"] = 1024
    gpu_required = bool(require_gpu) if require_gpu is not None else (jt == "pytorch_cuda_probe")
    by = (submitted_by or settings.discord_user or settings.worker_name or "desktop-app").strip()
    body = {
        "job_type": jt,
        "payload": body_payload,
        "require_gpu": gpu_required,
        "min_vram_mb": int(min_vram_mb or 0),
        "submitted_by": by,
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(f"{base}/jobs", json=body)
            if r.status_code >= 400:
                detail = ""
                try:
                    detail = str(r.json().get("detail") or r.text)
                except Exception:  # noqa: BLE001
                    detail = r.text
                return {
                    "ok": False,
                    "error": detail or f"HTTP {r.status_code}",
                    "job": None,
                    "url": base,
                }
            job = r.json()
        return {
            "ok": True,
            "error": "",
            "job": job,
            "job_id": job.get("id"),
            "url": base,
            "message": f"Queued {jt} job {job.get('id')}",
            "discord": discord_slash_for_job(jt, job.get("id")),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "job": None, "url": base}


def get_job(job_id: str, *, scheduler_url: str | None = None, timeout: float = 15.0) -> dict[str, Any]:
    """GET job status/result from live scheduler."""
    import httpx

    jid = (job_id or "").strip()
    if not jid:
        return {"ok": False, "error": "job_id required", "job": None}
    settings = load_joiner_settings()
    base = (scheduler_url or settings.scheduler_url or DEFAULT_LOCAL_SCHEDULER_URL).rstrip("/")
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(f"{base}/jobs/{jid}")
            if r.status_code == 404:
                return {"ok": False, "error": "job not found", "job": None, "url": base}
            r.raise_for_status()
            job = r.json()
        return {
            "ok": True,
            "error": "",
            "job": job,
            "job_id": job.get("id") or jid,
            "status": job.get("status"),
            "url": base,
            "discord": discord_slash_for_job(str(job.get("job_type") or ""), jid),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "job": None, "url": base}


def wait_for_job(
    job_id: str,
    *,
    scheduler_url: str | None = None,
    timeout_sec: float = 90.0,
    poll_sec: float = 1.0,
) -> dict[str, Any]:
    """Poll get_job until completed/failed or timeout."""
    deadline = time.time() + max(1.0, timeout_sec)
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = get_job(job_id, scheduler_url=scheduler_url)
        if not last.get("ok"):
            return last
        st = str((last.get("job") or {}).get("status") or "")
        if st in ("completed", "failed"):
            last["finished"] = True
            last["ok"] = st == "completed"
            if st == "failed":
                last["error"] = (last.get("job") or {}).get("error") or "job failed"
            return last
        time.sleep(max(0.2, poll_sec))
    last = last or get_job(job_id, scheduler_url=scheduler_url)
    last["finished"] = False
    last["ok"] = False
    last["error"] = last.get("error") or f"timeout waiting for job {job_id}"
    return last


def discord_slash_for_job(job_type: str, job_id: str | None = None) -> str:
    jt = (job_type or "").strip()
    if jt == "probe":
        submit = "/submit_probe"
    elif jt == "pytorch_cuda_probe":
        submit = "/submit_compute"
    else:
        submit = f"(allowlisted: {jt or 'n/a'})"
    lines = [submit]
    if job_id:
        lines.append(f"/job_status {job_id}")
    return "\n".join(lines)


def get_utilize_helper_text() -> str:
    jobs = list_allowed_jobs()
    lines = [
        "What can I run on the pool?",
        "",
        "Only allowlisted jobs — no arbitrary shell from the app, Discord, or portal.",
        "",
    ]
    for j in jobs:
        lines.append(f"• {j['title']} (`{j['job_type']}`)")
        lines.append(f"  {j['summary']}")
        lines.append(f"  Discord: {j.get('discord')}")
        lines.append("")
    lines += [
        "Pool status Discord: /pool  ·  /workers",
        "Job check: /job_status <id>",
        "",
        "RAM/SSD numbers are capacity ads for scheduling — not a shared drive/memory pool.",
    ]
    return "\n".join(lines)


def open_repo_doc(path: str | Path) -> dict[str, Any]:
    """Open a repo doc/example (or folder) in the OS default app / Explorer."""
    import webbrowser

    p = Path(path)
    if not p.exists():
        return {"ok": False, "path": str(p), "message": f"Missing path: {p}"}
    try:
        if sys.platform == "win32":
            os.startfile(str(p))  # type: ignore[attr-defined]
        else:
            webbrowser.open(p.as_uri())
        label = p.name if p.name else str(p)
        return {"ok": True, "path": str(p), "message": f"Opened {label}"}
    except OSError as exc:
        return {"ok": False, "path": str(p), "message": str(exc)}


def get_connect_from_code_text(scheduler_url: str | None = None) -> str:
    """Snippets pointing at CONNECTING.md + examples/coding_agent_pool.py."""
    settings = load_joiner_settings()
    hints = get_portal_hints()
    pub = get_public_access_info()
    if scheduler_url:
        base = scheduler_url.rstrip("/")
    elif pub.get("active") and pub.get("pool_api_public_url"):
        base = str(pub["pool_api_public_url"]).rstrip("/")
    else:
        base = (settings.scheduler_url or DEFAULT_SCHEDULER_URL).rstrip("/")
    portal = (
        hints.get("public_url")
        or hints.get("tailscale_url")
        or DEFAULT_PORTAL_URL
    )
    doc = CONNECTING_DOC
    example = CODING_AGENT_EXAMPLE
    offload = LOCAL_OFFLOAD_DOC
    public_line = ""
    if pub.get("active"):
        public_line = (
            f"Portal (public, no Tailscale): {portal}\n"
            f"Pool API (public /pool-api): {pub.get('pool_api_public_url')}\n"
        )
    return (
        "# Connect from code — verified paths\n"
        "\n"
        f"Docs:     {doc}\n"
        f"Example:  {example}\n"
        f"Local LLMs: {LOCAL_MODEL_DOC}  (pool as a local OpenAI endpoint)\n"
        f"Legacy notes: {offload}\n"
        "\n"
        f"GPU_SWARM_SCHEDULER_URL={base}\n"
        f"{public_line}"
        f"Portal (Tailscale): {DEFAULT_PORTAL_URL}\n"
        f"Invite: {PORTAL_INVITE_CODE}\n"
        "\n"
        "# 0) Local model endpoint (Open WebUI / LM Studio / Continue / Cursor)\n"
        "python -m gpu_swarm local-endpoint\n"
        f"set OPENAI_BASE_URL={DEFAULT_OPENAI_BASE_URL}\n"
        f"# URL to paste: {DEFAULT_OPENAI_BASE_URL}\n"
        "\n"
        "# 1) Python SDK (same HTTP: POST /jobs, GET /status)\n"
        "from gpu_swarm.client import GPUPool\n"
        f'pool = GPUPool("{base}")\n'
        "print(pool.status()[\"workers_online\"])\n"
        "print(pool.submit_probe(wait=True)[\"status\"])\n"
        "\n"
        "# 2) Coding-agent helper (stdlib only)\n"
        "cd /d C:\\Users\\Drew\\Projects\\gpu-swarm\n"
        f"set GPU_SWARM_SCHEDULER_URL={base}\n"
        "python examples\\coding_agent_pool.py --status-only\n"
        "python examples\\coding_agent_pool.py --job probe\n"
        "python examples\\use_pool_from_script.py --cuda\n"
        "\n"
        "# 3) CLI utilize\n"
        "python -m gpu_swarm utilize status\n"
        "python -m gpu_swarm utilize probe --wait\n"
        "python -m gpu_swarm utilize cuda --wait\n"
        "\n"
        "# 4) HTTP (any language)\n"
        f"GET  {base}/status\n"
        f"POST {base}/jobs   body: {{\"job_type\":\"probe\",\"payload\":{{}},\"submitted_by\":\"my-tool\"}}\n"
        f"GET  {base}/jobs/<id>\n"
        "\n"
        "# Read the full Contribute / Utilize / Connect map:\n"
        "  CONNECTING.md · LOCAL_MODEL.md\n"
        f"# {PRIVATE_NETWORK_BLURB}\n"
        "# No Docker. No arbitrary shell.\n"
    )


def get_discord_helper_text() -> str:
    hints = get_portal_hints()
    return (
        "Glitch Factor — GPU Pool Discord commands\n"
        "\n"
        "Contribute (join the pool):\n"
        "  /contribute   How to contribute / soft caps\n"
        "\n"
        "Utilize (send work to the pool):\n"
        "  /pool         Pool overview (workers + VRAM + host metrics)\n"
        "  /workers      List workers\n"
        "  /submit_probe Submit a live GPU probe job\n"
        "  /submit_compute  CUDA matmul probe\n"
        "  /job_status   Check a job by id\n"
        "\n"
        "Desktop app modes: Contribute (Join/Leave) · Utilize (submit jobs)\n"
        "Browser portal: login → Live pool + Utilize section\n"
        f"  Local:     {hints['local_url']}\n"
        f"  Tailscale: {hints['tailscale_url']}\n"
        f"  Invite:    {hints['invite_code']}  (pool password stays in .env — not shown)\n"
        "\n"
        "CLI: python -m gpu_swarm utilize status|probe|cuda --wait\n"
        "SDK: from gpu_swarm.client import GPUPool\n"
        "Docs: CONNECTING.md · examples/coding_agent_pool.py\n"
        f"{PRIVATE_NETWORK_BLURB}"
    )


def get_agent_vms_info(path: str | None = None) -> dict[str, Any]:
    """agent-vms workspace integration (Hermes control plane; not GPU passthrough)."""
    from gpu_swarm.agent_vm_bridge import (
        GPU_HONESTY,
        compute_vm_resource_plan,
        resolve_agent_vm_controller,
        workspace_status,
    )

    settings = load_joiner_settings()
    if path:
        settings.agent_vms_path = path
    present = agent_vms_present(path or settings.agent_vms_path)
    resolved = resolve_agent_vm_controller(settings)
    plan = compute_vm_resource_plan(settings)
    info: dict[str, Any] = {
        **present,
        "control_plane": "hermes",
        "ready": bool(resolved.get("ok")),
        "controller": resolved.get("controller") or "",
        "plan": plan,
        "note": GPU_HONESTY,
        "doc": str(ADVANCED_VM_DOC),
    }
    if resolved.get("ok"):
        try:
            info["status"] = workspace_status(settings)
        except Exception as exc:  # noqa: BLE001
            info["status_error"] = str(exc)
    return info


def workspace_resource_plan() -> dict[str, Any]:
    from gpu_swarm.agent_vm_bridge import compute_vm_resource_plan

    return compute_vm_resource_plan(load_joiner_settings())


def workspace_status() -> dict[str, Any]:
    from gpu_swarm.agent_vm_bridge import workspace_status as _status

    return _status(load_joiner_settings())


def apply_workspace_caps() -> dict[str, Any]:
    from gpu_swarm.agent_vm_bridge import apply_workspace_caps as _apply

    return _apply(load_joiner_settings())


def open_workspace(*, open_rdp: bool = True, start_if_needed: bool = True) -> dict[str, Any]:
    """Start/open agent Ubuntu workspace under Contribute offer caps (Hermes)."""
    from gpu_swarm.agent_vm_bridge import open_workspace as _open

    return _open(
        load_joiner_settings(),
        start_if_needed=start_if_needed,
        open_rdp=open_rdp,
        allow_vagrant_up=False,
    )


def halt_workspace() -> dict[str, Any]:
    from gpu_swarm.agent_vm_bridge import halt_workspace as _halt

    return _halt(load_joiner_settings())


def open_workspace_rdp() -> dict[str, Any]:
    from gpu_swarm.agent_vm_bridge import open_rdp_session, workspace_status as _status

    st = _status(load_joiner_settings())
    return open_rdp_session(
        host=str(st.get("rdp_host") or "127.0.0.1"),
        port=int(st.get("rdp_port") or 3390),
    )


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
        "GPU_SWARM_HOST_PROTECT": (
            "1" if bool(getattr(settings, "host_protect", True)) else "0"
        ),
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
                    **run_kwargs(),
                )
            return
        except OSError:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                check=False,
                timeout=10,
                **run_kwargs(),
            )
            return
    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + 8
    while time.time() < deadline and _pid_alive(pid):
        time.sleep(0.25)
    if _pid_alive(pid):
        os.kill(pid, signal.SIGKILL)


def get_local_endpoint_env_line(port: int | None = None) -> str:
    p = int(port or DEFAULT_LOCAL_ENDPOINT_PORT)
    return f"OPENAI_BASE_URL=http://127.0.0.1:{p}/v1"


def _local_endpoint_cli_registered() -> bool:
    try:
        from gpu_swarm.cli import build_parser

        parser = build_parser()
        for action in getattr(parser, "_actions", []):
            choices = getattr(action, "choices", None)
            if isinstance(choices, dict) and "local-endpoint" in choices:
                return True
    except Exception:  # noqa: BLE001
        return False
    return False


def local_endpoint_available() -> dict[str, Any]:
    """True when module, CLI subcommand, frozen EXE mode, or start-local-endpoint.cmd can start."""
    import importlib.util

    frozen = is_frozen()
    module_ok = importlib.util.find_spec("gpu_swarm.local_endpoint") is not None
    cli_ok = _local_endpoint_cli_registered()
    cmd_path = BUNDLE_ROOT / "start-local-endpoint.cmd"
    cmd_ok = cmd_path.is_file()
    available = bool(frozen or module_ok or cli_ok or cmd_ok)
    return {
        "available": available,
        "module": module_ok,
        "cli": cli_ok,
        "cmd": cmd_ok,
        "frozen": frozen,
        "cmd_path": str(cmd_path) if cmd_ok else "",
        "detail": (
            "Ready — Start local model endpoint on Connect."
            if available
            else (
                "Waiting for gpu_swarm.local_endpoint / `python -m gpu_swarm local-endpoint` "
                "(see LOCAL_MODEL.md)."
            )
        ),
    }


def local_endpoint_status() -> dict[str, Any]:
    """Whether the desktop-spawned local endpoint subprocess is alive + probe /health."""
    global _local_endpoint_proc
    avail = local_endpoint_available()
    running = False
    pid: int | None = None
    if _local_endpoint_proc is not None and _local_endpoint_proc.poll() is None:
        running = True
        pid = _local_endpoint_proc.pid
    else:
        if LOCAL_ENDPOINT_PID_FILE.is_file():
            try:
                pid = int(LOCAL_ENDPOINT_PID_FILE.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                pid = None
            if pid and _pid_alive(pid):
                running = True
            else:
                pid = None
        _local_endpoint_proc = None

    port = DEFAULT_LOCAL_ENDPOINT_PORT
    health: dict[str, Any] | None = None
    url = f"http://127.0.0.1:{port}"
    openai_base = f"{url}/v1"
    # Probe preferred + alt ports; require GPU Pool health shape (ignore other :8080 apps)
    http_live = False
    for probe_port in (port, 11434):
        probe_url = f"http://127.0.0.1:{probe_port}"
        try:
            import httpx

            r = httpx.get(f"{probe_url}/health", timeout=1.5)
            if r.status_code != 200:
                continue
            try:
                payload = r.json()
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(payload, dict):
                continue
            if "scheduler_ok" not in payload and "scheduler_url" not in payload:
                continue
            health = payload
            url = probe_url
            openai_base = f"{probe_url}/v1"
            port = probe_port
            http_live = True
            break
        except Exception:  # noqa: BLE001
            continue

    if http_live:
        running = True
    elif running and not http_live:
        # Process we spawned may still be warming
        pass

    if running and health:
        status = "running"
        detail = (
            f"Live at {openai_base} · scheduler_ok={health.get('scheduler_ok')} "
            f"{health.get('detail') or ''}"
        ).strip()
    elif running:
        status = "starting"
        detail = f"Process up (pid={pid}); waiting for /health on {url}"
    elif avail.get("available"):
        status = "stopped"
        detail = str(avail.get("detail") or "Ready — Start local model endpoint on Connect.")
    else:
        status = "unavailable"
        detail = str(avail.get("detail") or "Local endpoint module missing")

    blurb = (
        f"Paste into apps: OPENAI_BASE_URL={openai_base}  ·  "
        "Pool as a local AI API (not a Windows GPU driver). See LOCAL_MODEL.md"
    )
    return {
        "ok": True,
        "available": bool(avail.get("available")),
        "running": running,
        "status": status,
        "pid": pid,
        "url": url,
        "openai_base": openai_base,
        "openai_base_url": openai_base,
        "env_line": f"OPENAI_BASE_URL={openai_base}",
        "health": health,
        "doc": str(LOCAL_MODEL_DOC),
        "doc_exists": LOCAL_MODEL_DOC.is_file(),
        "detail": detail,
        "blurb": blurb,
        "honesty": (
            "Appears as a local AI API for apps (OpenAI-compatible) — not a physical GPU device."
        ),
        "availability": avail,
    }


def start_local_endpoint(
    *,
    scheduler_url: str | None = None,
    port: int | None = None,
) -> dict[str, Any]:
    """Spawn `python -m gpu_swarm local-endpoint` (or start-local-endpoint.cmd) on localhost."""
    global _local_endpoint_proc, _local_endpoint_log_handle
    avail = local_endpoint_available()
    if not avail.get("available"):
        return {
            "ok": False,
            "message": avail.get("detail")
            or "Local endpoint not available yet (module/CLI not merged).",
            "pid": None,
        }

    st = local_endpoint_status()
    if st.get("running"):
        return {
            "ok": True,
            "already_running": True,
            "message": "Local model endpoint already running",
            **{k: st[k] for k in ("pid", "url", "openai_base", "env_line")},
        }

    settings = load_joiner_settings()
    sched = (scheduler_url or settings.scheduler_url or DEFAULT_LOCAL_SCHEDULER_URL).rstrip("/")
    # Omit --port when unset so local_endpoint.pick_listen_port can fall back (8080→11434)
    listen_port: int | None = int(port) if port is not None else None
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["GPU_SWARM_SCHEDULER_URL"] = sched

    cmd_path = BUNDLE_ROOT / "start-local-endpoint.cmd"
    if is_frozen():
        # Re-launch this EXE in local-endpoint mode (fastapi bundled; no system Python).
        cmd = [
            sys.executable,
            "--local-endpoint",
            "--host",
            "127.0.0.1",
            "--scheduler-url",
            sched,
        ]
    elif avail.get("cli"):
        cmd = [
            sys.executable,
            "-m",
            "gpu_swarm",
            "local-endpoint",
            "--host",
            "127.0.0.1",
            "--scheduler-url",
            sched,
        ]
    elif avail.get("module"):
        # Module present before CLI subcommand is registered
        cmd = [
            sys.executable,
            "-m",
            "gpu_swarm.local_endpoint",
            "--host",
            "127.0.0.1",
            "--scheduler-url",
            sched,
        ]
    elif cmd_path.is_file() and sys.platform == "win32":
        cmd = [
            "cmd.exe",
            "/c",
            str(cmd_path),
            "--scheduler-url",
            sched,
        ]
    else:
        return {
            "ok": False,
            "message": "No local-endpoint launcher (module/CLI/cmd missing).",
            "pid": None,
        }
    if listen_port is not None:
        cmd.extend(["--port", str(listen_port)])
    try:
        LOCAL_ENDPOINT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _local_endpoint_log_handle is not None:
            try:
                _local_endpoint_log_handle.close()
            except Exception:  # noqa: BLE001
                pass
        _local_endpoint_log_handle = open(LOCAL_ENDPOINT_LOG_FILE, "a", encoding="utf-8")  # noqa: SIM115
        _local_endpoint_log_handle.write(
            f"\n--- local-endpoint start {time.strftime('%Y-%m-%d %H:%M:%S')} port={listen_port} ---\n"
        )
        _local_endpoint_log_handle.flush()
        _local_endpoint_proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=_local_endpoint_log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            **popen_kwargs(new_group=True),
        )
    except OSError as exc:
        _local_endpoint_proc = None
        return {"ok": False, "message": str(exc), "pid": None}

    pid = _local_endpoint_proc.pid
    LOCAL_ENDPOINT_PID_FILE.write_text(str(pid), encoding="utf-8")
    # Brief wait for bind
    time.sleep(0.8)
    if _local_endpoint_proc.poll() is not None:
        code = _local_endpoint_proc.returncode
        tail = ""
        try:
            text = LOCAL_ENDPOINT_LOG_FILE.read_text(encoding="utf-8", errors="replace")
            tail = "\n".join(text.splitlines()[-40:])
        except OSError:
            pass
        hint = ""
        low = tail.lower()
        if "invalid choice" in low or "unrecognized arguments" in low:
            hint = (
                " CLI does not know `local-endpoint` yet — pull latest gpu_swarm.local_endpoint "
                "or use start-local-endpoint.cmd when the module lands."
            )
        _local_endpoint_proc = None
        try:
            LOCAL_ENDPOINT_PID_FILE.unlink()
        except OSError:
            pass
        return {
            "ok": False,
            "message": (
                f"Local endpoint exited immediately (code {code}).{hint} "
                f"See {LOCAL_ENDPOINT_LOG_FILE}"
            ),
            "pid": pid,
            "log_tail": tail,
        }
    # Re-probe to learn actual bind port (8080 may be taken → 11434)
    live: dict[str, Any] = {}
    for _ in range(12):
        if _local_endpoint_proc is not None and _local_endpoint_proc.poll() is not None:
            break
        live = local_endpoint_status()
        if live.get("health"):
            break
        time.sleep(0.4)
    if _local_endpoint_proc is not None and _local_endpoint_proc.poll() is not None:
        code = _local_endpoint_proc.returncode
        _local_endpoint_proc = None
        try:
            LOCAL_ENDPOINT_PID_FILE.unlink()
        except OSError:
            pass
        return {
            "ok": False,
            "message": (
                f"Local endpoint exited while binding (code {code}). "
                "Preferred port may be busy — see data/local_endpoint.log "
                f"({LOCAL_ENDPOINT_LOG_FILE})."
            ),
            "pid": pid,
            "status": local_endpoint_status(),
        }
    openai_base = str(live.get("openai_base") or DEFAULT_OPENAI_BASE_URL)
    url = str(live.get("url") or DEFAULT_LOCAL_ENDPOINT_URL)
    return {
        "ok": True,
        "already_running": False,
        "message": (
            f"Local model endpoint started · {openai_base}"
            if live.get("health")
            else f"Local model endpoint process started (pid={pid}); waiting for /health"
        ),
        "pid": pid,
        "url": url,
        "openai_base": openai_base,
        "openai_base_url": openai_base,
        "env_line": f"OPENAI_BASE_URL={openai_base}",
        "scheduler_url": sched,
        "doc": str(LOCAL_MODEL_DOC),
        "status": live,
    }


def stop_local_endpoint() -> dict[str, Any]:
    global _local_endpoint_proc, _local_endpoint_log_handle
    stopped = False
    if _local_endpoint_proc is not None and _local_endpoint_proc.poll() is None:
        _graceful_stop(_local_endpoint_proc)
        stopped = True
    _local_endpoint_proc = None
    if LOCAL_ENDPOINT_PID_FILE.is_file():
        try:
            pid = int(LOCAL_ENDPOINT_PID_FILE.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pid = None
        if pid and _pid_alive(pid):
            _signal_stop_pid(pid)
            stopped = True
        try:
            LOCAL_ENDPOINT_PID_FILE.unlink()
        except OSError:
            pass
    if _local_endpoint_log_handle is not None:
        try:
            _local_endpoint_log_handle.close()
        except Exception:  # noqa: BLE001
            pass
        _local_endpoint_log_handle = None
    return {
        "ok": True,
        "stopped": stopped,
        "message": "Local model endpoint stopped" if stopped else "Local model endpoint was not running",
    }

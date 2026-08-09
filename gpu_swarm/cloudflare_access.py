"""Installer-facing Cloudflare access helpers.

This module intentionally supports only the GPU Pool portal origin. It never
publishes the scheduler directly and never reads or prints Cloudflare secrets.
Quick mode needs no account; named mode uses a user-created config outside the
repository.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from gpu_swarm.paths import APP_ROOT, BUNDLE_ROOT, ROOT, is_frozen
from gpu_swarm.public_endpoints import write_public_endpoints
from gpu_swarm.win_subprocess import popen_kwargs, run_kwargs

DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000
URL_RE = re.compile(r"https://[A-Za-z0-9-]+\.trycloudflare\.com")
DATA = ROOT / "data"
TUNNEL_LOG = DATA / "cloudflared_portal.log"
TUNNEL_PID = DATA / "cloudflared_portal.pid"


def _tool_candidates() -> list[Path]:
    local = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData/Local"))
    return [
        local / "GPUPool" / "tools" / "cloudflared.exe",
        APP_ROOT / "tools" / "cloudflared.exe",
        BUNDLE_ROOT / "tools" / "cloudflared.exe",
        ROOT / "tools" / "cloudflared.exe",
    ]


def resolve_cloudflared() -> str | None:
    for candidate in _tool_candidates():
        if candidate.is_file():
            return str(candidate)
    return shutil.which("cloudflared.exe") or shutil.which("cloudflared")


def _script_path(name: str) -> Path:
    bundled = BUNDLE_ROOT / "scripts" / name
    if bundled.is_file():
        return bundled
    return ROOT / "scripts" / name


def install_cloudflared_tool() -> dict[str, Any]:
    """Download cloudflared into writable GPUPool data, never the bundle."""
    script = _script_path("install_cloudflared.ps1")
    install_dir = APP_ROOT / "tools"
    if not script.is_file():
        return {"ok": False, "message": f"Cloudflare installer missing: {script}"}
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-InstallDir",
        str(install_dir),
        "-Json",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(APP_ROOT),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            **run_kwargs(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "message": f"Cloudflare helper install failed: {exc}"}
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    parsed: dict[str, Any] | None = None
    start, end = output.rfind("{"), output.rfind("}")
    if start >= 0 and end > start:
        try:
            value = json.loads(output[start : end + 1])
            if isinstance(value, dict):
                parsed = value
        except json.JSONDecodeError:
            pass
    result = parsed or {"ok": proc.returncode == 0, "message": output[-1200:]}
    result.setdefault("code", proc.returncode)
    result.setdefault("log_text", output[-4000:])
    result["path"] = resolve_cloudflared() or ""
    return result


def _read_owned_pid() -> int | None:
    try:
        pid = int(TUNNEL_PID.read_text(encoding="utf-8").strip())
        return pid if pid > 0 else None
    except (OSError, ValueError):
        return None


def _is_cloudflared_pid(pid: int) -> bool:
    try:
        proc = subprocess.run(
            ["tasklist.exe", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            **run_kwargs(),
        )
        return "cloudflared" in (proc.stdout or "").lower()
    except (OSError, subprocess.TimeoutExpired):
        return False


def stop_owned_tunnel() -> None:
    pid = _read_owned_pid()
    if pid and _is_cloudflared_pid(pid):
        try:
            subprocess.run(
                ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
                **run_kwargs(),
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        TUNNEL_PID.unlink(missing_ok=True)
    except OSError:
        pass


def _probe(url: str, path: str, timeout: float = 8.0) -> dict[str, Any]:
    target = url.rstrip("/") + path
    try:
        request = urllib.request.Request(target, headers={"User-Agent": "GPU-Pool-Cloudflare-Setup/1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(200_000).decode("utf-8", errors="replace")
            return {"ok": 200 <= response.status < 300, "status": response.status, "url": target, "bytes": len(body)}
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return {"ok": False, "url": target, "error": str(exc)}


def _origin_ready() -> dict[str, Any]:
    portal = _probe("http://127.0.0.1:8767", "/portal", timeout=4)
    if not portal.get("ok"):
        return {"ok": False, "message": "Local portal is not running at http://127.0.0.1:8767. Start the GPU Pool host services first.", "probe": portal}
    return {"ok": True, "probe": portal}


def _start_cloudflared(exe: str, args: list[str]) -> subprocess.Popen:
    DATA.mkdir(parents=True, exist_ok=True)
    TUNNEL_LOG.unlink(missing_ok=True)
    log_handle = TUNNEL_LOG.open("a", encoding="utf-8", errors="replace")
    try:
        popen_options = popen_kwargs()
        if os.name == "nt":
            popen_options["creationflags"] = DETACHED_PROCESS | CREATE_NO_WINDOW
        proc = subprocess.Popen(
            [exe, *args],
            cwd=str(APP_ROOT),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            close_fds=True,
            env={**os.environ, "NO_AUTOUPDATE": "1"},
            **popen_options,
        )
    finally:
        log_handle.close()
    TUNNEL_PID.write_text(str(proc.pid), encoding="utf-8")
    return proc


def _wait_quick_url(timeout: float = 60.0) -> str | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            text = TUNNEL_LOG.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        matches = URL_RE.findall(text)
        if matches:
            return matches[-1].rstrip("/")
        time.sleep(1.0)
    return None


def _wait_public(url: str, timeout: float = 60.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        portal = _probe(url, "/portal", timeout=6)
        api = _probe(url, "/pool-api/status", timeout=6)
        last = {"portal": portal, "api": api}
        if portal.get("ok") and api.get("ok"):
            return {"ok": True, **last}
        time.sleep(1.0)
    return {"ok": False, **last}


def publish_cloudflare(
    *,
    mode: str = "quick",
    hostname: str = "",
    tunnel_name: str = "gpu-pool",
    config_path: str = "",
    open_browser: bool = False,
) -> dict[str, Any]:
    """Publish only the portal origin and verify both public routes."""
    mode = (mode or "quick").strip().lower()
    if mode not in {"quick", "named"}:
        return {"ok": False, "message": f"Unsupported Cloudflare mode: {mode}"}
    origin = _origin_ready()
    if not origin.get("ok"):
        return origin
    exe = resolve_cloudflared()
    if not exe:
        return {"ok": False, "message": "cloudflared is not installed. Click Install Cloudflare helper first."}

    stop_owned_tunnel()
    if mode == "quick":
        args = ["tunnel", "--url", "http://127.0.0.1:8767", "--no-autoupdate"]
        proc = _start_cloudflared(exe, args)
        public_url = _wait_quick_url()
        if not public_url:
            stop_owned_tunnel()
            return {"ok": False, "message": "cloudflared started but did not emit a Quick Tunnel URL; review data/cloudflared_portal.log", "pid": proc.pid}
    else:
        hostname = hostname.strip().rstrip("/")
        cfg = Path(config_path).expanduser() if config_path else (Path.home() / ".cloudflared" / "gpu-pool.yml")
        if not hostname or "/" in hostname or "://" in hostname:
            return {"ok": False, "message": "Named mode requires a hostname such as gpu-pool.example.com."}
        if not cfg.is_file():
            return {"ok": False, "message": f"Named tunnel config not found: {cfg}. Use the Cloudflare setup guide first."}
        proc = _start_cloudflared(exe, ["tunnel", "--config", str(cfg), "run", tunnel_name])
        public_url = f"https://{hostname}"

    checks = _wait_public(public_url)
    if not checks.get("ok"):
        stop_owned_tunnel()
        return {"ok": False, "message": "Cloudflare tunnel started but public portal/API verification failed.", "public_url": public_url, "checks": checks}

    mode_name = "cloudflared_named" if mode == "named" else "cloudflared_quick"
    data = write_public_endpoints(
        portal_public_url=public_url,
        mode=mode_name,
        extra={
            "cloudflared_pid": proc.pid,
            "hostname": hostname if mode == "named" else "",
            "note": (
                "Stable Cloudflare named tunnel. Availability still depends on this host."
                if mode == "named"
                else "Ephemeral Cloudflare Quick Tunnel. URL changes when this host restarts the tunnel."
            ),
        },
    )
    portal_path = data["portal_path"]
    if open_browser:
        try:
            os.startfile(portal_path)  # type: ignore[attr-defined]
        except OSError:
            pass
    return {"ok": True, "mode": mode_name, "portal_path": portal_path, "pool_api_public_url": data["pool_api_public_url"], "pid": proc.pid, "checks": checks}


def open_cloudflare_guide() -> dict[str, Any]:
    guide = BUNDLE_ROOT / "cloudflare" / "README.md"
    if not guide.is_file():
        guide = ROOT / "cloudflare" / "README.md"
    if not guide.is_file():
        return {"ok": False, "message": f"Cloudflare guide missing: {guide}"}
    try:
        os.startfile(str(guide))  # type: ignore[attr-defined]
        return {"ok": True, "path": str(guide)}
    except OSError as exc:
        return {"ok": False, "path": str(guide), "message": str(exc)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GPU Pool Cloudflare access helper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--quick", action="store_true")
    group.add_argument("--named", action="store_true")
    group.add_argument("--install", action="store_true")
    group.add_argument("--guide", action="store_true")
    parser.add_argument("--hostname", default="")
    parser.add_argument("--tunnel-name", default="gpu-pool")
    parser.add_argument("--config", default="")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    if args.install:
        result = install_cloudflared_tool()
    elif args.guide:
        result = open_cloudflare_guide()
    else:
        result = publish_cloudflare(
            mode="named" if args.named else "quick",
            hostname=args.hostname,
            tunnel_name=args.tunnel_name,
            config_path=args.config,
            open_browser=not args.no_browser,
        )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

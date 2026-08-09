"""Reliable one-click GPU Pool web launcher.

Starts or reuses the local scheduler, portal, and worker, then creates a fresh
Cloudflare Quick Tunnel and verifies the public portal before opening it.

This is intentionally a bounded orchestrator, not a general shell runner:
only the known GPU Pool services and cloudflared are started. Every phase is
logged to data/launch_public.log and the public endpoint files are written only
after a newly observed tunnel URL passes an HTTP check.

For a durable public hostname, replace the quick-tunnel phase with a named
Cloudflare Tunnel/Worker deployment. The local GPU origin remains host-bound.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOG_PATH = DATA / "launch_public.log"
TUNNEL_LOG = DATA / "cloudflared_portal.log"
TUNNEL_PID = DATA / "cloudflared_portal.pid"
ENDPOINTS_JSON = DATA / "public_endpoints.json"
SHARE_PATH = DATA / "public_endpoints.share.txt"
CLOUDFLARED_CANDIDATES = (
    ROOT / "tools" / "cloudflared.exe",
    ROOT / "cloudflared.exe",
)
URL_RE = re.compile(r"https://[A-Za-z0-9-]+\.trycloudflare\.com")
DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log(message: str) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    line = f"[{utc_now()}] {message}"
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def load_dotenv() -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = ROOT / ".env"
    if not env_path.exists():
        return values
    for raw in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve_python() -> str:
    candidates = [
        Path(r"C:\Python313\python.exe"),
        Path(r"C:\Python312\python.exe"),
        Path(sys.executable),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise RuntimeError("No supported Python interpreter was found")


def resolve_cloudflared() -> str:
    for candidate in CLOUDFLARED_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    from shutil import which

    found = which("cloudflared.exe") or which("cloudflared")
    if found:
        return found
    raise RuntimeError(
        "cloudflared.exe is missing; run scripts/install_cloudflared.ps1 first"
    )


def http_get(url: str, timeout: float = 3.0) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read(1_000_000)
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read(1_000_000)


def wait_http(url: str, timeout: float, predicate=None) -> tuple[int, bytes] | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            status, body = http_get(url)
            if 200 <= status < 300 and (predicate is None or predicate(body)):
                return status, body
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(1)
    return None


def start_hidden_service(name: str, args: list[str], env: dict[str, str]) -> None:
    python = resolve_python()
    result = subprocess.run(
        [python, "-m", "scripts.start_hidden", name, *args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    output = (result.stdout + result.stderr).strip().replace("\n", " | ")
    log(f"start {name}: rc={result.returncode} {output}")
    if result.returncode != 0:
        raise RuntimeError(f"could not start {name}: {output or 'no launcher output'}")


def ensure_scheduler(env: dict[str, str]) -> None:
    if wait_http("http://127.0.0.1:8766/status", 2):
        log("scheduler already ready at 127.0.0.1:8766")
        return
    log("scheduler is not ready; starting the hidden scheduler")
    start_hidden_service("scheduler", ["--host", "127.0.0.1", "--port", "8766"], env)
    if not wait_http("http://127.0.0.1:8766/status", 30):
        raise RuntimeError("scheduler did not become healthy within 30 seconds")
    log("scheduler ready at 127.0.0.1:8766")


def ensure_portal(env: dict[str, str]) -> None:
    if wait_http("http://127.0.0.1:8767/portal", 2):
        log("portal already ready at 127.0.0.1:8767")
        return
    log("portal is not ready; starting the hidden portal")
    start_hidden_service("portal", ["--host", "0.0.0.0", "--port", "8767"], env)
    if not wait_http("http://127.0.0.1:8767/portal", 30):
        raise RuntimeError("portal did not become healthy within 30 seconds")
    log("portal ready at 127.0.0.1:8767")


def status_has_worker(body: bytes) -> bool:
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
        return int(data.get("workers_online", 0)) > 0
    except (ValueError, TypeError):
        return False


def ensure_worker(env: dict[str, str]) -> None:
    current = wait_http("http://127.0.0.1:8766/status", 2, status_has_worker)
    if current:
        log("worker already online")
        return
    log("no worker is online; starting the hidden Drew-Home worker")
    start_hidden_service(
        "worker", ["--name", "Drew-Home", "--discord-user", "Drew"], env
    )
    if not wait_http("http://127.0.0.1:8766/status", 60, status_has_worker):
        raise RuntimeError("worker did not register within 60 seconds")
    status, body = http_get("http://127.0.0.1:8766/status")
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
        log(
            "worker ready: online=%s free_vram_mb=%s"
            % (data.get("workers_online"), data.get("free_vram_mb"))
        )
    except (ValueError, TypeError):
        log(f"worker ready: scheduler status HTTP {status}")


def tasklist_name(pid: int) -> str | None:
    result = subprocess.run(
        ["tasklist.exe", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    line = result.stdout.strip().splitlines()
    if not line or "No tasks" in line[0]:
        return None
    return line[0].split(",", 1)[0].strip('"')


def stop_owned_tunnel() -> None:
    if not TUNNEL_PID.exists():
        return
    try:
        pid = int(TUNNEL_PID.read_text(encoding="ascii", errors="ignore").strip())
    except ValueError:
        TUNNEL_PID.unlink(missing_ok=True)
        return
    name = tasklist_name(pid)
    if name and name.lower() == "cloudflared.exe":
        log(f"stopping previous owned cloudflared pid={pid}")
        subprocess.run(
            ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    else:
        log(f"ignoring stale tunnel pid file pid={pid} process={name or 'gone'}")
    TUNNEL_PID.unlink(missing_ok=True)


def launch_quick_tunnel(cloudflared: str) -> tuple[subprocess.Popen, str]:
    DATA.mkdir(parents=True, exist_ok=True)
    stop_owned_tunnel()
    TUNNEL_LOG.unlink(missing_ok=True)
    log_handle = TUNNEL_LOG.open("ab", buffering=0)
    target = "http://127.0.0.1:8767"
    process = subprocess.Popen(
        [cloudflared, "tunnel", "--url", target, "--no-autoupdate"],
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
    )
    TUNNEL_PID.write_text(str(process.pid), encoding="ascii")
    log(f"quick tunnel started pid={process.pid} origin={target}")
    deadline = time.monotonic() + 60
    public_url: str | None = None
    while time.monotonic() < deadline:
        if TUNNEL_LOG.exists():
            text = TUNNEL_LOG.read_text(encoding="utf-8", errors="replace")
            match = URL_RE.search(text)
            if match:
                public_url = match.group(0).rstrip("/")
                break
        if process.poll() is not None:
            break
        time.sleep(1)
    log_handle.close()
    if not public_url:
        exit_code = process.poll()
        if exit_code is None:
            process.kill()
        TUNNEL_PID.unlink(missing_ok=True)
        raise RuntimeError(
            f"cloudflared produced no fresh trycloudflare URL within 60 seconds "
            f"(exit={exit_code}); see {TUNNEL_LOG}"
        )
    log(f"fresh quick-tunnel URL observed: {public_url}")
    return process, public_url


def launch_named_tunnel(
    cloudflared: str,
    config_path: Path,
    tunnel_name: str,
    hostname: str,
) -> tuple[subprocess.Popen, str]:
    """Run only the GPU Pool named tunnel; never reuse another app's config."""
    if not config_path.exists():
        raise RuntimeError(
            f"GPU Pool named-tunnel config is missing: {config_path}. "
            "Create it from cloudflare/gpu-pool.tunnel.yml.example after local Cloudflare login."
        )
    if not re.fullmatch(r"[A-Za-z0-9.-]+", hostname) or "." not in hostname:
        raise RuntimeError(f"invalid public hostname: {hostname!r}")
    DATA.mkdir(parents=True, exist_ok=True)
    stop_owned_tunnel()
    TUNNEL_LOG.unlink(missing_ok=True)
    log_handle = TUNNEL_LOG.open("ab", buffering=0)
    process = subprocess.Popen(
        [cloudflared, "tunnel", "--config", str(config_path), "run", tunnel_name],
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
    )
    TUNNEL_PID.write_text(str(process.pid), encoding="ascii")
    log(f"named tunnel started pid={process.pid} name={tunnel_name} hostname={hostname}")
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            log_handle.close()
            TUNNEL_PID.unlink(missing_ok=True)
            raise RuntimeError(
                f"named tunnel exited early with code {process.returncode}; see {TUNNEL_LOG}"
            )
        time.sleep(1)
    log_handle.close()
    return process, f"https://{hostname}"


def write_endpoint_files(
    public_url: str,
    pid: int,
    invite_code: str,
    *,
    mode: str = "cloudflared_quick",
    note: str = "Ephemeral Quick Tunnel. Use a named Cloudflare Tunnel for a stable hostname.",
) -> None:
    updated = utc_now()
    payload: dict[str, Any] = {
        "mode": mode,
        "portal_public_url": public_url,
        "portal_path": f"{public_url}/portal",
        "pool_api_public_url": f"{public_url}/pool-api",
        "scheduler_local": "http://127.0.0.1:8766",
        "portal_local": "http://127.0.0.1:8767",
        "updated_at": updated,
        "invite_code": invite_code,
        "cloudflared_pid": pid,
        "note": note,
    }
    ENDPOINTS_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    SHARE_PATH.write_text(
        "GPU Pool -- public access (no Tailscale needed)\n"
        "----------------------------------------------\n"
        f"Portal:     {public_url}/portal\n"
        f"Pool API:   {public_url}/pool-api  (portal proxy; allowlisted jobs only)\n"
        f"Invite:     {invite_code}\n\n"
        "Laptop / no NVIDIA: open Portal -> sign in -> Utilize.\n"
        "Optional: Contribute CPU/RAM/disk with VRAM=0.\n"
        f"{note}\n"
        f"Updated:    {updated}\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--with-bot", action="store_true", help="also start the authenticated Discord bot")
    parser.add_argument("--named", action="store_true", help="run the configured stable GPU Pool named tunnel")
    parser.add_argument("--hostname", help="public hostname for --named, e.g. gpu.example.com")
    parser.add_argument("--tunnel-name", default="gpu-pool", help="Cloudflare tunnel name for --named")
    parser.add_argument("--config", help="GPU Pool named-tunnel YAML path for --named")
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    dotenv = load_dotenv()
    log("=== launch-public begin ===")
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONUNBUFFERED"] = "1"
    env["GPU_SWARM_SCHEDULER_URL"] = "http://127.0.0.1:8766"
    try:
        ensure_scheduler(env)
        ensure_portal(env)
        ensure_worker(env)
        if args.with_bot:
            log("authenticated bot requested explicitly; starting it")
            start_hidden_service("bot", [], env)
        cloudflared = resolve_cloudflared()
        if args.named:
            hostname = (
                args.hostname
                or os.environ.get("GPU_SWARM_PUBLIC_HOSTNAME")
                or dotenv.get("GPU_SWARM_PUBLIC_HOSTNAME")
            )
            if not hostname:
                raise RuntimeError("--named requires --hostname or GPU_SWARM_PUBLIC_HOSTNAME")
            config = Path(
                args.config
                or os.environ.get("GPU_SWARM_NAMED_TUNNEL_CONFIG")
                or dotenv.get("GPU_SWARM_NAMED_TUNNEL_CONFIG")
                or str(Path.home() / ".cloudflared" / "gpu-pool.yml")
            )
            tunnel_name = (
                args.tunnel_name
                if args.tunnel_name != "gpu-pool"
                else os.environ.get("GPU_SWARM_NAMED_TUNNEL_NAME")
                or dotenv.get("GPU_SWARM_NAMED_TUNNEL_NAME")
                or args.tunnel_name
            )
            process, public_url = launch_named_tunnel(
                cloudflared, config, tunnel_name, hostname
            )
            mode = "cloudflared_named"
            note = "Stable named Cloudflare Tunnel hostname. Availability still depends on the local GPU host."
        else:
            process, public_url = launch_quick_tunnel(cloudflared)
            mode = "cloudflared_quick"
            note = "Ephemeral Quick Tunnel. Use --named with a Cloudflare-managed hostname for a stable link."
        public_portal = f"{public_url}/portal"
        if not wait_http(public_portal, 30):
            raise RuntimeError(f"public portal did not return HTTP 2xx: {public_portal}")
        if not wait_http(f"{public_url}/pool-api/status", 15):
            raise RuntimeError(f"public pool API did not return HTTP 2xx: {public_url}/pool-api/status")
        invite = load_dotenv().get("GPU_SWARM_INVITE_CODES", "glitch-factor")
        write_endpoint_files(public_url, process.pid, invite, mode=mode, note=note)
        log(f"PUBLIC READY portal={public_portal} pid={process.pid} mode={mode}")
        if not args.no_browser:
            try:
                os.startfile(public_portal)  # type: ignore[attr-defined]
                log("opened the verified public portal in the default browser")
            except OSError as exc:
                log(f"browser open skipped: {exc}")
        log("=== launch-public success ===")
        return 0
    except Exception as exc:  # noqa: BLE001 - top-level launcher must log a useful failure
        log(f"BLOCKED: {type(exc).__name__}: {exc}")
        log("=== launch-public failed ===")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

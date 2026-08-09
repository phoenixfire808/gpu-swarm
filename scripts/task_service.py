"""Long-running Windows Task Scheduler entry point for GPU Pool services.

Each scheduled task runs this file with one service name. The service itself
stays in the foreground, logs to %LOCALAPPDATA%\\GPUPool\\logs, and restarts
its child after an unexpected exit. Task Scheduler only needs to start this
small Python process at logon.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from gpu_swarm.service_lifecycle import gate_detail, services_enabled
from gpu_swarm.win_subprocess import popen_kwargs

LOG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GPUPool" / "logs"
PYTHON = Path(r"C:\Python313\pythonw.exe")
if not PYTHON.exists():
    PYTHON = Path(sys.executable)
POWERSHELL = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")

SERVICES = {
    "scheduler": ["-m", "gpu_swarm", "scheduler", "--host", "127.0.0.1", "--port", "8766"],
    "portal": ["-m", "gpu_swarm", "portal", "--host", "0.0.0.0", "--port", "8767"],
    "worker": ["-m", "gpu_swarm", "worker", "--name", "Drew-Home", "--discord-user", "Drew"],
    "tunnel": [
        "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
        "-File", str(ROOT / "scripts" / "start_public_tunnel.ps1"),
    ],
}


def _log_path(service: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"task-{service}.log"


def _command(service: str) -> list[str]:
    if service == "tunnel":
        return [str(POWERSHELL), *SERVICES[service]]
    return [str(PYTHON), *SERVICES[service]]


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in SERVICES:
        valid = ", ".join(SERVICES)
        print(f"usage: task_service.py <{valid}>", file=sys.stderr)
        return 2

    service = sys.argv[1]
    log_path = _log_path(service)
    if not services_enabled():
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"[task] {service} not started: {gate_detail()}\n")
        return 0
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env.pop("PYTHONPATH", None)
    if service == "worker":
        # The worker must talk to the local scheduler even though the portal
        # advertises the public /pool-api URL to friends.
        env["GPU_SWARM_SCHEDULER_URL"] = "http://127.0.0.1:8766"

    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n--- task service {service} starting cwd={ROOT} ---\n")
        log.flush()
        while True:
            if not services_enabled():
                log.write(f"[task] {service} stopping: {gate_detail()}\n")
                log.flush()
                return 0
            command = _command(service)
            log.write(f"[task] launching: {command}\n")
            log.flush()
            try:
                child = subprocess.Popen(
                    command,
                    cwd=str(ROOT),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    **popen_kwargs(),
                )
                while child.poll() is None:
                    if not services_enabled():
                        log.write(f"[task] {service} stopping child because services were disabled\n")
                        log.flush()
                        child.terminate()
                        try:
                            child.wait(timeout=8)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait(timeout=3)
                        return 0
                    time.sleep(1)
                code = child.returncode
            except Exception as exc:
                log.write(f"[task] launch error: {exc!r}\n")
                code = -1
            if not services_enabled():
                log.write(f"[task] {service} exited while disabled; no retry\n")
                log.flush()
                return 0
            log.write(f"[task] {service} exited code={code}; retrying in 10s\n")
            log.flush()
            time.sleep(10)


if __name__ == "__main__":
    raise SystemExit(main())

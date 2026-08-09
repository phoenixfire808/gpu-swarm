"""
start-hidden.py — launch a gpu_swarm subcommand as a fully detached hidden process.

Replaces the fragile PowerShell/VBS wrapper that was inside scripts/run-hidden.cmd.
The .cmd scripts (start-scheduler.cmd / start-portal.cmd / start-worker.cmd /
start-all-local.cmd) call this via pythonw.exe with the same arg shape:

    pythonw.exe -m scripts.start_hidden scheduler --host 127.0.0.1 --port 8766

This file is also the unit of registration for Windows Task Scheduler.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Detached, no console window
DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from gpu_swarm.service_lifecycle import gate_detail, services_enabled
from gpu_swarm.win_subprocess import popen_kwargs

LOG_DIR = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\Drew\AppData\Local")) \
          / "GPUPool" / "logs"


def _resolve_python() -> str:
    """Pick pythonw.exe (preferred) falling back to python.exe."""
    candidates = [
        r"C:\Python313\pythonw.exe",
        r"C:\Python313\python.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    # Fall back to PATH
    for name in ("pythonw.exe", "python.exe"):
        from shutil import which
        p = which(name)
        if p:
            return p
    raise SystemExit("ERROR: Python not found for hidden service start.")


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("subcommand", help="gpu_swarm subcommand (scheduler/portal/worker/bot)")
    parser.add_argument("args", nargs=argparse.REMAINDER,
                        help="forwarded args after the subcommand")
    parser.add_argument("--help", action="store_true")

    ns = parser.parse_args()
    if ns.help or not ns.subcommand:
        parser.print_help()
        return 0
    if not services_enabled():
        print(f"GPU Pool service start suppressed: {gate_detail()}")
        return 0

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{ns.subcommand}.log"
    forwarded = [a for a in ns.args if a != "--"]

    py = _resolve_python()

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    # Don't leak any parent PYTHONPATH into the service
    env.pop("PYTHONPATH", None)

    # Header line so it's obvious when a service started (and from which py)
    with log_path.open("a", encoding="utf-8") as lf:
        lf.write(f"\n--- start {ns.subcommand} via start-hidden.py "
                 f"({py}) args={forwarded} ---\n")
        lf.flush()
        proc = subprocess.Popen(
            [py, "-m", "gpu_swarm", ns.subcommand, *forwarded],
            cwd=str(REPO_ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=lf,
            stderr=subprocess.STDOUT,
            **popen_kwargs(),
            close_fds=True,
        )

    print(f"Started {ns.subcommand} (pid {proc.pid}). Log: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

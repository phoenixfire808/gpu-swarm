"""
PyInstaller entry for GPUPool.exe.

Modes:
  (default)  Launch Contribute / Utilize / Connect desktop wizard
  --worker   Run contribution worker (spawned by the app on Join)
"""

from __future__ import annotations

import argparse
import sys


def _run_worker(argv: list[str]) -> int:
    from gpu_swarm.worker import run_worker

    parser = argparse.ArgumentParser(prog="GPUPool --worker")
    parser.add_argument("--name", default="")
    parser.add_argument("--scheduler-url", default="")
    parser.add_argument("--max-vram-mb", type=int, default=None)
    parser.add_argument("--max-cpu-percent", type=float, default=None)
    parser.add_argument("--max-ram-mb", type=int, default=None)
    parser.add_argument("--max-disk-mb", type=int, default=None)
    parser.add_argument("--discord-user", default="")
    args = parser.parse_args(argv)
    return run_worker(args)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--worker":
        return _run_worker(argv[1:])
    from gpu_swarm.app.desktop_app import run_app

    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())

"""
PyInstaller entry for GPUPool.exe.

Modes:
  (default)           Launch Contribute / Utilize / Connect desktop wizard
  --worker            Run contribution worker (spawned by the app on Join)
  --local-endpoint    Run localhost OpenAI-compatible pool API (Connect Start)
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
    parser.add_argument(
        "--host-protect",
        dest="host_protect",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Desktop GPU safety ceiling (default ON)",
    )
    parser.add_argument("--discord-user", default="")
    args = parser.parse_args(argv)
    return run_worker(args)


def _run_local_endpoint(argv: list[str]) -> int:
    from gpu_swarm.local_endpoint import run_local_endpoint

    parser = argparse.ArgumentParser(prog="GPUPool --local-endpoint")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--scheduler-url", default="")
    args = parser.parse_args(argv)
    return int(
        run_local_endpoint(
            host=args.host,
            port=args.port,
            scheduler_url=args.scheduler_url or None,
        )
    )


def _first_run_portable_bootstrap() -> None:
    """
    GPUPool.exe first-run hook for isolated Python.

    - If %LOCALAPPDATA%\\GPUPool\\venv already exists → set GPU_SWARM_PYTHON (instant).
    - If a healthy system/portable Python exists → reuse (no download).
    - Otherwise schedule background bootstrap so the UI opens immediately;
      wizard “Bootstrap portable Python” / torch install can also trigger it.
    """
    import os
    import threading

    try:
        from gpu_swarm.portable_python import (
            ensure_portable_python,
            find_usable_python,
            venv_python_exe,
        )

        vpy = venv_python_exe()
        if vpy.is_file():
            os.environ.setdefault("GPU_SWARM_PYTHON", str(vpy))
            return
        found = find_usable_python()
        if found.get("ok") and found.get("pip_ok") and found.get("executable"):
            os.environ.setdefault("GPU_SWARM_PYTHON", str(found["executable"]))
            return

        def _bg() -> None:
            try:
                ensure_portable_python(with_venv=True, with_requirements=False, dry_run=False)
            except Exception:  # noqa: BLE001
                return

        threading.Thread(target=_bg, daemon=True).start()
    except Exception:  # noqa: BLE001
        return


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--worker":
        return _run_worker(argv[1:])
    if argv and argv[0] == "--local-endpoint":
        return _run_local_endpoint(argv[1:])
    # First-run: wire portable Python path (background download if needed).
    _first_run_portable_bootstrap()
    from gpu_swarm.app.desktop_app import run_app

    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())

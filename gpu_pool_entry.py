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
    # First-run: wire portable Python path (background download if needed).
    _first_run_portable_bootstrap()
    from gpu_swarm.app.desktop_app import run_app

    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())

"""GPU Pool desktop joiner app (customtkinter)."""

from __future__ import annotations


def main() -> int:
    from gpu_swarm.app.desktop_app import run_app

    return run_app()


__all__ = ["main"]

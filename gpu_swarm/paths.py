"""Writable app data vs read-only bundle roots (PyInstaller-aware)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) or hasattr(sys, "_MEIPASS")


def bundle_root() -> Path:
    """Read-only resources shipped with the app (or repo root in source)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def app_root() -> Path:
    """
    Writable root for settings, logs, pid files, optional user .env.

    Frozen builds use %LOCALAPPDATA%\\GPUPool so we never write into the
    one-file extract dir and never bake secrets into the EXE.
    """
    if is_frozen():
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "GPUPool"
        base.mkdir(parents=True, exist_ok=True)
        (base / "data").mkdir(parents=True, exist_ok=True)
        return base
    return Path(__file__).resolve().parent.parent


BUNDLE_ROOT = bundle_root()
APP_ROOT = app_root()
# Back-compat alias used across the package: writable project/data root.
ROOT = APP_ROOT

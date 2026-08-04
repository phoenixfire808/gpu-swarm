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


def gpu_pool_home() -> Path:
    """
    Always %LOCALAPPDATA%\\GPUPool (or ~/GPUPool fallback).

    Portable Python, isolated venv, and submitable error logs live here so
    friend installs never fight global site-packages or a broken system Python.
    """
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "GPUPool"
    base.mkdir(parents=True, exist_ok=True)
    return base


def app_root() -> Path:
    """
    Writable root for settings, logs, pid files, optional user .env.

    Frozen builds use %LOCALAPPDATA%\\GPUPool so we never write into the
    one-file extract dir and never bake secrets into the EXE.
    """
    if is_frozen():
        base = gpu_pool_home()
        (base / "data").mkdir(parents=True, exist_ok=True)
        return base
    return Path(__file__).resolve().parent.parent


def portable_python_dir() -> Path:
    return gpu_pool_home() / "python"


def venv_dir() -> Path:
    return gpu_pool_home() / "venv"


def logs_dir() -> Path:
    d = gpu_pool_home() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


BUNDLE_ROOT = bundle_root()
APP_ROOT = app_root()
# Back-compat alias used across the package: writable project/data root.
ROOT = APP_ROOT
GPU_POOL_HOME = gpu_pool_home()
PORTABLE_PYTHON_DIR = portable_python_dir()
VENV_DIR = venv_dir()
LOGS_DIR = logs_dir()

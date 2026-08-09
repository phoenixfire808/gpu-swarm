"""Fail-closed lifecycle and Docker/Ollama re-enable gate for GPU Pool services."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from gpu_swarm.paths import ROOT

load_dotenv(ROOT / ".env")

SETTINGS_PATH = ROOT / "data" / "joiner_settings.json"
DOCKER_LATCH_PATH = ROOT / "data" / "docker-reenable-required.json"
LIFECYCLE_LOG = ROOT / "data" / "service-lifecycle.log"
_DOCKER_FAILURES = 0
_DOCKER_FAILURE_THRESHOLD = 3


def _log(message: str) -> None:
    try:
        LIFECYCLE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with LIFECYCLE_LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {message}\n")
    except OSError:
        pass


def services_enabled() -> bool:
    """Return whether the user explicitly enabled local GPU Pool services."""
    raw_env = os.environ.get("GPU_SWARM_SERVICES_ENABLED")
    if raw_env is not None:
        return raw_env.strip().lower() in {"1", "true", "yes", "on", "enabled"} and not docker_latched()
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict) or not bool(data.get("services_enabled", False)):
        return False
    return not docker_latched()


def gate_detail() -> str:
    if docker_latched():
        return f"Docker/Ollama re-enable required: {docker_latch_reason()}"
    return (
        "enabled"
        if services_enabled()
        else f"disabled (enable it in the desktop app; state={SETTINGS_PATH})"
    )


def configured_ollama_url() -> str | None:
    """Return an explicitly configured Ollama base URL, without exposing keys."""
    raw = (os.environ.get("GPU_SWARM_LLM_BASE_URL") or "").strip()
    for item in raw.replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            prefix, value = item.split("=", 1)
            if prefix.strip().lower() == "ollama":
                return value.strip().rstrip("/") or None
    host = (os.environ.get("OLLAMA_HOST") or "").strip().rstrip("/")
    return host or None


def docker_guard_required() -> bool:
    raw = os.environ.get("GPU_SWARM_DOCKER_GUARD")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on", "enabled"}
    return configured_ollama_url() is not None


def docker_latched() -> bool:
    return DOCKER_LATCH_PATH.is_file()


def docker_latch_reason() -> str:
    try:
        data = json.loads(DOCKER_LATCH_PATH.read_text(encoding="utf-8"))
        return str(data.get("reason") or "Docker/Ollama health check failed")[:240]
    except (OSError, json.JSONDecodeError, AttributeError):
        return "Docker/Ollama health check failed"


def latch_docker_down(reason: str) -> None:
    DOCKER_LATCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"reason": str(reason)[:240], "latched_at": time.time()}
    tmp = DOCKER_LATCH_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(DOCKER_LATCH_PATH)
    _log(f"docker_guard latched: {payload['reason']}")


def clear_docker_latch() -> None:
    try:
        DOCKER_LATCH_PATH.unlink()
        _log("docker_guard cleared after successful health check")
    except FileNotFoundError:
        pass
    except OSError as exc:
        _log(f"docker_guard clear failed: {type(exc).__name__}")


def docker_health(*, timeout: float = 1.5) -> tuple[bool, str]:
    base = configured_ollama_url()
    if not base:
        return True, "no explicit Ollama provider configured"
    url = f"{base}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if int(response.status) != 200:
                return False, f"Ollama health HTTP {response.status}"
        return True, "Ollama API healthy"
    except urllib.error.HTTPError as exc:
        return False, f"Ollama health HTTP {exc.code}"
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return False, f"Ollama/Docker unreachable ({type(exc).__name__})"


def docker_guard(*, timeout: float = 1.5) -> tuple[bool, str]:
    """Require a manual re-enable after three consecutive Ollama/Docker failures."""
    global _DOCKER_FAILURES
    if not docker_guard_required():
        return True, "Docker guard not required"
    if docker_latched():
        return False, docker_latch_reason()
    healthy, detail = docker_health(timeout=timeout)
    if healthy:
        _DOCKER_FAILURES = 0
        return True, detail
    _DOCKER_FAILURES += 1
    if _DOCKER_FAILURES < _DOCKER_FAILURE_THRESHOLD:
        _log(f"docker_guard transient failure {_DOCKER_FAILURES}/{_DOCKER_FAILURE_THRESHOLD}: {detail}")
        return True, f"transient Docker/Ollama failure {_DOCKER_FAILURES}/{_DOCKER_FAILURE_THRESHOLD}: {detail}"
    latch_docker_down(detail)
    return False, detail


def docker_reenable_check(*, timeout: float = 2.0) -> tuple[bool, str]:
    """Health-check before clearing the manual outage latch."""
    healthy, detail = docker_health(timeout=timeout)
    if not healthy:
        return False, detail
    global _DOCKER_FAILURES
    _DOCKER_FAILURES = 0
    clear_docker_latch()
    return True, detail

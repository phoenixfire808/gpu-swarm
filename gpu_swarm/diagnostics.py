"""
Collect + submit install/join diagnostic logs for friend debugging.

Writes: %LOCALAPPDATA%\\GPUPool\\logs\\error-<timestamp>.log
Submit: POST portal /api/diagnostics (redacts tokens/secrets)
Fallback: clipboard / mailto when portal unreachable
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from gpu_swarm.paths import LOGS_DIR, ROOT, gpu_pool_home, is_frozen, logs_dir
from gpu_swarm.win_subprocess import run_kwargs

# In-memory last failure context (wizard / join sets these).
_LAST_TRACEBACK: str = ""
_LAST_WIZARD_STEP: str = ""
_LAST_CONTEXT: dict[str, Any] = {}

MAX_LOG_BYTES = 256_000
MAX_SUBMIT_BYTES = 200_000

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)(GPU_SWARM_START_TOKEN|DISCORD_BOT_TOKEN|BOT_TOKEN)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(pool_password|invite_session)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(sk-[A-Za-z0-9]{20,})"),
    re.compile(r"(?i)(AIza[0-9A-Za-z\-_]{20,})"),
)


def set_wizard_step(step: str) -> None:
    global _LAST_WIZARD_STEP
    _LAST_WIZARD_STEP = (step or "").strip()[:120]


def set_last_failure(
    *,
    traceback_text: str = "",
    wizard_step: str = "",
    context: dict[str, Any] | None = None,
) -> None:
    global _LAST_TRACEBACK, _LAST_WIZARD_STEP, _LAST_CONTEXT
    if traceback_text:
        _LAST_TRACEBACK = traceback_text[-12000:]
    if wizard_step:
        _LAST_WIZARD_STEP = wizard_step.strip()[:120]
    if context:
        _LAST_CONTEXT = dict(context)


def redact_secrets(text: str) -> str:
    out = text or ""
    for pat in _SECRET_PATTERNS:
        out = pat.sub(lambda m: (m.group(1) if m.lastindex else "") + "[REDACTED]", out)
    # Cookie / session fragments
    out = re.sub(
        r"(?i)(gpu_swarm_portal_session=)[^;\s]+",
        r"\1[REDACTED]",
        out,
    )
    return out


def _safe_run(cmd: list[str], *, timeout: float = 20) -> str:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            **run_kwargs(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"(failed: {exc})"
    out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    return out.strip() or f"(exit {proc.returncode}, empty output)"


def _pip_freeze(python_exe: str | None = None) -> str:
    exe = python_exe or sys.executable
    if is_frozen() and (not python_exe or Path(exe).resolve() == Path(sys.executable).resolve()):
        try:
            from gpu_swarm.portable_python import resolve_pip_python

            alt = resolve_pip_python()
            if alt:
                exe = alt
            else:
                return "(frozen EXE — no separate pip Python; portable/venv not bootstrapped yet)"
        except Exception:  # noqa: BLE001
            return "(frozen EXE — pip freeze unavailable)"
    return _safe_run([exe, "-m", "pip", "freeze"], timeout=60)


def _nvidia_smi() -> str:
    return _safe_run(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total,memory.free",
            "--format=csv",
        ],
        timeout=15,
    )


def _scheduler_url_test(url: str) -> str:
    url = (url or "").rstrip("/")
    if not url:
        return "(no scheduler URL)"
    target = f"{url}/status"
    try:
        import httpx

        r = httpx.get(target, timeout=5.0)
        body = (r.text or "")[:500]
        return f"GET {target} → HTTP {r.status_code}\n{body}"
    except Exception as exc:  # noqa: BLE001
        return f"GET {target} → FAILED: {exc}"


def _tail_file(path: Path, lines: int = 80) -> str:
    if not path.is_file():
        return f"(missing {path})"
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return f"(read failed: {exc})"
    return "\n".join(raw[-lines:])


def collect_diagnostics(
    *,
    wizard_step: str | None = None,
    scheduler_url: str = "",
    portal_url: str = "",
    extra: dict[str, Any] | None = None,
    include_traceback: str | None = None,
) -> dict[str, Any]:
    """Gather a structured diagnostic payload (secrets redacted in text form)."""
    step = wizard_step if wizard_step is not None else _LAST_WIZARD_STEP
    tb = include_traceback if include_traceback is not None else _LAST_TRACEBACK
    if not tb:
        # Capture current exception if any
        tb = traceback.format_exc()
        if tb.strip() == "NoneType: None":
            tb = ""

    pip_python = ""
    try:
        from gpu_swarm.portable_python import python_runtime_report, resolve_pip_python

        py_report = python_runtime_report()
        pip_python = resolve_pip_python() or ""
    except Exception as exc:  # noqa: BLE001
        py_report = {"error": str(exc)}
        pip_python = ""

    worker_log = ROOT / "data" / "joiner_worker.log"
    payload: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": platform.node(),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "platform": platform.platform(),
        },
        "python": {
            "app_executable": sys.executable,
            "app_version": sys.version,
            "frozen": is_frozen(),
            "pip_python": pip_python,
            "report": py_report,
        },
        "paths": {
            "gpu_pool_home": str(gpu_pool_home()),
            "root": str(ROOT),
            "logs_dir": str(logs_dir()),
        },
        "wizard_step": step or "",
        "scheduler_url": scheduler_url or os.environ.get("GPU_SWARM_SCHEDULER_URL", ""),
        "portal_url": portal_url or "",
        "nvidia_smi": _nvidia_smi(),
        "pip_freeze": _pip_freeze(pip_python or None),
        "scheduler_test": _scheduler_url_test(
            scheduler_url or os.environ.get("GPU_SWARM_SCHEDULER_URL", "")
        ),
        "worker_log_tail": _tail_file(worker_log),
        "last_traceback": tb,
        "context": {**(extra or {}), **_LAST_CONTEXT},
        "env_safe": {
            k: v
            for k, v in os.environ.items()
            if k.startswith("GPU_SWARM_")
            and "TOKEN" not in k.upper()
            and "PASSWORD" not in k.upper()
            and "SECRET" not in k.upper()
        },
    }
    return payload


def format_diagnostics_text(payload: dict[str, Any]) -> str:
    lines = [
        "=== GPU Pool diagnostic log ===",
        f"timestamp_utc: {payload.get('timestamp_utc')}",
        f"hostname: {payload.get('hostname')}",
        f"wizard_step: {payload.get('wizard_step')}",
        "",
        "--- OS ---",
        json.dumps(payload.get("os") or {}, indent=2),
        "",
        "--- Python ---",
        json.dumps(payload.get("python") or {}, indent=2, default=str),
        "",
        "--- Paths ---",
        json.dumps(payload.get("paths") or {}, indent=2),
        "",
        f"scheduler_url: {payload.get('scheduler_url')}",
        f"portal_url: {payload.get('portal_url')}",
        "",
        "--- nvidia-smi ---",
        str(payload.get("nvidia_smi") or "(none)"),
        "",
        "--- scheduler URL test ---",
        str(payload.get("scheduler_test") or ""),
        "",
        "--- pip freeze ---",
        str(payload.get("pip_freeze") or ""),
        "",
        "--- worker log tail ---",
        str(payload.get("worker_log_tail") or ""),
        "",
        "--- last traceback ---",
        str(payload.get("last_traceback") or "(none)"),
        "",
        "--- context ---",
        json.dumps(payload.get("context") or {}, indent=2, default=str),
        "",
        "--- env (safe GPU_SWARM_*) ---",
        json.dumps(payload.get("env_safe") or {}, indent=2),
        "",
        "=== end ===",
        "",
    ]
    return redact_secrets("\n".join(lines))


def write_error_log(
    *,
    wizard_step: str | None = None,
    scheduler_url: str = "",
    portal_url: str = "",
    extra: dict[str, Any] | None = None,
    include_traceback: str | None = None,
    reason: str = "error",
) -> dict[str, Any]:
    """Collect diagnostics and write error-*.log under LocalAppData\\GPUPool\\logs."""
    payload = collect_diagnostics(
        wizard_step=wizard_step,
        scheduler_url=scheduler_url,
        portal_url=portal_url,
        extra=extra,
        include_traceback=include_traceback,
    )
    text = format_diagnostics_text(payload)
    if len(text.encode("utf-8")) > MAX_LOG_BYTES:
        text = text.encode("utf-8")[:MAX_LOG_BYTES].decode("utf-8", errors="ignore")
        text += "\n\n[truncated]\n"

    logs_dir().mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_reason = re.sub(r"[^a-zA-Z0-9_-]+", "-", (reason or "error"))[:40].strip("-") or "error"
    path = LOGS_DIR / f"error-{stamp}-{safe_reason}.log"
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        return {
            "ok": False,
            "message": f"Could not write log: {exc}",
            "path": str(path),
            "text": text,
            "payload": payload,
        }
    # Also keep a JSON sibling for machine parse (redacted text already).
    json_path = path.with_suffix(".json")
    try:
        redacted_payload = json.loads(redact_secrets(json.dumps(payload, default=str)))
        json_path.write_text(json.dumps(redacted_payload, indent=2) + "\n", encoding="utf-8")
    except Exception:  # noqa: BLE001
        json_path = None
    return {
        "ok": True,
        "path": str(path),
        "json_path": str(json_path) if json_path else "",
        "text": text,
        "bytes": len(text.encode("utf-8")),
        "message": f"Diagnostic log written: {path}",
        "payload": payload,
    }


def zip_error_log(log_path: str | Path) -> dict[str, Any]:
    path = Path(log_path)
    if not path.is_file():
        return {"ok": False, "message": f"Missing {path}"}
    zpath = path.with_suffix(path.suffix + ".zip")
    try:
        with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(path, arcname=path.name)
            sibling = path.with_suffix(".json")
            if sibling.is_file():
                zf.write(sibling, arcname=sibling.name)
    except OSError as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "path": str(zpath), "message": f"Zip ready: {zpath}"}


def submit_diagnostics(
    *,
    portal_url: str,
    log_path: str | Path | None = None,
    text: str | None = None,
    display_name: str = "",
    invite_code: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """
    POST diagnostics to portal /api/diagnostics.

    Auth: invite session cookie/token OR invite_code + display_name (same as portal login).
    On failure: returns clipboard/mailto fallbacks (no exception).
    """
    body_text = text or ""
    if log_path and not body_text:
        try:
            body_text = Path(log_path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {"ok": False, "message": f"Cannot read log: {exc}", "fallback": "clipboard"}
    body_text = redact_secrets(body_text)
    if len(body_text.encode("utf-8")) > MAX_SUBMIT_BYTES:
        body_text = body_text.encode("utf-8")[:MAX_SUBMIT_BYTES].decode("utf-8", errors="ignore")
        body_text += "\n\n[truncated for submit]\n"

    base = (portal_url or "").rstrip("/")
    if base.endswith("/portal"):
        api = base[: -len("/portal")] + "/api/diagnostics"
    elif base.endswith("/api/diagnostics"):
        api = base
    else:
        api = base + "/api/diagnostics"

    payload = {
        "display_name": (display_name or platform.node())[:64],
        "invite_code": invite_code or "",
        "hostname": platform.node(),
        "wizard_step": _LAST_WIZARD_STEP,
        "log_text": body_text,
        "log_path": str(log_path or ""),
        "client_time": time.time(),
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "GPUPool-Diagnostics/1.0",
    }
    if session_token:
        headers["Cookie"] = f"gpu_swarm_portal_session={session_token}"

    mailto = (
        "mailto:drew@localhost?subject=GPU%20Pool%20diagnostics&body="
        "(paste%20log%20from%20clipboard%20-%20see%20Copy%20log%20in%20app)"
    )
    fallback = {
        "clipboard": body_text,
        "mailto": mailto,
        "log_path": str(log_path or ""),
        "hint": "Portal unreachable — use Copy log and paste to the host in Discord.",
    }

    try:
        req = Request(api, data=data, headers=headers, method="POST")
        with urlopen(req, timeout=20) as resp:  # noqa: S310 — portal URL from settings
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"raw": raw}
            return {
                "ok": True,
                "message": parsed.get("message") or f"Submitted to {api}",
                "api": api,
                "response": parsed,
                "id": parsed.get("id") or "",
            }
    except HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:  # noqa: BLE001
            detail = str(exc)
        return {
            "ok": False,
            "message": f"Portal rejected diagnostics ({exc.code}): {detail}",
            "api": api,
            "fallback": "clipboard",
            **fallback,
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "message": f"Portal down or unreachable: {exc}",
            "api": api,
            "fallback": "clipboard",
            **fallback,
        }


def record_failure_and_write(
    *,
    message: str,
    wizard_step: str = "",
    scheduler_url: str = "",
    portal_url: str = "",
    fix: str = "",
    log_tail: str = "",
    exc: BaseException | None = None,
) -> dict[str, Any]:
    """Convenience: stash failure context + write error-*.log."""
    tb = ""
    if exc is not None:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    elif sys.exc_info()[0] is not None:
        tb = traceback.format_exc()
    set_last_failure(
        traceback_text=tb or message,
        wizard_step=wizard_step,
        context={"message": message, "fix": fix, "log_tail": (log_tail or "")[-4000:]},
    )
    return write_error_log(
        wizard_step=wizard_step,
        scheduler_url=scheduler_url,
        portal_url=portal_url,
        extra={"message": message, "fix": fix},
        include_traceback=tb or message,
        reason="join-fail" if "join" in (wizard_step or "").lower() else "error",
    )

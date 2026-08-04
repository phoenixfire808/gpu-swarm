"""Detect local OpenAI-compatible / Ollama runtimes for llm_chat jobs."""

from __future__ import annotations

import os
from typing import Any

import httpx

# Contributor enablement copy — surfaced in job errors and LOCAL_MODEL.md
ENABLE_LLM_HELP = (
    "No local LLM runtime on this worker.\n"
    "To enable llm_chat jobs on a contributor machine:\n"
    "  1. Install Ollama from https://ollama.com (or any OpenAI-compatible server)\n"
    "  2. Pull a model:  ollama pull llama3.2\n"
    "  3. Keep it running (ollama serve) on http://127.0.0.1:11434\n"
    "  4. Restart the GPU Pool worker so it re-detects llm_ready\n"
    "Optional: set GPU_SWARM_LLM_BASE_URL=http://127.0.0.1:PORT/v1 "
    "(OpenAI-compatible) or OLLAMA_HOST=http://127.0.0.1:11434"
)


def _candidate_bases() -> list[tuple[str, str]]:
    """Return (kind, base_url_without_trailing_slash) candidates."""
    out: list[tuple[str, str]] = []
    custom = (os.environ.get("GPU_SWARM_LLM_BASE_URL") or "").strip().rstrip("/")
    if custom:
        if custom.endswith("/v1"):
            out.append(("openai", custom[: -len("/v1")]))
        else:
            out.append(("openai", custom))
    ollama = (os.environ.get("OLLAMA_HOST") or "").strip().rstrip("/")
    if ollama:
        out.append(("ollama", ollama))
    for kind, base in (
        ("ollama", "http://127.0.0.1:11434"),
        ("openai", "http://127.0.0.1:1234"),
    ):
        if all(b != base for _, b in out):
            out.append((kind, base))
    return out


_DETECT_CACHE: dict[str, Any] = {"ts": 0.0, "result": None}
_DETECT_TTL_SEC = 20.0


def detect_llm_runtime(*, timeout: float = 0.6, force: bool = False) -> dict[str, Any]:
    """Probe localhost for Ollama or OpenAI-compatible chat API (cached ~20s)."""
    import time as _time

    now = _time.time()
    if (
        not force
        and _DETECT_CACHE["result"] is not None
        and (now - float(_DETECT_CACHE["ts"])) < _DETECT_TTL_SEC
    ):
        return dict(_DETECT_CACHE["result"])  # type: ignore[arg-type]

    last_err = "no candidate LLM endpoints responded"
    models: list[str] = []
    result: dict[str, Any]
    for kind, base in _candidate_bases():
        openai_base = f"{base}/v1"
        try:
            with httpx.Client(timeout=timeout) as client:
                if kind == "ollama":
                    r = client.get(f"{base}/api/tags")
                    if r.status_code == 200:
                        data = r.json()
                        models = [
                            str(m.get("name") or m.get("model") or "")
                            for m in (data.get("models") or [])
                            if isinstance(m, dict)
                        ]
                        models = [m for m in models if m]
                        result = {
                            "ready": True,
                            "kind": "ollama",
                            "base_url": base,
                            "openai_base": openai_base,
                            "models": models,
                            "error": None,
                        }
                        _DETECT_CACHE["ts"] = now
                        _DETECT_CACHE["result"] = result
                        return dict(result)
                    last_err = f"Ollama {base}/api/tags → HTTP {r.status_code}"
                r = client.get(f"{openai_base}/models")
                if r.status_code == 200:
                    data = r.json()
                    raw = data.get("data") if isinstance(data, dict) else None
                    if isinstance(raw, list):
                        models = [
                            str(m.get("id") or "")
                            for m in raw
                            if isinstance(m, dict) and m.get("id")
                        ]
                    result = {
                        "ready": True,
                        "kind": "openai",
                        "base_url": base,
                        "openai_base": openai_base,
                        "models": models,
                        "error": None,
                    }
                    _DETECT_CACHE["ts"] = now
                    _DETECT_CACHE["result"] = result
                    return dict(result)
                last_err = f"{openai_base}/models → HTTP {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = f"{base}: {exc}"
            continue
    result = {
        "ready": False,
        "kind": None,
        "base_url": None,
        "openai_base": None,
        "models": [],
        "error": last_err,
        "help": ENABLE_LLM_HELP,
    }
    _DETECT_CACHE["ts"] = now
    _DETECT_CACHE["result"] = result
    return dict(result)


def chat_completions(
    *,
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 512,
    temperature: float | None = None,
    timeout: float = 300.0,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call local OpenAI-compatible /v1/chat/completions."""
    rt = runtime or detect_llm_runtime(timeout=2.0)
    if not rt.get("ready") or not rt.get("openai_base"):
        raise RuntimeError(rt.get("help") or ENABLE_LLM_HELP)

    openai_base = str(rt["openai_base"]).rstrip("/")
    body: dict[str, Any] = {
        "model": model or (rt["models"][0] if rt.get("models") else "llama3.2"),
        "messages": messages,
        "max_tokens": max(1, min(int(max_tokens or 512), 8192)),
        "stream": False,
    }
    if temperature is not None:
        body["temperature"] = float(temperature)

    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{openai_base}/chat/completions", json=body)
        if r.status_code >= 400:
            detail = r.text[:2000]
            raise RuntimeError(
                f"LLM runtime error HTTP {r.status_code} at {openai_base}/chat/completions: {detail}"
            )
        data = r.json()
    if not isinstance(data, dict):
        raise RuntimeError("LLM runtime returned non-object JSON")
    data["_gpu_pool_runtime"] = {
        "kind": rt.get("kind"),
        "base_url": rt.get("base_url"),
        "model_requested": body["model"],
    }
    return data

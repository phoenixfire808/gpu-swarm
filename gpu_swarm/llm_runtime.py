"""Discover and call contributor-local LLM runtimes.

Supported contributor runtimes:
- Ollama (native ``/api/tags`` plus OpenAI-compatible chat endpoint)
- LM Studio, vLLM, llama.cpp, or any compatible server (``/v1/models``)

Only provider kind, sanitized base URL, model IDs, and readiness are advertised
upstream. API keys remain local to the worker process and are never returned in
status payloads.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

ENABLE_LLM_HELP = (
    "No local LLM runtime on this worker.\n"
    "To mount your own model for shared GPU Pool use:\n"
    "  1. Run Ollama, LM Studio, vLLM, llama.cpp, or another OpenAI-compatible server locally.\n"
    "  2. Set GPU_SWARM_LLM_BASE_URL to its base URL (for example http://127.0.0.1:1234/v1).\n"
    "  3. Make sure the model is loaded/listed, then restart or wait for the worker heartbeat.\n"
    "  4. The model will appear in the Discord /models picker and the local /v1/models list.\n"
    "Ollama default: http://127.0.0.1:11434. LM Studio default: http://127.0.0.1:1234."
)

_DETECT_CACHE: dict[str, Any] = {"ts": 0.0, "result": None}
_DETECT_TTL_SEC = 20.0


def _normalize_base(value: str) -> str:
    return value.strip().rstrip("/")


def _candidate_bases() -> list[tuple[str, str]]:
    """Return ordered ``(provider, base_url_without_/v1)`` candidates.

    ``GPU_SWARM_LLM_BASE_URL`` accepts comma/semicolon-separated values. A
    value may be prefixed with ``ollama=`` or ``openai=``; unprefixed values
    use the OpenAI-compatible protocol.
    """
    out: list[tuple[str, str]] = []
    raw_custom = (os.environ.get("GPU_SWARM_LLM_BASE_URL") or "").strip()
    for raw in re.split(r"[,;]", raw_custom):
        item = raw.strip()
        if not item:
            continue
        provider = "openai-compatible"
        if "=" in item and item.split("=", 1)[0].lower() in {"ollama", "openai", "vllm", "lmstudio", "llama.cpp"}:
            prefix, item = item.split("=", 1)
            provider = "ollama" if prefix.lower() == "ollama" else "openai-compatible"
        item = _normalize_base(item)
        if item.endswith("/v1"):
            item = item[:-3].rstrip("/")
        if item and all(existing != item for _, existing in out):
            out.append((provider, item))

    ollama = _normalize_base(os.environ.get("OLLAMA_HOST") or "")
    if ollama and all(existing != ollama for _, existing in out):
        out.append(("ollama", ollama))

    defaults = (
        ("ollama", "http://127.0.0.1:11434"),
        ("openai-compatible", "http://127.0.0.1:1234"),
    )
    for provider, base in defaults:
        if all(existing != base for _, existing in out):
            out.append((provider, base))
    return out


def _headers() -> dict[str, str]:
    # Optional local/provider key. Never include it in a returned runtime dict.
    key = (os.environ.get("GPU_SWARM_LLM_API_KEY") or "").strip()
    return {"Authorization": f"Bearer {key}"} if key else {}


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _unique_models(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        model = str(value or "").strip()
        if model and "embed" not in model.lower() and model not in result:
            result.append(model)
    return result[:64]


def discover_llm_runtimes(*, timeout: float = 0.6, force: bool = False) -> dict[str, Any]:
    """Probe all configured local providers and return safe model mounts."""
    import time

    now = time.time()
    if (
        not force
        and _DETECT_CACHE["result"] is not None
        and now - float(_DETECT_CACHE["ts"]) < _DETECT_TTL_SEC
    ):
        return dict(_DETECT_CACHE["result"])

    runtimes: list[dict[str, Any]] = []
    errors: list[str] = []
    for provider, base in _candidate_bases():
        openai_base = f"{base}/v1"
        try:
            with httpx.Client(timeout=timeout, headers=_headers()) as client:
                models: list[str] = []
                model_records: list[dict[str, Any]] = []
                loaded_models: list[dict[str, Any]] = []
                if provider == "ollama":
                    response = client.get(f"{base}/api/tags")
                    if response.status_code == 200:
                        payload = response.json()
                        for item in (payload.get("models") or []) if isinstance(payload, dict) else []:
                            if not isinstance(item, dict):
                                continue
                            name = str(item.get("name") or item.get("model") or "").strip()
                            if not name or "embed" in name.lower() or name in models:
                                continue
                            models.append(name)
                            model_records.append(
                                {"model": name, "size_bytes": _safe_int(item.get("size"))}
                            )
                        ps_response = client.get(f"{base}/api/ps")
                        if ps_response.status_code == 200:
                            ps_payload = ps_response.json()
                            for item in (ps_payload.get("models") or []) if isinstance(ps_payload, dict) else []:
                                if not isinstance(item, dict):
                                    continue
                                name = str(item.get("name") or item.get("model") or "").strip()
                                if name:
                                    loaded_models.append(
                                        {
                                            "model": name,
                                            "size_bytes": _safe_int(item.get("size")),
                                            "size_vram_bytes": _safe_int(item.get("size_vram")),
                                            "context_length": _safe_int(item.get("context_length")),
                                        }
                                    )
                    else:
                        errors.append(f"Ollama {base}/api/tags HTTP {response.status_code}")
                        continue
                else:
                    response = client.get(f"{openai_base}/models")
                    if response.status_code == 200:
                        payload = response.json()
                        raw = payload.get("data") if isinstance(payload, dict) else []
                        models = _unique_models(
                            [
                                str(item.get("id") or "")
                                for item in (raw if isinstance(raw, list) else [])
                                if isinstance(item, dict)
                            ]
                        )
                        model_records = [{"model": model} for model in models]
                    else:
                        errors.append(f"{openai_base}/models HTTP {response.status_code}")
                        continue
                runtimes.append(
                    {
                        "provider": provider,
                        "kind": provider,
                        "base_url": base,
                        "openai_base": openai_base,
                        "models": models,
                        "model_records": model_records,
                        "loaded_models": loaded_models,
                        "ready": True,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{base}: {exc}")

    all_models = _unique_models(
        [model for runtime in runtimes for model in runtime.get("models") or []]
    )
    result: dict[str, Any] = {
        "ready": bool(runtimes),
        "runtimes": runtimes,
        "models": all_models,
        "error": None if runtimes else (errors[-1] if errors else "no candidate LLM endpoints responded"),
        "help": ENABLE_LLM_HELP,
    }
    _DETECT_CACHE["ts"] = now
    _DETECT_CACHE["result"] = result
    return dict(result)


def runtime_mounts(discovery: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Flatten provider runtimes into safe model mount records for the scheduler."""
    discovery = discovery or discover_llm_runtimes()
    mounts: list[dict[str, Any]] = []
    for runtime in discovery.get("runtimes") or []:
        records = {
            str(item.get("model")): item
            for item in (runtime.get("model_records") or [])
            if isinstance(item, dict) and item.get("model")
        }
        loaded = {
            str(item.get("model")): item
            for item in (runtime.get("loaded_models") or [])
            if isinstance(item, dict) and item.get("model")
        }
        for model in runtime.get("models") or []:
            name = str(model)
            record = records.get(name) or {}
            loaded_record = loaded.get(name) or {}
            mounts.append(
                {
                    "model": name,
                    "provider": runtime.get("provider") or runtime.get("kind") or "openai-compatible",
                    "base_url": runtime.get("base_url"),
                    "openai_base": runtime.get("openai_base"),
                    "model_size_mb": round(_safe_int(record.get("size_bytes")) / 1048576),
                    "loaded": bool(loaded_record),
                    "loaded_vram_mb": round(_safe_int(loaded_record.get("size_vram_bytes")) / 1048576),
                    "context_length": _safe_int(loaded_record.get("context_length")),
                }
            )
    return mounts[:64]


def detect_llm_runtime(*, timeout: float = 0.6, force: bool = False) -> dict[str, Any]:
    """Backward-compatible first-ready runtime plus all discovered mounts."""
    result = discover_llm_runtimes(timeout=timeout, force=force)
    first = (result.get("runtimes") or [None])[0]
    if first:
        return {
            **result,
            "kind": first.get("kind"),
            "provider": first.get("provider"),
            "base_url": first.get("base_url"),
            "openai_base": first.get("openai_base"),
            "models": list(first.get("models") or []),
            "mounts": runtime_mounts(result),
        }
    return {
        **result,
        "kind": None,
        "provider": None,
        "base_url": None,
        "openai_base": None,
        "models": [],
        "mounts": [],
    }


def chat_completions(
    *,
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 512,
    temperature: float | None = None,
    timeout: float = 300.0,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call a contributor-local OpenAI-compatible ``/v1/chat/completions`` endpoint."""
    rt = runtime or detect_llm_runtime(timeout=2.0)
    if not rt.get("ready") or not rt.get("openai_base"):
        raise RuntimeError(rt.get("help") or ENABLE_LLM_HELP)
    requested_model = model or (rt.get("models") or ["llama3.2"])[0]
    limit = max(1, min(int(max_tokens or 512), 8192))
    is_ollama = str(rt.get("kind") or "").lower() == "ollama"
    if is_ollama:
        # Ollama's OpenAI-compatibility layer may expose reasoning-only output
        # even when an extra `think` field is supplied. Use the native API for
        # its explicit thinking switch, then normalize the response below.
        body: dict[str, Any] = {
            "model": requested_model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"num_predict": limit},
        }
        if temperature is not None:
            body["options"]["temperature"] = float(temperature)
        path = f"{str(rt['base_url']).rstrip('/')}/api/chat"
    else:
        body = {
            "model": requested_model,
            "messages": messages,
            "max_tokens": limit,
            "stream": False,
        }
        if temperature is not None:
            body["temperature"] = float(temperature)
        path = f"{str(rt['openai_base']).rstrip('/')}/chat/completions"
    with httpx.Client(timeout=timeout, headers=_headers()) as client:
        response = client.post(path, json=body)
        if response.status_code >= 400:
            raise RuntimeError(
                f"LLM runtime error HTTP {response.status_code} at {path}: {response.text[:2000]}"
            )
        raw = response.json()
    if is_ollama:
        if not isinstance(raw, dict):
            raise RuntimeError("Ollama runtime returned non-object JSON")
        message = raw.get("message") if isinstance(raw.get("message"), dict) else {}
        data: dict[str, Any] = {
            "id": f"ollama-{raw.get('created_at') or 'completion'}",
            "object": "chat.completion",
            "model": raw.get("model") or requested_model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": message.get("role") or "assistant",
                        "content": message.get("content") or "",
                    },
                    "finish_reason": "stop" if raw.get("done", True) else None,
                }
            ],
            "usage": {
                "prompt_tokens": int(raw.get("prompt_eval_count") or 0),
                "completion_tokens": int(raw.get("eval_count") or 0),
                "total_tokens": int((raw.get("prompt_eval_count") or 0) + (raw.get("eval_count") or 0)),
            },
        }
    else:
        data = raw
    if not isinstance(data, dict):
        raise RuntimeError("LLM runtime returned non-object JSON")
    data["_gpu_pool_runtime"] = {
        "kind": rt.get("kind"),
        "provider": rt.get("provider"),
        "base_url": rt.get("base_url"),
        "model_requested": requested_model,
    }
    return data

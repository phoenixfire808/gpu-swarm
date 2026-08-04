"""Local Pool Endpoint — OpenAI/Ollama-compatible localhost API → GPU Pool llm_chat.

Friends point Open WebUI / LM Studio / Continue / Cursor at::

    http://127.0.0.1:8080/v1
    OPENAI_BASE_URL=http://127.0.0.1:8080/v1

This is a **network GPU via API**, not a fake Windows display adapter.
"""

from __future__ import annotations

import argparse
import os
import socket
import time
import uuid
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from gpu_swarm.client import DEFAULT_SCHEDULER_URL, GPUPool, GPUPoolError

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
ALT_PORT = 11434
DEFAULT_MODEL_ID = "gpu-pool"


def _scheduler_url(explicit: str | None = None) -> str:
    if explicit:
        return explicit.rstrip("/")
    env = (os.environ.get("GPU_SWARM_SCHEDULER_URL") or "").strip()
    if env:
        return env.rstrip("/")
    return DEFAULT_SCHEDULER_URL


def _port_free(host: str, port: int) -> bool:
    """Return True if nothing is accepting on host:port and bind would succeed.

    Avoid SO_REUSEADDR-only checks on Windows — they can claim a busy port is free.
    """
    probe_host = "127.0.0.1" if host in ("0.0.0.0", "", "::", "[::]") else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.35)
        try:
            if s.connect_ex((probe_host, int(port))) == 0:
                return False
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, int(port)))
            return True
        except OSError:
            return False


def pick_listen_port(host: str, preferred: int | None = None) -> int:
    if preferred is not None:
        return int(preferred)
    env = (os.environ.get("GPU_SWARM_LOCAL_ENDPOINT_PORT") or "").strip()
    if env:
        try:
            return int(env)
        except ValueError:
            pass
    for port in (DEFAULT_PORT, ALT_PORT):
        if _port_free(host, port):
            return port
    return DEFAULT_PORT


def create_app(*, scheduler_url: str | None = None, submitted_by: str = "local-endpoint") -> FastAPI:
    base = _scheduler_url(scheduler_url)
    app = FastAPI(
        title="GPU Pool Local Model Endpoint",
        description=(
            "OpenAI-compatible localhost shim. Chat/completions become allowlisted "
            "llm_chat jobs on the GPU Pool scheduler."
        ),
        version="0.1.0",
    )
    app.state.scheduler_url = base
    app.state.submitted_by = submitted_by

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "service": "gpu-pool-local-endpoint",
            "openai_base": "/v1",
            "scheduler_url": app.state.scheduler_url,
            "honesty": (
                "Network GPU via OpenAI-compatible API — not a PCI/Windows display adapter. "
                "See LOCAL_MODEL.md"
            ),
            "endpoints": [
                "GET /v1/models",
                "POST /v1/chat/completions",
                "GET /api/tags",
                "GET /health",
            ],
        }

    @app.get("/health")
    async def health() -> dict[str, Any]:
        pool_ok = False
        detail = ""
        try:
            st = GPUPool(scheduler_url=app.state.scheduler_url, timeout=5.0).status()
            pool_ok = True
            detail = f"workers_online={st.get('workers_online')}"
        except Exception as exc:  # noqa: BLE001
            detail = str(exc)
        return {
            "ok": True,
            "scheduler_ok": pool_ok,
            "scheduler_url": app.state.scheduler_url,
            "detail": detail,
        }

    @app.get("/v1/models")
    async def list_models() -> dict[str, Any]:
        models = _model_catalog(app.state.scheduler_url)
        now = int(time.time())
        return {
            "object": "list",
            "data": [
                {
                    "id": mid,
                    "object": "model",
                    "created": now,
                    "owned_by": "gpu-pool",
                }
                for mid in models
            ],
        }

    @app.get("/api/tags")
    async def ollama_tags() -> dict[str, Any]:
        models = _model_catalog(app.state.scheduler_url)
        return {
            "models": [
                {
                    "name": mid,
                    "model": mid,
                    "modified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "size": 0,
                    "digest": "gpu-pool",
                    "details": {"family": "gpu-pool", "parameter_size": "pool"},
                }
                for mid in models
            ]
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"invalid JSON body: {exc}") from exc
        if not isinstance(body, dict):
            raise HTTPException(400, "body must be a JSON object")

        if body.get("stream"):
            raise HTTPException(
                400,
                "stream=true not supported yet on local endpoint. "
                "Set stream=false (default) — Open WebUI / most clients work without streaming.",
            )

        model = str(body.get("model") or DEFAULT_MODEL_ID).strip() or DEFAULT_MODEL_ID
        messages = body.get("messages") or []
        if not isinstance(messages, list) or not messages:
            raise HTTPException(400, "messages must be a non-empty list")

        max_tokens = body.get("max_tokens", body.get("max_completion_tokens", 512))
        try:
            max_tokens = int(max_tokens or 512)
        except (TypeError, ValueError):
            max_tokens = 512
        max_tokens = max(1, min(max_tokens, 8192))

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if body.get("temperature") is not None:
            payload["temperature"] = body.get("temperature")

        pool = GPUPool(
            scheduler_url=app.state.scheduler_url,
            timeout=60.0,
            submitted_by=app.state.submitted_by,
        )
        wait_timeout = float(os.environ.get("GPU_SWARM_LLM_WAIT_TIMEOUT", "300") or 300)
        try:
            job = pool.submit(
                "llm_chat",
                payload,
                require_gpu=False,
                wait=True,
                wait_timeout=wait_timeout,
                poll_sec=1.0,
            )
        except GPUPoolError as exc:
            raise HTTPException(502, str(exc)) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"scheduler unreachable: {exc}") from exc

        if job.get("status") == "failed":
            err = job.get("error") or "llm_chat job failed"
            raise HTTPException(503, err)

        result = job.get("result") or {}
        completion = result.get("completion") if isinstance(result, dict) else None
        if isinstance(completion, dict) and completion.get("choices"):
            out = dict(completion)
            out["model"] = model
            out["id"] = out.get("id") or f"chatcmpl-pool-{uuid.uuid4().hex[:12]}"
            out["object"] = "chat.completion"
            out["gpu_pool_job_id"] = job.get("id")
            return JSONResponse(out)

        text = ""
        if isinstance(result, dict):
            text = str(result.get("message") or "")
        if not text:
            text = (
                f"llm_chat job {job.get('id')} finished with status={job.get('status')} "
                "but no completion payload. Is Ollama running on a contributor worker?"
            )
        created = int(time.time())
        return JSONResponse(
            {
                "id": f"chatcmpl-pool-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "gpu_pool_job_id": job.get("id"),
            }
        )

    return app


def _model_catalog(scheduler_url: str) -> list[str]:
    models = [DEFAULT_MODEL_ID, "gpu-pool/auto"]
    env_models = (os.environ.get("GPU_SWARM_LOCAL_MODELS") or "").strip()
    if env_models:
        for part in env_models.split(","):
            mid = part.strip()
            if mid and mid not in models:
                models.append(mid)
    try:
        st = GPUPool(scheduler_url=scheduler_url, timeout=4.0).status()
        for w in st.get("workers") or []:
            if not isinstance(w, dict):
                continue
            for mid in w.get("llm_models") or []:
                mid_s = str(mid).strip()
                if mid_s and mid_s not in models:
                    models.append(mid_s)
    except Exception:  # noqa: BLE001
        pass
    return models


def run_local_endpoint(
    *,
    host: str | None = None,
    port: int | None = None,
    scheduler_url: str | None = None,
) -> int:
    host = host or (os.environ.get("GPU_SWARM_LOCAL_ENDPOINT_HOST") or DEFAULT_HOST).strip() or DEFAULT_HOST
    listen_port = pick_listen_port(host, port)
    base = _scheduler_url(scheduler_url)
    openai_base = f"http://{host}:{listen_port}/v1"
    print(f"[local-endpoint] bind={host}:{listen_port}", flush=True)
    print(f"[local-endpoint] scheduler={base}", flush=True)
    print(f"[local-endpoint] OpenAI base URL (paste into apps): {openai_base}", flush=True)
    print(f"[local-endpoint] OPENAI_BASE_URL={openai_base}", flush=True)
    print(
        "[local-endpoint] Honest note: pool GPU via API — not a Windows display adapter. "
        "See LOCAL_MODEL.md",
        flush=True,
    )
    os.environ.setdefault("GPU_SWARM_SCHEDULER_URL", base)
    app = create_app(scheduler_url=base)
    uvicorn.run(app, host=host, port=listen_port, log_level="info")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Start localhost OpenAI-compatible endpoint that forwards chat to GPU Pool",
    )
    p.add_argument("--host", default=None, help=f"Bind host (default {DEFAULT_HOST})")
    p.add_argument("--port", type=int, default=None, help=f"Bind port (default {DEFAULT_PORT})")
    p.add_argument("--scheduler-url", default=None, help="GPU Pool scheduler base URL")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    return run_local_endpoint(host=args.host, port=args.port, scheduler_url=args.scheduler_url)


if __name__ == "__main__":
    raise SystemExit(main())

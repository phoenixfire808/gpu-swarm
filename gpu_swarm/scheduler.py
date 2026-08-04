"""FastAPI scheduler / queue API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from gpu_swarm import ALLOWED_JOB_TYPES, MAX_RESULT_BYTES
from gpu_swarm.config import SchedulerConfig, scheduler_config
from gpu_swarm.db import Store

store: Store | None = None
cfg: SchedulerConfig = scheduler_config()


class WorkerRegister(BaseModel):
    id: str | None = None
    name: str = "worker"
    discord_user: str | None = None
    host: str | None = None
    gpus: list[dict[str, Any]] = Field(default_factory=list)
    free_vram_mb: int | None = None
    total_vram_mb: int | None = None
    max_vram_mb: int = 0
    max_cpu_percent: float = 50.0
    # Host capacity (from worker nvidia-smi + host probe; RAM/SSD are ads, not a DFS)
    cpu_cores: int = 0
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    max_ram_mb: int = 0
    disk_free_mb: int = 0
    disk_total_mb: int = 0
    disk_path: str | None = None
    max_disk_mb: int = 0
    # Portal aliases
    dedicated_ram_mb: int = 0
    dedicated_disk_mb: int = 0
    dedicated_cpu_cores: float = 0.0
    contributor_name: str | None = None


class WorkerHeartbeat(BaseModel):
    gpus: list[dict[str, Any]] | None = None
    free_vram_mb: int | None = None
    total_vram_mb: int | None = None
    status: str = "online"
    cpu_cores: int | None = None
    ram_total_mb: int | None = None
    ram_available_mb: int | None = None
    max_ram_mb: int | None = None
    disk_free_mb: int | None = None
    disk_total_mb: int | None = None
    disk_path: str | None = None
    max_disk_mb: int | None = None
    max_cpu_percent: float | None = None
    dedicated_ram_mb: int | None = None
    dedicated_disk_mb: int | None = None
    dedicated_cpu_cores: float | None = None
    contributor_name: str | None = None


class JobSubmit(BaseModel):
    job_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    require_gpu: bool = False
    min_vram_mb: int = 0
    submitted_by: str | None = None


class LeaseRequest(BaseModel):
    worker_id: str
    free_vram_mb: int = 0
    has_gpu: bool = True
    cpu_cores: int | None = None
    ram_available_mb: int | None = None
    disk_free_mb: int | None = None


class JobComplete(BaseModel):
    worker_id: str
    result: Any = None


class JobFail(BaseModel):
    worker_id: str
    error: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    global store, cfg
    cfg = scheduler_config()
    store = Store(cfg.db_path)
    await store.connect()
    yield
    await store.close()


app = FastAPI(title="gpu-swarm scheduler", version="0.1.0", lifespan=lifespan)


def _store() -> Store:
    if store is None:
        raise HTTPException(503, "store not ready")
    return store


def _normalize_capacity(data: dict[str, Any]) -> dict[str, Any]:
    """Map portal dedicated_* aliases onto scheduler max_* / cpu_cores fields."""
    out = dict(data)
    if not int(out.get("max_ram_mb") or 0) and out.get("dedicated_ram_mb"):
        out["max_ram_mb"] = int(out["dedicated_ram_mb"])
    if not int(out.get("max_disk_mb") or 0) and out.get("dedicated_disk_mb"):
        out["max_disk_mb"] = int(out["dedicated_disk_mb"])
    if not int(out.get("cpu_cores") or 0) and out.get("dedicated_cpu_cores"):
        out["cpu_cores"] = int(float(out["dedicated_cpu_cores"]))
    return out


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/workers/register")
async def workers_register(body: WorkerRegister) -> dict[str, Any]:
    return await _store().register_worker(_normalize_capacity(body.model_dump()))


@app.post("/workers/{worker_id}/heartbeat")
async def workers_heartbeat(worker_id: str, body: WorkerHeartbeat) -> dict[str, Any]:
    raw = _normalize_capacity(body.model_dump())
    row = await _store().heartbeat(worker_id, raw)
    if not row:
        raise HTTPException(404, "unknown worker")
    return row


@app.get("/workers")
async def workers_list() -> list[dict[str, Any]]:
    return await _store().list_workers(cfg.worker_stale_sec)


@app.post("/jobs")
async def jobs_submit(body: JobSubmit) -> dict[str, Any]:
    if body.job_type not in ALLOWED_JOB_TYPES:
        raise HTTPException(
            400,
            f"job_type not allowlisted. Allowed: {sorted(ALLOWED_JOB_TYPES)}",
        )
    require_gpu = body.require_gpu
    if body.job_type == "pytorch_cuda_probe":
        require_gpu = True
    return await _store().submit_job(
        {
            "job_type": body.job_type,
            "payload": body.payload,
            "require_gpu": require_gpu,
            "min_vram_mb": body.min_vram_mb,
            "submitted_by": body.submitted_by,
        }
    )


@app.get("/jobs/{job_id}")
async def jobs_get(job_id: str) -> dict[str, Any]:
    job = await _store().get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


@app.post("/jobs/lease")
async def jobs_lease(body: LeaseRequest) -> dict[str, Any]:
    job = await _store().lease_job(
        body.worker_id,
        {
            "free_vram_mb": body.free_vram_mb,
            "has_gpu": body.has_gpu,
            "cpu_cores": body.cpu_cores,
            "ram_available_mb": body.ram_available_mb,
            "disk_free_mb": body.disk_free_mb,
        },
    )
    if not job:
        return {"job": None}
    return {"job": job}


@app.post("/jobs/{job_id}/complete")
async def jobs_complete(job_id: str, body: JobComplete) -> dict[str, Any]:
    import json

    raw = json.dumps(body.result)
    if len(raw.encode("utf-8")) > MAX_RESULT_BYTES:
        raise HTTPException(400, f"result exceeds {MAX_RESULT_BYTES} bytes")
    job = await _store().complete_job(job_id, body.worker_id, body.result)
    if not job:
        raise HTTPException(404, "job not found or wrong worker")
    return job


@app.post("/jobs/{job_id}/fail")
async def jobs_fail(job_id: str, body: JobFail) -> dict[str, Any]:
    job = await _store().fail_job(job_id, body.worker_id, body.error)
    if not job:
        raise HTTPException(404, "job not found or wrong worker")
    return job


@app.get("/status")
async def status() -> dict[str, Any]:
    summary = await _store().status_summary(cfg.worker_stale_sec)
    summary["capacity_note"] = (
        "v1 contributes compute to JOBS (GPU/CPU). RAM/SSD figures are capacity "
        "advertisements for future job constraints — not a literal distributed filesystem yet."
    )
    return summary


# --- Utilizer API (OpenAI-style path prefix; allowlisted jobs only) ---
# Same semantics as /jobs + /status — cleaner for local-model / coding clients.
# No public auth yet: keep scheduler on Tailscale/LAN only.


class PoolJobSubmit(BaseModel):
    job_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    require_gpu: bool | None = None
    min_vram_mb: int = 0
    submitted_by: str | None = "v1-pool"
    matrix_size: int | None = Field(default=None, ge=64, le=4096)


@app.get("/v1/pool/status")
async def v1_pool_status() -> dict[str, Any]:
    """Utilizer-friendly pool status (wraps /status)."""
    return await status()


@app.get("/v1/pool/jobs/{job_id}")
async def v1_pool_job_get(job_id: str) -> dict[str, Any]:
    """Utilizer-friendly job get (wraps /jobs/{id})."""
    return await jobs_get(job_id)


@app.post("/v1/pool/jobs")
async def v1_pool_jobs_submit(body: PoolJobSubmit) -> dict[str, Any]:
    """Submit allowlisted work from scripts / agents / OpenAI-shim clients.

    Only ``probe`` and ``pytorch_cuda_probe`` are accepted. Arbitrary shell is rejected.
    """
    if body.job_type not in ALLOWED_JOB_TYPES:
        raise HTTPException(
            400,
            f"job_type not allowlisted. Allowed: {sorted(ALLOWED_JOB_TYPES)}",
        )
    payload = dict(body.payload or {})
    if body.job_type == "pytorch_cuda_probe":
        if body.matrix_size is not None:
            payload["matrix_size"] = int(body.matrix_size)
        elif "matrix_size" not in payload and "size" not in payload:
            payload["matrix_size"] = 1024
    require_gpu = body.require_gpu
    if require_gpu is None:
        require_gpu = body.job_type == "pytorch_cuda_probe"
    if body.job_type == "pytorch_cuda_probe":
        require_gpu = True
    return await _store().submit_job(
        {
            "job_type": body.job_type,
            "payload": payload,
            "require_gpu": require_gpu,
            "min_vram_mb": body.min_vram_mb,
            "submitted_by": body.submitted_by or "v1-pool",
        }
    )


@app.post("/v1/chat/completions")
async def v1_chat_completions(body: dict[str, Any]) -> dict[str, Any]:
    """Minimal OpenAI-shaped shim: documents how to route heavy work to the pool.

    This is **not** a full LLM gateway. It returns a structured assistant message
    telling clients to call ``/v1/pool/jobs`` (or the Python SDK) for GPU work.
    If ``tools`` / message content includes an explicit pool probe request, it may
    enqueue an allowlisted probe and include the job id.
    """
    import time as _time
    import uuid as _uuid

    messages = body.get("messages") or []
    text_blob = " ".join(
        str(m.get("content") or "") for m in messages if isinstance(m, dict)
    ).lower()
    want_cuda = any(k in text_blob for k in ("cuda", "pytorch_cuda", "submit_compute", "matmul"))
    want_probe = want_cuda or any(
        k in text_blob for k in ("probe", "gpu pool", "nvidia-smi", "/v1/pool", "submit_probe")
    )

    job: dict[str, Any] | None = None
    if want_probe:
        jt = "pytorch_cuda_probe" if want_cuda else "probe"
        job = await _store().submit_job(
            {
                "job_type": jt,
                "payload": {"matrix_size": 1024} if jt == "pytorch_cuda_probe" else {},
                "require_gpu": jt == "pytorch_cuda_probe",
                "min_vram_mb": 0,
                "submitted_by": "v1-chat-shim",
            }
        )

    guidance = (
        "GPU Pool utilizer shim (MVP). This endpoint is not a full chat model. "
        "Route heavy GPU work via POST /v1/pool/jobs with allowlisted job_type "
        "('probe' or 'pytorch_cuda_probe'), then poll GET /v1/pool/jobs/{id}. "
        "Python: from gpu_swarm.client import GPUPool; pool = GPUPool(); "
        "pool.submit_probe(wait=True) / pool.submit_cuda_probe(wait=True). "
        "Env: GPU_SWARM_SCHEDULER_URL."
    )
    if job:
        content = (
            f"{guidance}\n\nEnqueued allowlisted job {job.get('id')} "
            f"({job.get('job_type')}, status={job.get('status')}). "
            f"Poll GET /v1/pool/jobs/{job.get('id')} or use GPUPool.wait(...)."
        )
    else:
        content = guidance

    created = int(_time.time())
    return {
        "id": f"chatcmpl-pool-{_uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": created,
        "model": body.get("model") or "gpu-pool-utilizer-shim",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "gpu_pool": {
            "scheduler_paths": {
                "status": "/v1/pool/status",
                "submit": "/v1/pool/jobs",
                "job": "/v1/pool/jobs/{job_id}",
            },
            "allowed_job_types": sorted(ALLOWED_JOB_TYPES),
            "job": job,
        },
    }


def run_scheduler(host: str | None = None, port: int | None = None) -> None:
    import uvicorn

    c = scheduler_config()
    uvicorn.run(
        "gpu_swarm.scheduler:app",
        host=host or c.host,
        port=port or c.port,
        reload=False,
        log_level="info",
    )

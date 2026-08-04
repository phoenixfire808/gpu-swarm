"""Python client for utilizing the GPU Pool (submit allowlisted jobs).

Coders / local-model runners plug in like this::

    from gpu_swarm.client import GPUPool

    pool = GPUPool()  # or GPU_SWARM_SCHEDULER_URL
    print(pool.status())
    print(pool.submit_probe(wait=True))
    print(pool.submit_cuda_probe(wait=True))

Env:
  GPU_SWARM_SCHEDULER_URL  default http://100.85.165.84:8766
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

# Mirrored allowlist (avoid circular import with gpu_swarm.__init__)
ALLOWED_JOB_TYPES = frozenset({"probe", "pytorch_cuda_probe", "llm_chat"})

DEFAULT_SCHEDULER_URL = "http://100.85.165.84:8766"
TERMINAL_STATUSES = frozenset({"completed", "failed"})

def _env_scheduler_url(explicit: str | None = None) -> str:
    if explicit:
        return explicit.rstrip("/")
    raw = (os.environ.get("GPU_SWARM_SCHEDULER_URL") or "").strip()
    if raw:
        return raw.rstrip("/")
    return DEFAULT_SCHEDULER_URL


class GPUPoolError(RuntimeError):
    """Raised when the pool rejects a request or a job fails."""

    def __init__(self, message: str, *, job: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.job = job


class GPUPool:
    """Thin HTTP client for the live gpu-swarm scheduler (utilizer side)."""

    def __init__(
        self,
        scheduler_url: str | None = None,
        *,
        timeout: float = 30.0,
        submitted_by: str = "gpu_swarm.client",
    ) -> None:
        self.scheduler_url = _env_scheduler_url(scheduler_url)
        self.timeout = timeout
        self.submitted_by = submitted_by

    # --- core ---

    def status(self) -> dict[str, Any]:
        """GET pool capacity + workers + job counts."""
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.scheduler_url}/status")
            r.raise_for_status()
            return r.json()

    def get_job(self, job_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.scheduler_url}/jobs/{job_id}")
            r.raise_for_status()
            return r.json()

    def submit(
        self,
        job_type: str,
        payload: dict[str, Any] | None = None,
        *,
        require_gpu: bool | None = None,
        min_vram_mb: int = 0,
        submitted_by: str | None = None,
        wait: bool = False,
        wait_timeout: float = 120.0,
        poll_sec: float = 1.0,
    ) -> dict[str, Any]:
        """Submit an allowlisted job. Optionally poll until completed/failed."""
        jt = (job_type or "").strip()
        if jt not in ALLOWED_JOB_TYPES:
            raise GPUPoolError(
                f"job_type not allowlisted: {jt!r}. Allowed: {sorted(ALLOWED_JOB_TYPES)}"
            )
        body_payload = dict(payload or {})
        gpu_required = bool(require_gpu) if require_gpu is not None else (jt == "pytorch_cuda_probe")
        if jt == "pytorch_cuda_probe":
            gpu_required = True
            if "matrix_size" not in body_payload and "size" not in body_payload:
                body_payload["matrix_size"] = 1024
        if jt == "llm_chat":
            if require_gpu is None:
                gpu_required = False
            if "messages" not in body_payload:
                raise GPUPoolError("llm_chat payload requires messages")
            if "max_tokens" not in body_payload:
                body_payload["max_tokens"] = 512
            if "model" not in body_payload:
                body_payload["model"] = "gpu-pool"
        body = {
            "job_type": jt,
            "payload": body_payload,
            "require_gpu": gpu_required,
            "min_vram_mb": int(min_vram_mb or 0),
            "submitted_by": (submitted_by or self.submitted_by or "gpu_swarm.client"),
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(f"{self.scheduler_url}/jobs", json=body)
            if r.status_code >= 400:
                detail = _http_detail(r)
                raise GPUPoolError(detail or f"HTTP {r.status_code}")
            job = r.json()
        if wait:
            return self.wait(job["id"], timeout=wait_timeout, poll_sec=poll_sec)
        return job

    def wait(
        self,
        job_id: str,
        *,
        timeout: float = 120.0,
        poll_sec: float = 1.0,
        raise_on_fail: bool = False,
    ) -> dict[str, Any]:
        """Poll until job completes/fails or timeout."""
        deadline = time.time() + max(1.0, timeout)
        last: dict[str, Any] = {}
        while time.time() < deadline:
            last = self.get_job(job_id)
            st = str(last.get("status") or "")
            if st in TERMINAL_STATUSES:
                if raise_on_fail and st == "failed":
                    raise GPUPoolError(
                        last.get("error") or f"job {job_id} failed",
                        job=last,
                    )
                return last
            time.sleep(max(0.2, poll_sec))
        raise GPUPoolError(f"timeout waiting for job {job_id}", job=last or None)

    # --- convenience ---

    def submit_probe(
        self,
        *,
        wait: bool = False,
        wait_timeout: float = 120.0,
        submitted_by: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Live nvidia-smi inventory via a pool worker."""
        return self.submit(
            "probe",
            payload or {},
            require_gpu=False,
            submitted_by=submitted_by,
            wait=wait,
            wait_timeout=wait_timeout,
        )

    def submit_cuda_probe(
        self,
        *,
        matrix_size: int = 1024,
        device_index: int | None = None,
        min_vram_mb: int = 0,
        wait: bool = False,
        wait_timeout: float = 180.0,
        submitted_by: str | None = None,
    ) -> dict[str, Any]:
        """Real CUDA matmul probe on a pool GPU (PyTorch)."""
        size = max(64, min(int(matrix_size), 4096))
        payload: dict[str, Any] = {"matrix_size": size}
        if device_index is not None:
            payload["device_index"] = int(device_index)
        return self.submit(
            "pytorch_cuda_probe",
            payload,
            require_gpu=True,
            min_vram_mb=min_vram_mb,
            submitted_by=submitted_by,
            wait=wait,
            wait_timeout=wait_timeout,
        )

    def submit_llm_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str = "gpu-pool",
        max_tokens: int = 512,
        temperature: float | None = None,
        wait: bool = True,
        wait_timeout: float = 300.0,
        submitted_by: str | None = None,
    ) -> dict[str, Any]:
        """Allowlisted chat job — runs on a worker with Ollama / OpenAI-compatible runtime."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max(1, min(int(max_tokens), 8192)),
        }
        if temperature is not None:
            payload["temperature"] = float(temperature)
        return self.submit(
            "llm_chat",
            payload,
            require_gpu=False,
            submitted_by=submitted_by,
            wait=wait,
            wait_timeout=wait_timeout,
        )

    def close(self) -> None:
        """No persistent connection; kept for API symmetry / context managers."""

    def __enter__(self) -> "GPUPool":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


# Friendly alias for docs / imports
GPUPoolClient = GPUPool


def _http_detail(r: httpx.Response) -> str:
    try:
        data = r.json()
        if isinstance(data, dict):
            detail = data.get("detail")
            if detail is not None:
                return str(detail)
        return str(data)
    except Exception:  # noqa: BLE001
        return (r.text or "").strip()

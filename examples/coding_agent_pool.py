#!/usr/bin/env python3
"""Offload an allowlisted GPU Pool job and print the JSON result.

Coding agents / local tools can call this instead of inventing shell on workers.

  python examples/coding_agent_pool.py
  python examples/coding_agent_pool.py --job probe
  python examples/coding_agent_pool.py --job pytorch_cuda_probe --matrix-size 1024
  python examples/coding_agent_pool.py --scheduler-url http://127.0.0.1:8766 --wait

Env:
  GPU_SWARM_SCHEDULER_URL  default scheduler base (else http://127.0.0.1:8766)

HTTP: POST /jobs · GET /jobs/{id} · GET /status (same surface as gpu_swarm.client.GPUPool).
SDK twin: examples/use_pool_from_script.py · CLI: python -m gpu_swarm utilize …
Guide: CONNECTING.md

v1 allowlist only: probe, pytorch_cuda_probe — no arbitrary shell / Ollama proxy.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_SCHEDULER = "http://127.0.0.1:8766"
ALLOWED = frozenset({"probe", "pytorch_cuda_probe"})


def _request(method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 30.0) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Cannot reach scheduler at {url}: {exc.reason}\n"
            "Is the pool up? Try: curl http://127.0.0.1:8766/status"
        ) from exc
    if not raw:
        return {}
    return json.loads(raw)


def submit_job(
    base: str,
    job_type: str,
    *,
    matrix_size: int = 1024,
    device_index: int | None = None,
    min_vram_mb: int = 0,
    submitted_by: str = "coding_agent",
) -> dict[str, Any]:
    if job_type not in ALLOWED:
        raise SystemExit(f"job type not allowlisted: {job_type}. Allowed: {sorted(ALLOWED)}")
    payload: dict[str, Any] = {}
    require_gpu = False
    if job_type == "pytorch_cuda_probe":
        payload["matrix_size"] = max(64, min(int(matrix_size), 4096))
        if device_index is not None:
            payload["device_index"] = int(device_index)
        require_gpu = True
    body = {
        "job_type": job_type,
        "payload": payload,
        "require_gpu": require_gpu,
        "min_vram_mb": int(min_vram_mb),
        "submitted_by": submitted_by,
    }
    return _request("POST", f"{base.rstrip('/')}/jobs", body)


def wait_job(base: str, job_id: str, timeout: float) -> dict[str, Any]:
    deadline = time.time() + timeout
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = _request("GET", f"{base.rstrip('/')}/jobs/{job_id}")
        if last.get("status") in ("completed", "failed"):
            return last
        time.sleep(1.0)
    raise SystemExit(f"timeout waiting for job {job_id} after {timeout}s; last={json.dumps(last)}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Submit allowlisted GPU Pool job; print JSON result")
    p.add_argument(
        "--scheduler-url",
        default=os.environ.get("GPU_SWARM_SCHEDULER_URL", DEFAULT_SCHEDULER),
        help=f"Scheduler base URL (default {DEFAULT_SCHEDULER})",
    )
    p.add_argument("--job", choices=sorted(ALLOWED), default="probe", help="Allowlisted job type")
    p.add_argument("--matrix-size", type=int, default=1024, help="For pytorch_cuda_probe")
    p.add_argument("--device-index", type=int, default=None, help="Optional CUDA device index")
    p.add_argument("--min-vram-mb", type=int, default=0)
    p.add_argument("--by", default="coding_agent", help="submitted_by label")
    p.add_argument("--wait", action="store_true", default=True, help="Wait for completion (default)")
    p.add_argument("--no-wait", action="store_true", help="Print queued job JSON and exit")
    p.add_argument("--wait-timeout", type=float, default=120.0)
    p.add_argument("--status-only", action="store_true", help="GET /status and exit")
    args = p.parse_args(argv)

    base = args.scheduler_url.rstrip("/")
    if args.status_only:
        print(json.dumps(_request("GET", f"{base}/status"), indent=2))
        return 0

    job = submit_job(
        base,
        args.job,
        matrix_size=args.matrix_size,
        device_index=args.device_index,
        min_vram_mb=args.min_vram_mb,
        submitted_by=args.by,
    )
    if args.no_wait:
        print(json.dumps(job, indent=2))
        return 0

    final = wait_job(base, job["id"], args.wait_timeout)
    print(json.dumps(final, indent=2))
    return 0 if final.get("status") == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())

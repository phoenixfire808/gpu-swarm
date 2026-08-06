//remove and optmize a code from ai slop//

#!/usr/bin/env python3
"""Submit an allowlisted GPU Pool job and print the JSON result."""

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
ALLOWED = {"probe", "pytorch_cuda_probe"}


def request(method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 30) -> dict[str, Any]:
    headers = {"Accept": "application/json"}

    data = None
    if body:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()

    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, data=data, headers=headers, method=method),
            timeout=timeout,
        ) as resp:
            return json.loads(resp.read() or "{}")

    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read().decode(errors='replace')}") from e

    except urllib.error.URLError as e:
        raise SystemExit(
            f"Cannot reach scheduler: {url}\n"
            f"Reason: {e.reason}\n"
            "Try: curl http://127.0.0.1:8766/status"
        ) from e


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
        raise SystemExit(f"Unknown job: {job_type}")

    payload = {}
    require_gpu = job_type == "pytorch_cuda_probe"

    if require_gpu:
        payload["matrix_size"] = max(64, min(matrix_size, 4096))
        if device_index is not None:
            payload["device_index"] = device_index

    return request(
        "POST",
        f"{base}/jobs",
        {
            "job_type": job_type,
            "payload": payload,
            "require_gpu": require_gpu,
            "min_vram_mb": min_vram_mb,
            "submitted_by": submitted_by,
        },
    )


def wait_for_job(base: str, job_id: str, timeout: float) -> dict[str, Any]:
    end = time.time() + timeout

    while time.time() < end:
        job = request("GET", f"{base}/jobs/{job_id}")

        if job.get("status") in {"completed", "failed"}:
            return job

        time.sleep(1)

    raise SystemExit(f"Timed out waiting for {job_id}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GPU Pool client")

    parser.add_argument(
        "--scheduler-url",
        default=os.getenv("GPU_SWARM_SCHEDULER_URL", DEFAULT_SCHEDULER),
    )
    parser.add_argument("--job", choices=sorted(ALLOWED), default="probe")
    parser.add_argument("--matrix-size", type=int, default=1024)
    parser.add_argument("--device-index", type=int)
    parser.add_argument("--min-vram-mb", type=int, default=0)
    parser.add_argument("--by", default="coding_agent")
    parser.add_argument("--wait-timeout", type=float, default=120)
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument("--no-wait", action="store_true")

    args = parser.parse_args(argv)

    base = args.scheduler_url.rstrip("/")

    if args.status_only:
        print(json.dumps(request("GET", f"{base}/status"), indent=2))
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

    result = wait_for_job(base, job["id"], args.wait_timeout)
    print(json.dumps(result, indent=2))

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3
"""Utilize the GPU Pool via the Python SDK (aligned with coding_agent_pool.py).

Uses the same scheduler surface:
  GET  /status
  POST /jobs
  GET  /jobs/{id}

  cd C:\\Users\\Drew\\Projects\\gpu-swarm
  set GPU_SWARM_SCHEDULER_URL=http://127.0.0.1:8766
  python examples/use_pool_from_script.py
  python examples/use_pool_from_script.py --cuda

See CONNECTING.md and examples/coding_agent_pool.py (stdlib twin).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo without install
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gpu_swarm.client import GPUPool  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="GPUPool SDK example (probe / cuda)")
    p.add_argument("--scheduler-url", default=None, help="Override GPU_SWARM_SCHEDULER_URL")
    p.add_argument("--cuda", action="store_true", help="Run pytorch_cuda_probe instead of probe")
    p.add_argument("--matrix-size", type=int, default=1024)
    p.add_argument("--no-wait", action="store_true")
    args = p.parse_args(argv)

    pool = GPUPool(scheduler_url=args.scheduler_url, submitted_by="use_pool_from_script")
    print(json.dumps({"scheduler_url": pool.scheduler_url, **{k: pool.status().get(k) for k in (
        "workers_online", "free_vram_mb", "jobs"
    )}}, indent=2))

    wait = not args.no_wait
    if args.cuda:
        job = pool.submit_cuda_probe(matrix_size=args.matrix_size, wait=wait)
    else:
        job = pool.submit_probe(wait=wait)
    print(json.dumps(job, indent=2))
    return 0 if (not wait or job.get("status") == "completed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Hermes-friendly CLI for gpu-swarm."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

import httpx

from gpu_swarm import ALLOWED_JOB_TYPES
from gpu_swarm.config import ROOT, scheduler_config, worker_config


def _base_url(url: str | None = None) -> str:
    if url:
        return url.rstrip("/")
    c = scheduler_config()
    host = "127.0.0.1" if c.host == "0.0.0.0" else c.host
    return f"http://{host}:{c.port}"


def cmd_scheduler(args: argparse.Namespace) -> int:
    from gpu_swarm.scheduler import run_scheduler

    host = args.host
    port = args.port
    print(f"[scheduler] starting on {host or scheduler_config().host}:{port or scheduler_config().port}")
    print(f"[scheduler] db={scheduler_config().db_path}")
    run_scheduler(host=host, port=port)
    return 0


def cmd_worker(args: argparse.Namespace) -> int:
    from gpu_swarm.worker import run_worker

    return run_worker(args)


def cmd_bot(args: argparse.Namespace) -> int:
    from gpu_swarm.bot import bot_help_check, run_bot

    if args.check:
        return bot_help_check()
    return run_bot()


def cmd_submit(args: argparse.Namespace) -> int:
    job_type = args.job_type
    if job_type not in ALLOWED_JOB_TYPES:
        print(f"Unknown/forbidden job type: {job_type}. Allowed: {sorted(ALLOWED_JOB_TYPES)}")
        return 2
    payload: dict[str, Any] = {}
    if job_type == "pytorch_cuda_probe":
        payload["matrix_size"] = args.matrix_size
        if args.device_index is not None:
            payload["device_index"] = args.device_index
    body = {
        "job_type": job_type,
        "payload": payload,
        "require_gpu": job_type == "pytorch_cuda_probe",
        "min_vram_mb": args.min_vram_mb,
        "submitted_by": args.by or "cli",
    }
    base = _base_url(args.scheduler_url)
    with httpx.Client(timeout=30.0) as client:
        r = client.post(f"{base}/jobs", json=body)
        r.raise_for_status()
        job = r.json()
    print(json.dumps(job, indent=2))
    if args.wait:
        return _wait_job(base, job["id"], args.wait_timeout)
    return 0


def _wait_job(base: str, job_id: str, timeout: float) -> int:
    deadline = time.time() + timeout
    with httpx.Client(timeout=30.0) as client:
        while time.time() < deadline:
            r = client.get(f"{base}/jobs/{job_id}")
            r.raise_for_status()
            job = r.json()
            st = job["status"]
            if st in ("completed", "failed"):
                print(json.dumps(job, indent=2))
                return 0 if st == "completed" else 1
            time.sleep(1.0)
    print(f"timeout waiting for job {job_id}", file=sys.stderr)
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    base = _base_url(args.scheduler_url)
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{base}/status")
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))
    return 0


def cmd_job(args: argparse.Namespace) -> int:
    base = _base_url(args.scheduler_url)
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{base}/jobs/{args.job_id}")
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))
    return 0


def cmd_portal(args: argparse.Namespace) -> int:
    from gpu_swarm.config import portal_config
    from gpu_swarm.portal import run_portal

    c = portal_config()
    host = args.host or c.host
    port = args.port or c.port
    print(f"[portal] starting on http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}/portal")
    print(f"[portal] scheduler={c.scheduler_url}")
    print(f"[portal] db={c.db_path}")
    if not c.pool_password and not c.invite_codes:
        print("[portal] WARNING: no GPU_SWARM_POOL_PASSWORD / INVITE_CODES — open-dev login enabled")
    run_portal(host=host, port=port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gpu_swarm",
        description="Private Discord GPU/CPU co-op swarm (scheduler, worker, bot, CLI)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scheduler", help="Start the central scheduler/API")
    s.add_argument("--host", default=None, help="Bind host (default 127.0.0.1; use 0.0.0.0 for LAN/Tailscale)")
    s.add_argument("--port", type=int, default=None)
    s.set_defaults(func=cmd_scheduler)

    w = sub.add_parser("worker", help="Start a contribution worker")
    w.add_argument("--name", default=None)
    w.add_argument("--scheduler-url", default=None)
    w.add_argument("--max-vram-mb", type=int, default=None)
    w.add_argument("--max-ram-mb", type=int, default=None)
    w.add_argument("--max-disk-mb", type=int, default=None)
    w.add_argument("--max-cpu-percent", type=float, default=None)
    w.add_argument("--discord-user", default=None)
    w.add_argument("--start-token", default=None, help="Portal start token")
    w.add_argument("--portal-url", default=None, help="Portal base URL for token redeem")
    w.set_defaults(func=cmd_worker)

    portal = sub.add_parser("portal", help="Start web contributor portal (browser UI)")
    portal.add_argument("--host", default=None, help="Bind host (default 127.0.0.1; 0.0.0.0 for LAN)")
    portal.add_argument("--port", type=int, default=None, help="Default 8767")
    portal.set_defaults(func=cmd_portal)

    b = sub.add_parser("bot", help="Start Discord bot (needs DISCORD_BOT_TOKEN)")
    b.add_argument("--check", action="store_true", help="Verify bot wiring without connecting")
    b.set_defaults(func=cmd_bot)

    sub_submit = sub.add_parser("submit", help="Submit a job")
    sub_submit.add_argument("job_type", choices=sorted(ALLOWED_JOB_TYPES))
    sub_submit.add_argument("--scheduler-url", default=None)
    sub_submit.add_argument("--matrix-size", type=int, default=1024)
    sub_submit.add_argument("--device-index", type=int, default=None)
    sub_submit.add_argument("--min-vram-mb", type=int, default=0)
    sub_submit.add_argument("--by", default="cli")
    sub_submit.add_argument("--wait", action="store_true")
    sub_submit.add_argument("--wait-timeout", type=float, default=120.0)
    sub_submit.set_defaults(func=cmd_submit)

    st = sub.add_parser("status", help="Pool status summary")
    st.add_argument("--scheduler-url", default=None)
    st.set_defaults(func=cmd_status)

    j = sub.add_parser("job", help="Get a job by id")
    j.add_argument("job_id")
    j.add_argument("--scheduler-url", default=None)
    j.set_defaults(func=cmd_job)

    a = sub.add_parser("app", help="Launch GPU Pool desktop joiner (customtkinter)")
    a.set_defaults(func=cmd_app)

    return p


def cmd_app(_args: argparse.Namespace) -> int:
    from gpu_swarm.app import main as app_main

    return int(app_main())


def main(argv: list[str] | None = None) -> int:
    # Ensure project root is importable when run as python -m
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

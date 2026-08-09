"""Hermes-friendly CLI for gpu-swarm."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from gpu_swarm import ALLOWED_JOB_TYPES
from gpu_swarm.client import DEFAULT_SCHEDULER_URL, GPUPool, GPUPoolError
from gpu_swarm.config import ROOT, parse_gpu_ids, scheduler_config


def _gpu_ids_arg(raw: str) -> tuple[int, ...]:
    parsed = parse_gpu_ids(raw)
    if parsed is None or parsed == ():
        raise argparse.ArgumentTypeError("GPU IDs must be a comma-separated list of non-negative physical indexes")
    return parsed


def _base_url(url: str | None = None) -> str:
    """Resolve scheduler URL: flag → GPU_SWARM_SCHEDULER_URL → local scheduler cfg → Tailscale default."""
    if url:
        return url.rstrip("/")
    env = (os.environ.get("GPU_SWARM_SCHEDULER_URL") or "").strip()
    if env:
        return env.rstrip("/")
    c = scheduler_config()
    # Prefer explicit local bind when running on the host; else utilizer Tailscale default.
    if c.host in ("127.0.0.1", "localhost"):
        return f"http://127.0.0.1:{c.port}"
    if c.host == "0.0.0.0":
        # LAN scheduler often means local utilizer should hit loopback first.
        return f"http://127.0.0.1:{c.port}"
    return DEFAULT_SCHEDULER_URL


def _pool(args: argparse.Namespace) -> GPUPool:
    url = getattr(args, "scheduler_url", None)
    by = getattr(args, "by", None) or "cli"
    return GPUPool(scheduler_url=_base_url(url), submitted_by=by)


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
    """Submit via scheduler POST /jobs (same path as examples/coding_agent_pool.py)."""
    job_type = args.job_type
    if job_type not in ALLOWED_JOB_TYPES:
        print(f"Unknown/forbidden job type: {job_type}. Allowed: {sorted(ALLOWED_JOB_TYPES)}")
        return 2
    pool = _pool(args)
    payload: dict[str, Any] = {}
    if job_type == "pytorch_cuda_probe":
        payload["matrix_size"] = args.matrix_size
        if args.device_index is not None:
            payload["device_index"] = args.device_index
    try:
        job = pool.submit(
            job_type,
            payload,
            min_vram_mb=args.min_vram_mb,
            wait=bool(args.wait),
            wait_timeout=float(args.wait_timeout),
        )
    except GPUPoolError as exc:
        print(str(exc), file=sys.stderr)
        if exc.job:
            print(json.dumps(exc.job, indent=2))
        return 1
    print(json.dumps(job, indent=2))
    if args.wait:
        return 0 if job.get("status") == "completed" else 1
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """GET /status — same as coding_agent_pool.py --status-only."""
    try:
        print(json.dumps(_pool(args).status(), indent=2))
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def cmd_job(args: argparse.Namespace) -> int:
    try:
        print(json.dumps(_pool(args).get_job(args.job_id), indent=2))
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def cmd_utilize(args: argparse.Namespace) -> int:
    """Coder-facing utilize helpers (status / probe / cuda) via GPUPool → /status + /jobs."""
    pool = _pool(args)
    action = args.utilize_action
    try:
        if action == "status":
            print(json.dumps(pool.status(), indent=2))
            return 0
        if action == "probe":
            job = pool.submit_probe(
                wait=bool(args.wait),
                wait_timeout=float(args.wait_timeout),
                submitted_by=args.by,
            )
            print(json.dumps(job, indent=2))
            if args.wait:
                return 0 if job.get("status") == "completed" else 1
            return 0
        if action == "cuda":
            job = pool.submit_cuda_probe(
                matrix_size=args.matrix_size,
                device_index=args.device_index,
                min_vram_mb=args.min_vram_mb,
                wait=bool(args.wait),
                wait_timeout=float(args.wait_timeout),
                submitted_by=args.by,
            )
            print(json.dumps(job, indent=2))
            if args.wait:
                return 0 if job.get("status") == "completed" else 1
            return 0
    except GPUPoolError as exc:
        print(str(exc), file=sys.stderr)
        if exc.job:
            print(json.dumps(exc.job, indent=2))
        return 1
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1
    print(f"unknown utilize action: {action}", file=sys.stderr)
    return 2


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
        description=(
            "Private Discord GPU/CPU co-op swarm.\n"
            "Coders: use `utilize` or see CONNECTING.md + examples/coding_agent_pool.py"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
    w.add_argument(
        "--selected-gpu-ids",
        type=_gpu_ids_arg,
        default=None,
        help="Comma-separated physical nvidia-smi indexes to advertise (default: all)",
    )
    w.add_argument(
        "--host-protect",
        dest="host_protect",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Desktop GPU safety ceiling (default ON). --no-host-protect disables.",
    )
    w.add_argument("--discord-user", default=None)
    w.add_argument("--start-token", default=None, help="Portal start token")
    w.add_argument("--portal-url", default=None, help="Portal base URL for token redeem")
    w.set_defaults(func=cmd_worker)

    portal = sub.add_parser("portal", help="Start web contributor portal (browser UI)")
    portal.add_argument("--host", default=None, help="Bind host (default 0.0.0.0 for LAN/Tailscale; 127.0.0.1 local-only)")
    portal.add_argument("--port", type=int, default=None, help="Default 8767")
    portal.set_defaults(func=cmd_portal)

    b = sub.add_parser("bot", help="Start Discord bot (needs DISCORD_BOT_TOKEN)")
    b.add_argument("--check", action="store_true", help="Verify bot wiring without connecting")
    b.set_defaults(func=cmd_bot)

    sub_submit = sub.add_parser("submit", help="Submit a job (POST /jobs)")
    sub_submit.add_argument("job_type", choices=sorted(ALLOWED_JOB_TYPES))
    sub_submit.add_argument("--scheduler-url", default=None)
    sub_submit.add_argument("--matrix-size", type=int, default=1024)
    sub_submit.add_argument("--device-index", type=int, default=None)
    sub_submit.add_argument("--min-vram-mb", type=int, default=0)
    sub_submit.add_argument("--by", default="cli")
    sub_submit.add_argument("--wait", action="store_true")
    sub_submit.add_argument("--wait-timeout", type=float, default=120.0)
    sub_submit.set_defaults(func=cmd_submit)

    st = sub.add_parser("status", help="Pool status summary (GET /status)")
    st.add_argument("--scheduler-url", default=None)
    st.set_defaults(func=cmd_status)

    j = sub.add_parser("job", help="Get a job by id (GET /jobs/{id})")
    j.add_argument("job_id")
    j.add_argument("--scheduler-url", default=None)
    j.set_defaults(func=cmd_job)

    u = sub.add_parser(
        "utilize",
        help="Coder helpers: status / probe / cuda (uses GPUPool → scheduler /status + /jobs)",
        description=(
            "Utilize the GPU Pool from a coding session or local model runner.\n\n"
            "Examples:\n"
            "  python -m gpu_swarm utilize status\n"
            "  python -m gpu_swarm utilize probe --wait\n"
            "  python -m gpu_swarm utilize cuda --wait\n\n"
            "Same HTTP surface as examples/coding_agent_pool.py (POST /jobs, GET /status).\n"
            "See CONNECTING.md. Env: GPU_SWARM_SCHEDULER_URL "
            f"(SDK default {DEFAULT_SCHEDULER_URL})."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    u_sub = u.add_subparsers(dest="utilize_action", required=True)

    u_st = u_sub.add_parser("status", help="GET /status — workers, VRAM, job counts")
    u_st.add_argument("--scheduler-url", default=None)
    u_st.add_argument("--by", default="cli-utilize", help=argparse.SUPPRESS)
    u_st.set_defaults(func=cmd_utilize)

    u_pr = u_sub.add_parser("probe", help="Submit allowlisted probe job (nvidia-smi inventory)")
    u_pr.add_argument("--scheduler-url", default=None)
    u_pr.add_argument("--wait", action="store_true", help="Poll until completed/failed")
    u_pr.add_argument("--wait-timeout", type=float, default=120.0)
    u_pr.add_argument("--by", default="cli-utilize")
    u_pr.set_defaults(func=cmd_utilize)

    u_cu = u_sub.add_parser("cuda", help="Submit pytorch_cuda_probe (real CUDA matmul)")
    u_cu.add_argument("--scheduler-url", default=None)
    u_cu.add_argument("--matrix-size", type=int, default=1024)
    u_cu.add_argument("--device-index", type=int, default=None)
    u_cu.add_argument("--min-vram-mb", type=int, default=0)
    u_cu.add_argument("--wait", action="store_true", help="Poll until completed/failed")
    u_cu.add_argument("--wait-timeout", type=float, default=180.0)
    u_cu.add_argument("--by", default="cli-utilize")
    u_cu.set_defaults(func=cmd_utilize)

    a = sub.add_parser("app", help="Launch GPU Pool desktop joiner (customtkinter)")
    a.set_defaults(func=cmd_app)

    le = sub.add_parser(
        "local-endpoint",
        help="Start localhost OpenAI-compatible endpoint (pool as a local AI API)",
        description=(
            "Bind 127.0.0.1 (default :8080) and expose OpenAI-compatible /v1/* that "
            "forwards chat to the GPU Pool scheduler. Not a physical GPU device — "
            "see LOCAL_MODEL.md."
        ),
    )
    le.add_argument("--host", default=None, help="Bind host (default 127.0.0.1)")
    le.add_argument("--port", type=int, default=None, help="Bind port (default 8080; alt 11434)")
    le.add_argument("--scheduler-url", default=None, help="GPU Pool scheduler base URL")
    le.set_defaults(func=cmd_local_endpoint)

    return p


def cmd_app(_args: argparse.Namespace) -> int:
    from gpu_swarm.app import main as app_main

    return int(app_main())


def cmd_local_endpoint(args: argparse.Namespace) -> int:
    from gpu_swarm.local_endpoint import run_local_endpoint

    return int(
        run_local_endpoint(
            host=args.host,
            port=args.port,
            scheduler_url=args.scheduler_url,
        )
    )


def main(argv: list[str] | None = None) -> int:
    # Ensure project root is importable when run as python -m
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

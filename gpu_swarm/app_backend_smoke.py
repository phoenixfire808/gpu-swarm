"""
CLI smoke test for desktop app backend.

  python -m gpu_swarm.app_backend_smoke
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict


def main() -> int:
    # Ensure project root importable
    from gpu_swarm.config import ROOT

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from gpu_swarm import app_backend as be

    print("=== gpu_swarm.app_backend smoke ===")
    print(f"root={ROOT}")

    nvidia = be.check_nvidia()
    print(f"nvidia: {json.dumps(nvidia)}")

    gpus = be.get_gpus()
    print(f"get_gpus ({len(gpus)}):")
    for g in gpus:
        print(
            f"  [{g.get('index')}] {g.get('name')} "
            f"free={g.get('memory_free_mb')} / total={g.get('memory_total_mb')} MiB"
        )
    if not gpus:
        print("ERROR: no GPUs detected (expected real nvidia-smi inventory)")
        return 1

    cfg = be.save_config(
        {
            "scheduler_url": "http://127.0.0.1:8766",
            "worker_name": "Joiner-Smoke",
            "max_vram_mb": 1024,
            "max_cpu_percent": 25.0,
            "discord_user": "smoke-test",
        }
    )
    print(f"save_config: {json.dumps(asdict(cfg), indent=2)}")

    # Confirm Discord token untouched
    env_path = ROOT / ".env"
    token_before = None
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("DISCORD_BOT_TOKEN="):
                token_before = line
                break

    test = be.test_scheduler()
    print(
        f"test_scheduler: ok={test.get('ok')} url={test.get('url')} "
        f"ts={test.get('tailscale_ipv4')} attempts={len(test.get('attempts') or [])}"
    )
    if not test.get("ok"):
        print(f"ERROR: scheduler /status failed: {test.get('error')}")
        return 2
    data = test.get("data") or {}
    print(
        f"  pool workers_online={data.get('workers_online')} "
        f"free_vram={data.get('free_vram_mb')} jobs={data.get('jobs')}"
    )

    if env_path.is_file() and token_before is not None:
        token_after = None
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("DISCORD_BOT_TOKEN="):
                token_after = line
                break
        if token_before != token_after:
            print("ERROR: DISCORD_BOT_TOKEN was modified — abort")
            return 3
        print("DISCORD_BOT_TOKEN: unchanged (ok)")

    status_before = be.get_status()
    print(
        f"get_status (before start): running={status_before['worker']['running']} "
        f"sched_ok={status_before['scheduler']['ok']}"
    )

    # Only start briefly if no app-managed worker is already up
    started = False
    if be.is_worker_running():
        print("start_worker: skipped — joiner worker already running")
        start = {"ok": True, "message": "already running", "pid": None}
    else:
        start = be.start_worker(cfg)
        print(f"start_worker: {json.dumps({k: start.get(k) for k in ('ok', 'message', 'pid', 'log')})}")
        if not start.get("ok"):
            print(f"ERROR: start_worker failed: {start.get('message')}")
            return 4
        started = True
        # Wait for register/heartbeat
        time.sleep(3.0)

    status = be.get_status()
    print(
        f"get_status: running={status['worker']['running']} "
        f"connected={status['worker']['connected']} "
        f"pid={status['worker']['pid']} "
        f"detail={status['worker']['detail']}"
    )

    if started:
        stop = be.stop_worker()
        print(f"stop_worker: {json.dumps(stop)}")
        time.sleep(0.5)
        if be.is_worker_running():
            print("ERROR: worker still running after stop")
            return 5

    # Final scheduler health — host scheduler must still be up
    final = be.fetch_scheduler_status("http://127.0.0.1:8766")
    if not final.get("ok"):
        print(f"ERROR: scheduler unreachable after smoke: {final.get('error')}")
        return 6
    print("scheduler still healthy on :8766")
    print("=== smoke OK ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

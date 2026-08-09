"""Worker: advertise GPUs + host resources, heartbeat, lease + run allowlisted jobs."""

from __future__ import annotations

import argparse
import json
import platform
import signal
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from gpu_swarm import MAX_RESULT_BYTES
from gpu_swarm.availability_schedule import AvailabilityConfig, is_available, status_dict
from gpu_swarm.config import WorkerConfig, worker_config
from gpu_swarm.gpu import inventory_summary
from gpu_swarm.host import query_host
from gpu_swarm.host_protect import (
    apply_offer_caps,
    evaluate_admission,
    load_host_protect,
)
from gpu_swarm.jobs import execute_job
from gpu_swarm.llm_runtime import detect_llm_runtime
from gpu_swarm.paths import ROOT
from gpu_swarm.service_lifecycle import docker_guard

DEFAULT_STATE_FILE = ROOT / "data" / "worker_id.txt"


def _worker_id_path() -> Path:
    import os

    override = os.environ.get("GPU_SWARM_WORKER_ID_FILE", "").strip()
    if override:
        return Path(override)
    return DEFAULT_STATE_FILE


class Worker:
    def __init__(self, cfg: WorkerConfig) -> None:
        self.cfg = cfg
        self.worker_id = self._load_or_create_id()
        self._stop = False
        self._client = httpx.Client(base_url=cfg.scheduler_url.rstrip("/"), timeout=30.0)
        self._host_protect = load_host_protect(enabled_override=bool(cfg.host_protect))
        self._last_protect_log = 0.0
        self._last_schedule_log = 0.0
        self._availability = AvailabilityConfig(
            mode=str(getattr(cfg, "availability_mode", "always") or "always"),
            daily_start=str(getattr(cfg, "availability_daily_start", "22:00") or "22:00"),
            daily_end=str(getattr(cfg, "availability_daily_end", "08:00") or "08:00"),
            until_ts=float(getattr(cfg, "availability_until", 0) or 0),
        ).normalized()

    def _load_or_create_id(self) -> str:
        state_file = _worker_id_path()
        state_file.parent.mkdir(parents=True, exist_ok=True)
        if state_file.exists():
            existing = state_file.read_text(encoding="utf-8").strip()
            if existing:
                return existing
        wid = str(uuid.uuid4())
        state_file.write_text(wid, encoding="utf-8")
        return wid

    def stop(self, *_args: Any) -> None:
        self._stop = True
        print("\n[worker] stop requested — finishing current cycle…", flush=True)

    def _reload_availability(self) -> None:
        """Re-read joiner_settings.json so schedule edits apply without restart."""
        try:
            from gpu_swarm.availability_schedule import settings_to_config
            from gpu_swarm.joiner_settings import load_settings

            self._availability = settings_to_config(load_settings())
        except Exception:  # noqa: BLE001
            pass

    def _caps(self) -> dict[str, Any]:
        """
        Advertised capacity after soft caps.

        Stable field names for portal / desktop / scheduler:
          gpus, free_vram_mb, total_vram_mb, has_gpu, max_vram_mb,
          cpu_cores, max_cpu_percent,
          ram_total_mb, ram_available_mb, max_ram_mb,
          disk_free_mb, disk_total_mb, disk_path, max_disk_mb,
          dedicated_ram_mb, dedicated_disk_mb, dedicated_cpu_cores, contributor_name
        """
        self._reload_availability()
        inv = inventory_summary(self.cfg.selected_gpu_ids)
        host = query_host()

        # Soft caps + durable host-protect ceiling (desktop headroom).
        offered = apply_offer_caps(
            total_vram_mb=int(inv["total_vram_mb"] or 0),
            free_vram_mb=int(inv["free_vram_mb"] or 0),
            max_vram_mb=int(self.cfg.max_vram_mb or 0),
            max_cpu_percent=float(self.cfg.max_cpu_percent or 50.0),
            cfg=self._host_protect,
        )
        free_vram = int(offered["free_vram_mb"])
        max_vram = int(offered["max_vram_mb"])
        max_cpu = float(offered["max_cpu_percent"])

        ram_available = host["ram_available_mb"]
        if self.cfg.max_ram_mb > 0:
            ram_available = min(ram_available, self.cfg.max_ram_mb)

        disk_free = host["disk_free_mb"]
        if self.cfg.max_disk_mb > 0:
            disk_free = min(disk_free, self.cfg.max_disk_mb)

        # Portal/desktop dedication ads (aliases of soft caps)
        dedicated_ram = int(self.cfg.max_ram_mb or 0)
        dedicated_disk = int(self.cfg.max_disk_mb or 0)
        dedicated_cpu = float(self.cfg.dedicated_cpu_cores or 0.0)
        if dedicated_cpu <= 0 and host["cpu_cores"] > 0 and max_cpu > 0:
            dedicated_cpu = round(host["cpu_cores"] * (max_cpu / 100.0), 2)

        gpu_available = bool(inv.get("gpu_available", inv["gpu_count"] > 0))
        admission = evaluate_admission(
            inv["gpus"],
            self._host_protect,
            vram_ceiling_mb=int(offered.get("vram_ceiling_mb") or 0),
        )
        llm = detect_llm_runtime(timeout=1.0)
        docker_ok, docker_detail = docker_guard(timeout=0.8)
        if not docker_ok:
            self._stop = True
            print(f"[worker] Docker/Ollama outage latched; stopping worker: {docker_detail}", flush=True)
            llm = {"ready": False, "error": docker_detail, "mounts": []}
        llm_mounts = list(llm.get("mounts") or [])[:64]
        sched = status_dict(self._availability)
        return {
            "gpus": inv["gpus"],
            "free_vram_mb": free_vram,
            "total_vram_mb": inv["total_vram_mb"],
            "has_gpu": gpu_available,
            "gpu_available": gpu_available,
            "mode": inv.get("mode") or ("gpu" if gpu_available else "cpu-only"),
            "max_vram_mb": max_vram,
            "cpu_cores": host["cpu_cores"],
            "max_cpu_percent": max_cpu,
            "ram_total_mb": host["ram_total_mb"],
            "ram_available_mb": ram_available,
            "max_ram_mb": self.cfg.max_ram_mb,
            "disk_free_mb": disk_free,
            "disk_total_mb": host["disk_total_mb"],
            "disk_path": host["disk_path"],
            "max_disk_mb": self.cfg.max_disk_mb,
            "dedicated_ram_mb": dedicated_ram,
            "dedicated_disk_mb": dedicated_disk,
            "dedicated_cpu_cores": dedicated_cpu,
            "contributor_name": self.cfg.contributor_name or self.cfg.discord_user or None,
            "llm_ready": bool(llm.get("ready")),
            "llm_kind": llm.get("kind"),
            "llm_models": [str(item.get("model")) for item in llm_mounts if item.get("model")],
            "llm_runtimes": llm_mounts,
            "host_protect": offered.get("host_protect") or self._host_protect.summary(),
            "host_protect_admit": bool(admission.admit),
            "host_protect_reason": admission.reason,
            "vram_ceiling_mb": int(offered.get("vram_ceiling_mb") or 0),
            "availability": sched,
            "schedule_admit": bool(sched.get("available")),
            "schedule_label": sched.get("label") or "",
        }

    def register(self) -> dict[str, Any]:
        caps = self._caps()
        body = {
            "id": self.worker_id,
            "name": self.cfg.worker_name,
            "discord_user": self.cfg.discord_user or None,
            "host": platform.node(),
            "gpus": caps["gpus"],
            "free_vram_mb": caps["free_vram_mb"],
            "total_vram_mb": caps["total_vram_mb"],
            "max_vram_mb": caps["max_vram_mb"],
            "max_cpu_percent": caps["max_cpu_percent"],
            "cpu_cores": caps["cpu_cores"],
            "ram_total_mb": caps["ram_total_mb"],
            "ram_available_mb": caps["ram_available_mb"],
            "max_ram_mb": caps["max_ram_mb"],
            "disk_free_mb": caps["disk_free_mb"],
            "disk_total_mb": caps["disk_total_mb"],
            "disk_path": caps["disk_path"],
            "max_disk_mb": caps["max_disk_mb"],
            "dedicated_ram_mb": caps["dedicated_ram_mb"],
            "dedicated_disk_mb": caps["dedicated_disk_mb"],
            "dedicated_cpu_cores": caps["dedicated_cpu_cores"],
            "contributor_name": caps["contributor_name"],
            "llm_ready": bool(caps.get("llm_ready")),
            "llm_models": list(caps.get("llm_models") or []),
            "llm_runtimes": list(caps.get("llm_runtimes") or []),
        }
        r = self._client.post("/workers/register", json=body)
        r.raise_for_status()
        return r.json()

    def heartbeat(self, status: str = "online") -> None:
        caps = self._caps()
        sched = caps.get("availability") or {}
        if not sched.get("available") and status == "online":
            status = "paused_schedule"
        r = self._client.post(
            f"/workers/{self.worker_id}/heartbeat",
            json={
                "gpus": caps["gpus"],
                "free_vram_mb": caps["free_vram_mb"],
                "total_vram_mb": caps["total_vram_mb"],
                "cpu_cores": caps["cpu_cores"],
                "max_vram_mb": caps["max_vram_mb"],
                "max_cpu_percent": caps["max_cpu_percent"],
                "ram_total_mb": caps["ram_total_mb"],
                "ram_available_mb": caps["ram_available_mb"],
                "max_ram_mb": caps["max_ram_mb"],
                "disk_free_mb": caps["disk_free_mb"],
                "disk_total_mb": caps["disk_total_mb"],
                "disk_path": caps["disk_path"],
                "max_disk_mb": caps["max_disk_mb"],
                "dedicated_ram_mb": caps["dedicated_ram_mb"],
                "dedicated_disk_mb": caps["dedicated_disk_mb"],
                "dedicated_cpu_cores": caps["dedicated_cpu_cores"],
                "contributor_name": caps["contributor_name"],
                "llm_ready": bool(caps.get("llm_ready")),
                "llm_models": list(caps.get("llm_models") or []),
                "llm_runtimes": list(caps.get("llm_runtimes") or []),
                "status": status,
            },
        )
        r.raise_for_status()

    def lease(self) -> dict[str, Any] | None:
        caps = self._caps()
        if not caps.get("schedule_admit", True):
            now = time.time()
            if now - self._last_schedule_log >= 30.0:
                print(
                    f"[worker] schedule PAUSE lease — {caps.get('schedule_label') or 'outside window'}",
                    flush=True,
                )
                self._last_schedule_log = now
            return None
        # Pause admission when live GPU util / free VRAM would freeze the desktop.
        if not caps.get("host_protect_admit", True):
            now = time.time()
            if now - self._last_protect_log >= 30.0:
                print(
                    f"[worker] host_protect PAUSE lease — {caps.get('host_protect_reason')} "
                    f"(util/free checked via nvidia-smi; desktop headroom)",
                    flush=True,
                )
                self._last_protect_log = now
            return None
        r = self._client.post(
            "/jobs/lease",
            json={
                "worker_id": self.worker_id,
                "free_vram_mb": caps["free_vram_mb"],
                "has_gpu": caps["has_gpu"],
                "cpu_cores": caps["cpu_cores"],
                "ram_available_mb": caps["ram_available_mb"],
                "disk_free_mb": caps["disk_free_mb"],
                "llm_ready": bool(caps.get("llm_ready")),
            },
        )
        r.raise_for_status()
        return r.json().get("job")

    def complete(self, job_id: str, result: Any) -> None:
        raw = json.dumps(result)
        if len(raw.encode("utf-8")) > MAX_RESULT_BYTES:
            result = {
                "truncated": True,
                "note": f"result capped at {MAX_RESULT_BYTES} bytes",
                "preview": raw[: MAX_RESULT_BYTES // 2],
            }
        r = self._client.post(
            f"/jobs/{job_id}/complete",
            json={"worker_id": self.worker_id, "result": result},
        )
        r.raise_for_status()

    def fail(self, job_id: str, error: str) -> None:
        r = self._client.post(
            f"/jobs/{job_id}/fail",
            json={"worker_id": self.worker_id, "error": error},
        )
        r.raise_for_status()

    def run_forever(self) -> None:
        signal.signal(signal.SIGINT, self.stop)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, self.stop)

        print(f"[worker] connecting to {self.cfg.scheduler_url}", flush=True)
        self.register()
        caps = self._caps()
        names = [g["name"] for g in caps["gpus"]]
        print(
            f"[worker] registered id={self.worker_id} name={self.cfg.worker_name}",
            flush=True,
        )
        mode = caps.get("mode") or ("gpu" if caps.get("has_gpu") else "cpu-only")
        print(
            f"[worker] mode={mode} gpu_available={caps.get('gpu_available', caps.get('has_gpu'))}",
            flush=True,
        )
        print(
            f"[worker] GPUs ({len(names)}): {', '.join(names) or 'none (CPU-only OK)'}",
            flush=True,
        )
        print(
            f"[worker] free_vram={caps['free_vram_mb']} MiB / "
            f"total={caps['total_vram_mb']} MiB "
            f"(offer max_vram={caps['max_vram_mb']} "
            f"ceiling={caps.get('vram_ceiling_mb', 0)})",
            flush=True,
        )
        print(
            f"[worker] cpu_cores={caps['cpu_cores']} "
            f"max_cpu_percent={caps['max_cpu_percent']} "
            f"ram_available={caps['ram_available_mb']}/{caps['ram_total_mb']} MiB "
            f"disk_free={caps['disk_free_mb']} MiB  (Ctrl+C to stop)",
            flush=True,
        )
        hp = caps.get("host_protect") or {}
        if hp.get("enabled", True):
            print(
                "[worker] host_protect=ON — desktop safety ceiling "
                f"(VRAM≤{float(hp.get('max_vram_fraction', 0.55)) * 100:.0f}% total, "
                f"pause util≥{hp.get('pause_gpu_util_pct')}%, "
                f"min free {hp.get('min_free_vram_mb')} MiB). "
                "Raise caps ok; disable only if you accept desktop freeze risk "
                "(GPU_SWARM_HOST_PROTECT=0).",
                flush=True,
            )
        else:
            print(
                "[worker] host_protect=OFF — no desktop GPU safety ceiling",
                flush=True,
            )
        sched = caps.get("availability") or {}
        if sched.get("mode") and sched.get("mode") != "always":
            print(f"[worker] availability: {sched.get('label')}", flush=True)
        if caps.get("llm_ready"):
            models = caps.get("llm_models") or []
            preview = ", ".join(models[:5]) if models else "(models unknown)"
            print(
                f"[worker] llm_ready=yes kind={caps.get('llm_kind')} models={preview}",
                flush=True,
            )
        else:
            print(
                "[worker] llm_ready=no — llm_chat jobs skipped until Ollama "
                "(or OpenAI-compatible server) is running locally. See LOCAL_MODEL.md",
                flush=True,
            )
        last_hb = 0.0
        while not self._stop:
            now = time.time()
            try:
                if now - last_hb >= self.cfg.heartbeat_sec:
                    self.heartbeat("online")
                    last_hb = now
                job = self.lease()
                if job:
                    jid = job["id"]
                    jtype = job["job_type"]
                    print(f"[worker] leased {jtype} job={jid}", flush=True)
                    self.heartbeat("busy")
                    last_hb = time.time()
                    try:
                        result = execute_job(jtype, job.get("payload") or {})
                        self.complete(jid, result)
                        print(f"[worker] completed job={jid}", flush=True)
                    except Exception as exc:  # noqa: BLE001 — report to scheduler
                        self.fail(jid, f"{type(exc).__name__}: {exc}")
                        print(f"[worker] failed job={jid}: {exc}", flush=True)
                else:
                    time.sleep(self.cfg.poll_sec)
            except httpx.HTTPError as exc:
                print(f"[worker] network error: {exc}", flush=True)
                time.sleep(max(3.0, self.cfg.poll_sec))
            except Exception as exc:  # noqa: BLE001
                print(f"[worker] loop error: {exc}", flush=True)
                time.sleep(max(3.0, self.cfg.poll_sec))
        try:
            self.heartbeat("stopped")
        except Exception:  # noqa: BLE001
            pass
        self._client.close()
        print("[worker] stopped", flush=True)


def run_worker(args: argparse.Namespace | None = None) -> int:
    cfg = worker_config()
    if args:
        if args.name:
            cfg.worker_name = args.name
        if args.scheduler_url:
            cfg.scheduler_url = args.scheduler_url
        if args.max_vram_mb is not None:
            cfg.max_vram_mb = args.max_vram_mb
        if getattr(args, "max_ram_mb", None) is not None:
            cfg.max_ram_mb = args.max_ram_mb
        if getattr(args, "max_disk_mb", None) is not None:
            cfg.max_disk_mb = args.max_disk_mb
        if getattr(args, "max_cpu_percent", None) is not None:
            cfg.max_cpu_percent = args.max_cpu_percent
        if getattr(args, "host_protect", None) is not None:
            cfg.host_protect = bool(args.host_protect)
        if getattr(args, "availability_mode", None):
            cfg.availability_mode = str(args.availability_mode)
        if getattr(args, "availability_daily_start", None):
            cfg.availability_daily_start = str(args.availability_daily_start)
        if getattr(args, "availability_daily_end", None):
            cfg.availability_daily_end = str(args.availability_daily_end)
        if getattr(args, "availability_until", None) is not None:
            cfg.availability_until = float(args.availability_until)
        if getattr(args, "selected_gpu_ids", None) is not None:
            cfg.selected_gpu_ids = tuple(args.selected_gpu_ids)
        if args.discord_user:
            cfg.discord_user = args.discord_user
    Worker(cfg).run_forever()
    return 0

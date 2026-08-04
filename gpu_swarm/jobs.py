"""Allowlisted job runners — no arbitrary shell from Discord."""

from __future__ import annotations

import platform
import time
from typing import Any, Callable

from gpu_swarm import ALLOWED_JOB_TYPES
from gpu_swarm.gpu import inventory_summary, query_gpus


def run_probe(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Real GPU probe via nvidia-smi — proves network + worker path."""
    inv = inventory_summary()
    return {
        "job_type": "probe",
        "platform": platform.platform(),
        "hostname": platform.node(),
        "timestamp": time.time(),
        "inventory": inv,
        "payload_echo": payload or {},
    }


def run_pytorch_cuda_probe(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Small real CUDA tensor op when torch+CUDA available; else clear CPU fallback note."""
    payload = payload or {}
    size = int(payload.get("matrix_size") or 1024)
    size = max(64, min(size, 4096))  # keep bounded
    device_index = payload.get("device_index")
    started = time.time()
    gpus = query_gpus()

    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "torch not installed on this worker. Install CUDA torch to run pytorch_cuda_probe."
        ) from exc

    cuda_ok = bool(torch.cuda.is_available())
    device_count = torch.cuda.device_count() if cuda_ok else 0
    device_names = []
    if cuda_ok:
        for i in range(device_count):
            device_names.append(torch.cuda.get_device_name(i))

    if not cuda_ok or device_count == 0:
        # Still do a small CPU matmul so the job completes meaningfully.
        a = __import__("torch").randn(size, size)
        b = __import__("torch").randn(size, size)
        c = a @ b
        checksum = float(c.sum().item())
        return {
            "job_type": "pytorch_cuda_probe",
            "cuda_available": False,
            "used_device": "cpu",
            "matrix_size": size,
            "checksum": checksum,
            "elapsed_sec": round(time.time() - started, 4),
            "nvidia_smi_gpus": gpus,
            "note": "CUDA not available to torch; ran CPU matmul",
            "torch_version": getattr(torch, "__version__", "unknown"),
        }

    # Prefer a free-enough GPU; allow caller override.
    idx = int(device_index) if device_index is not None else _pick_gpu(gpus, device_count)
    device = torch.device(f"cuda:{idx}")
    # Warmup + timed matmul
    a = torch.randn(size, size, device=device)
    b = torch.randn(size, size, device=device)
    torch.cuda.synchronize(device)
    t0 = time.time()
    c = a @ b
    torch.cuda.synchronize(device)
    elapsed = time.time() - t0
    checksum = float(c.sum().item())
    mem = torch.cuda.memory_allocated(device)
    return {
        "job_type": "pytorch_cuda_probe",
        "cuda_available": True,
        "used_device": f"cuda:{idx}",
        "device_name": torch.cuda.get_device_name(idx),
        "device_names": device_names,
        "matrix_size": size,
        "checksum": checksum,
        "matmul_sec": round(elapsed, 4),
        "elapsed_sec": round(time.time() - started, 4),
        "memory_allocated_bytes": mem,
        "nvidia_smi_gpus": gpus,
        "torch_version": getattr(torch, "__version__", "unknown"),
    }


def _pick_gpu(gpus: list[dict[str, Any]], device_count: int) -> int:
    """Pick GPU with most free VRAM among torch-visible devices."""
    best_idx = 0
    best_free = -1
    for g in gpus:
        idx = int(g.get("index", 0))
        if idx >= device_count:
            continue
        free = int(g.get("memory_free_mb", 0))
        if free > best_free:
            best_free = free
            best_idx = idx
    return best_idx


RUNNERS: dict[str, Callable[[dict[str, Any] | None], dict[str, Any]]] = {
    "probe": run_probe,
    "pytorch_cuda_probe": run_pytorch_cuda_probe,
}


def execute_job(job_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if job_type not in ALLOWED_JOB_TYPES:
        raise ValueError(f"job type not allowlisted: {job_type}")
    runner = RUNNERS.get(job_type)
    if not runner:
        raise ValueError(f"no runner for job type: {job_type}")
    return runner(payload)

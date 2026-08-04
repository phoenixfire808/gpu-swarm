"""Host GPU safety ceiling — keep the desktop responsive while contributing.

Default ON for gaming/desktop hosts. Clamps how much VRAM/CPU a worker may
offer and pauses job admission when live nvidia-smi util/free-VRAM is too tight.

Tunables (env):
  GPU_SWARM_HOST_PROTECT                 1/0 (default 1)
  GPU_SWARM_HOST_PROTECT_MAX_VRAM_FRAC   0.55  offer ≤ this fraction of total VRAM
  GPU_SWARM_HOST_PROTECT_PAUSE_UTIL_PCT  65    pause lease when GPU util ≥ this
  GPU_SWARM_HOST_PROTECT_MIN_FREE_VRAM_MB 1536 pause when free VRAM below this
  GPU_SWARM_HOST_PROTECT_MAX_CPU_PERCENT 70    clamp CPU offer ceiling
  GPU_SWARM_HOST_PROTECT_MAX_CUDA_MATRIX 1024  cap pytorch_cuda_probe matrix size
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key, "").strip().lower()
    if not raw:
        return default
    if raw in ("0", "false", "no", "off", "disabled"):
        return False
    if raw in ("1", "true", "yes", "on", "enabled"):
        return True
    return default


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


# Conservative desktop defaults: leave ~45% VRAM headroom; pause before DWM freezes.
DEFAULT_ENABLED = True
DEFAULT_MAX_VRAM_FRACTION = 0.55
DEFAULT_PAUSE_GPU_UTIL_PCT = 65.0
DEFAULT_MIN_FREE_VRAM_MB = 1536
DEFAULT_MAX_CPU_PERCENT = 70.0
DEFAULT_MAX_CUDA_MATRIX = 1024


@dataclass(frozen=True)
class HostProtectConfig:
    """Durable host-protect policy applied on the contributor worker."""

    enabled: bool = DEFAULT_ENABLED
    max_vram_fraction: float = DEFAULT_MAX_VRAM_FRACTION
    pause_gpu_util_pct: float = DEFAULT_PAUSE_GPU_UTIL_PCT
    min_free_vram_mb: int = DEFAULT_MIN_FREE_VRAM_MB
    max_cpu_percent: float = DEFAULT_MAX_CPU_PERCENT
    max_cuda_matrix_size: int = DEFAULT_MAX_CUDA_MATRIX

    def summary(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "max_vram_fraction": self.max_vram_fraction,
            "pause_gpu_util_pct": self.pause_gpu_util_pct,
            "min_free_vram_mb": self.min_free_vram_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "max_cuda_matrix_size": self.max_cuda_matrix_size,
        }


@dataclass(frozen=True)
class AdmissionDecision:
    admit: bool
    reason: str
    max_util_pct: float
    free_vram_mb: int
    vram_ceiling_mb: int


def load_host_protect(
    *,
    enabled_override: bool | None = None,
) -> HostProtectConfig:
    """Load policy from env. ``enabled_override`` wins (joiner_settings / CLI)."""
    enabled = (
        DEFAULT_ENABLED if enabled_override is None else bool(enabled_override)
    )
    if enabled_override is None:
        enabled = _env_bool("GPU_SWARM_HOST_PROTECT", DEFAULT_ENABLED)
    frac = _env_float(
        "GPU_SWARM_HOST_PROTECT_MAX_VRAM_FRAC", DEFAULT_MAX_VRAM_FRACTION
    )
    frac = max(0.15, min(frac, 0.95))
    pause = _env_float(
        "GPU_SWARM_HOST_PROTECT_PAUSE_UTIL_PCT", DEFAULT_PAUSE_GPU_UTIL_PCT
    )
    pause = max(20.0, min(pause, 99.0))
    min_free = _env_int(
        "GPU_SWARM_HOST_PROTECT_MIN_FREE_VRAM_MB", DEFAULT_MIN_FREE_VRAM_MB
    )
    min_free = max(256, min_free)
    max_cpu = _env_float(
        "GPU_SWARM_HOST_PROTECT_MAX_CPU_PERCENT", DEFAULT_MAX_CPU_PERCENT
    )
    max_cpu = max(10.0, min(max_cpu, 100.0))
    matrix = _env_int(
        "GPU_SWARM_HOST_PROTECT_MAX_CUDA_MATRIX", DEFAULT_MAX_CUDA_MATRIX
    )
    matrix = max(64, min(matrix, 4096))
    return HostProtectConfig(
        enabled=enabled,
        max_vram_fraction=frac,
        pause_gpu_util_pct=pause,
        min_free_vram_mb=min_free,
        max_cpu_percent=max_cpu,
        max_cuda_matrix_size=matrix,
    )


def vram_offer_ceiling_mb(total_vram_mb: int, cfg: HostProtectConfig) -> int:
    """Max VRAM MiB this host may advertise when protect is on."""
    total = max(0, int(total_vram_mb or 0))
    if not cfg.enabled or total <= 0:
        return total
    return max(256, int(total * cfg.max_vram_fraction))


def apply_offer_caps(
    *,
    total_vram_mb: int,
    free_vram_mb: int,
    max_vram_mb: int,
    max_cpu_percent: float,
    cfg: HostProtectConfig,
) -> dict[str, Any]:
    """Clamp advertised offer caps under the host safety ceiling.

    Returns dict with effective max_vram_mb, free_vram_mb, max_cpu_percent,
    vram_ceiling_mb, and host_protect summary.
    """
    raw_free = max(0, int(free_vram_mb or 0))
    raw_total = max(0, int(total_vram_mb or 0))
    user_max = max(0, int(max_vram_mb or 0))
    cpu = float(max_cpu_percent if max_cpu_percent is not None else 50.0)

    ceiling = vram_offer_ceiling_mb(raw_total, cfg)
    if cfg.enabled and raw_total > 0:
        # User offer clamped under the durable desktop ceiling (default ~55% VRAM).
        effective_max = ceiling if user_max <= 0 else min(user_max, ceiling)
        free = min(raw_free, effective_max)
        if cpu > cfg.max_cpu_percent:
            cpu = cfg.max_cpu_percent
    else:
        effective_max = user_max
        free = min(raw_free, user_max) if user_max > 0 else raw_free

    return {
        "max_vram_mb": int(effective_max),
        "free_vram_mb": int(free),
        "max_cpu_percent": float(cpu),
        "vram_ceiling_mb": int(ceiling),
        "host_protect": cfg.summary(),
    }


def evaluate_admission(
    gpus: list[dict[str, Any]] | None,
    cfg: HostProtectConfig,
    *,
    vram_ceiling_mb: int = 0,
) -> AdmissionDecision:
    """Decide whether the worker may lease a new job right now.

    Uses live nvidia-smi fields already present on GPU dicts (no mocks).
    CPU-only hosts (no GPUs) always admit — protect is GPU-desktop focused.
    """
    gpu_list = list(gpus or [])
    if not cfg.enabled:
        free = sum(int(g.get("memory_free_mb") or 0) for g in gpu_list)
        util = max((float(g.get("utilization_gpu_pct") or 0) for g in gpu_list), default=0.0)
        return AdmissionDecision(
            admit=True,
            reason="host_protect_disabled",
            max_util_pct=util,
            free_vram_mb=free,
            vram_ceiling_mb=int(vram_ceiling_mb or 0),
        )
    if not gpu_list:
        return AdmissionDecision(
            admit=True,
            reason="cpu_only",
            max_util_pct=0.0,
            free_vram_mb=0,
            vram_ceiling_mb=0,
        )

    free = sum(int(g.get("memory_free_mb") or 0) for g in gpu_list)
    util = max(float(g.get("utilization_gpu_pct") or 0) for g in gpu_list)
    ceiling = int(vram_ceiling_mb or 0)

    if util >= cfg.pause_gpu_util_pct:
        return AdmissionDecision(
            admit=False,
            reason=(
                f"gpu_util {util:.0f}% >= pause ceiling "
                f"{cfg.pause_gpu_util_pct:.0f}% (desktop headroom)"
            ),
            max_util_pct=util,
            free_vram_mb=free,
            vram_ceiling_mb=ceiling,
        )
    if free < cfg.min_free_vram_mb:
        return AdmissionDecision(
            admit=False,
            reason=(
                f"free_vram {free} MiB < min {cfg.min_free_vram_mb} MiB "
                "(desktop headroom)"
            ),
            max_util_pct=util,
            free_vram_mb=free,
            vram_ceiling_mb=ceiling,
        )
    return AdmissionDecision(
        admit=True,
        reason="ok",
        max_util_pct=util,
        free_vram_mb=free,
        vram_ceiling_mb=ceiling,
    )


def clamp_cuda_matrix_size(size: int, cfg: HostProtectConfig | None = None) -> int:
    """Bound pytorch_cuda_probe matrix size; tighter when host protect is on."""
    cfg = cfg or load_host_protect()
    size = int(size or 1024)
    size = max(64, min(size, 4096))
    if cfg.enabled:
        size = min(size, cfg.max_cuda_matrix_size)
    return size

"""Unit checks for host GPU safety ceiling (no CUDA / no stress)."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gpu_swarm.host_protect import (
    HostProtectConfig,
    apply_offer_caps,
    clamp_cuda_matrix_size,
    evaluate_admission,
    load_host_protect,
    vram_offer_ceiling_mb,
)


class HostProtectTests(unittest.TestCase):
    def test_default_enabled(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GPU_SWARM_HOST_PROTECT", None)
            cfg = load_host_protect()
        self.assertTrue(cfg.enabled)
        self.assertAlmostEqual(cfg.max_vram_fraction, 0.55)
        self.assertAlmostEqual(cfg.pause_gpu_util_pct, 65.0)

    def test_vram_ceiling_clamps_user_offer(self) -> None:
        cfg = HostProtectConfig(enabled=True, max_vram_fraction=0.55)
        # 24 GiB card → ceiling ~13 209 MiB
        ceiling = vram_offer_ceiling_mb(24576, cfg)
        self.assertEqual(ceiling, int(24576 * 0.55))
        out = apply_offer_caps(
            total_vram_mb=24576,
            free_vram_mb=20000,
            max_vram_mb=24576,  # user tried to offer full card
            max_cpu_percent=100.0,
            cfg=cfg,
        )
        self.assertEqual(out["max_vram_mb"], ceiling)
        self.assertEqual(out["free_vram_mb"], ceiling)
        self.assertLessEqual(out["max_cpu_percent"], cfg.max_cpu_percent)

    def test_zero_user_max_gets_ceiling_when_protect_on(self) -> None:
        cfg = HostProtectConfig(enabled=True, max_vram_fraction=0.55)
        out = apply_offer_caps(
            total_vram_mb=8192,
            free_vram_mb=7000,
            max_vram_mb=0,
            max_cpu_percent=50.0,
            cfg=cfg,
        )
        self.assertEqual(out["max_vram_mb"], int(8192 * 0.55))
        self.assertEqual(out["free_vram_mb"], int(8192 * 0.55))

    def test_admission_pauses_on_high_util(self) -> None:
        cfg = HostProtectConfig(enabled=True, pause_gpu_util_pct=65.0, min_free_vram_mb=1536)
        gpus = [
            {
                "index": 0,
                "memory_free_mb": 8000,
                "utilization_gpu_pct": 90,
            }
        ]
        d = evaluate_admission(gpus, cfg)
        self.assertFalse(d.admit)
        self.assertIn("gpu_util", d.reason)

    def test_admission_pauses_on_low_free_vram(self) -> None:
        cfg = HostProtectConfig(enabled=True, pause_gpu_util_pct=65.0, min_free_vram_mb=1536)
        gpus = [
            {
                "index": 0,
                "memory_free_mb": 512,
                "utilization_gpu_pct": 10,
            }
        ]
        d = evaluate_admission(gpus, cfg)
        self.assertFalse(d.admit)
        self.assertIn("free_vram", d.reason)

    def test_admission_ok_with_headroom(self) -> None:
        cfg = HostProtectConfig(enabled=True, pause_gpu_util_pct=65.0, min_free_vram_mb=1536)
        gpus = [
            {
                "index": 0,
                "memory_free_mb": 6000,
                "utilization_gpu_pct": 20,
            }
        ]
        d = evaluate_admission(gpus, cfg)
        self.assertTrue(d.admit)

    def test_cpu_only_always_admits(self) -> None:
        cfg = HostProtectConfig(enabled=True)
        d = evaluate_admission([], cfg)
        self.assertTrue(d.admit)
        self.assertEqual(d.reason, "cpu_only")

    def test_matrix_clamp(self) -> None:
        cfg = HostProtectConfig(enabled=True, max_cuda_matrix_size=1024)
        self.assertEqual(clamp_cuda_matrix_size(4096, cfg), 1024)
        cfg_off = HostProtectConfig(enabled=False, max_cuda_matrix_size=1024)
        self.assertEqual(clamp_cuda_matrix_size(2048, cfg_off), 2048)

    def test_disable_via_override(self) -> None:
        cfg = load_host_protect(enabled_override=False)
        self.assertFalse(cfg.enabled)
        out = apply_offer_caps(
            total_vram_mb=8192,
            free_vram_mb=7000,
            max_vram_mb=0,
            max_cpu_percent=90.0,
            cfg=cfg,
        )
        self.assertEqual(out["max_vram_mb"], 0)
        self.assertEqual(out["free_vram_mb"], 7000)
        self.assertEqual(out["max_cpu_percent"], 90.0)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for contributor availability windows."""

from __future__ import annotations

import unittest
from datetime import datetime

from gpu_swarm.availability_schedule import (
    AvailabilityConfig,
    apply_preset,
    is_available,
    next_resume_at,
    status_dict,
)


class AvailabilityScheduleTests(unittest.TestCase):
    def test_always_on(self) -> None:
        cfg = AvailabilityConfig(mode="always")
        self.assertTrue(is_available(cfg))
        self.assertEqual(status_dict(cfg)["label"], "Sharing now")

    def test_daily_overnight_window_inside(self) -> None:
        cfg = AvailabilityConfig(mode="daily", daily_start="22:00", daily_end="08:00")
        inside = datetime(2026, 8, 4, 23, 30)
        self.assertTrue(is_available(cfg, inside))

    def test_daily_overnight_window_outside(self) -> None:
        cfg = AvailabilityConfig(mode="daily", daily_start="22:00", daily_end="08:00")
        outside = datetime(2026, 8, 4, 14, 0)
        self.assertFalse(is_available(cfg, outside))
        st = status_dict(cfg, outside)
        self.assertFalse(st["available"])
        self.assertIn("Paused", st["label"])

    def test_daily_same_day_window(self) -> None:
        cfg = AvailabilityConfig(mode="daily", daily_start="10:00", daily_end="18:00")
        self.assertTrue(is_available(cfg, datetime(2026, 8, 4, 12, 0)))
        self.assertFalse(is_available(cfg, datetime(2026, 8, 4, 9, 0)))

    def test_timer_active_and_expired(self) -> None:
        now = datetime(2026, 8, 4, 12, 0)
        cfg = AvailabilityConfig(mode="timer", until_ts=now.timestamp() + 3600)
        self.assertTrue(is_available(cfg, now))
        expired = datetime(2026, 8, 4, 14, 0)
        cfg2 = AvailabilityConfig(mode="timer", until_ts=expired.timestamp() - 10)
        self.assertFalse(is_available(cfg2, expired))

    def test_next_resume_overnight(self) -> None:
        cfg = AvailabilityConfig(mode="daily", daily_start="22:00", daily_end="08:00")
        outside = datetime(2026, 8, 4, 14, 0)
        resume = next_resume_at(cfg, outside)
        self.assertIsNotNone(resume)
        assert resume is not None
        self.assertEqual(resume.hour, 22)

    def test_preset_nights(self) -> None:
        cfg = apply_preset("nights_weekends")
        self.assertEqual(cfg.mode, "nights_weekends")
        self.assertEqual(cfg.daily_start, "22:00")

    def test_nights_weekends_saturday(self) -> None:
        cfg = apply_preset("nights_weekends")
        self.assertTrue(is_available(cfg, datetime(2026, 8, 8, 14, 0)))  # Saturday

    def test_preset_next_2h(self) -> None:
        cfg = apply_preset("next_2_hours", now=1000.0)
        self.assertEqual(cfg.mode, "timer")
        self.assertAlmostEqual(cfg.until_ts, 8200.0)


if __name__ == "__main__":
    unittest.main()

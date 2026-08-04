"""When a contributor's PC is available to accept pool jobs."""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

MODES = frozenset({"always", "daily", "timer", "nights_weekends"})
PRESET_ALWAYS = "always"
PRESET_NIGHTS = "nights_weekends"
PRESET_NEXT_2H = "next_2_hours"
PRESET_CUSTOM = "custom"

PRESET_LABELS: dict[str, str] = {
    PRESET_ALWAYS: "Always on",
    PRESET_NIGHTS: "Nights & weekends (10pm–8am)",
    PRESET_NEXT_2H: "Next 2 hours",
    PRESET_CUSTOM: "Custom daily window",
}


@dataclass
class AvailabilityConfig:
    mode: str = "always"
    daily_start: str = "22:00"
    daily_end: str = "08:00"
    until_ts: float = 0.0

    def normalized(self) -> AvailabilityConfig:
        mode = (self.mode or "always").strip().lower()
        if mode not in MODES:
            mode = "always"
        return AvailabilityConfig(
            mode=mode,
            daily_start=_norm_hm(self.daily_start, "22:00"),
            daily_end=_norm_hm(self.daily_end, "08:00"),
            until_ts=float(self.until_ts or 0.0),
        )


def _norm_hm(raw: str, default: str) -> str:
    try:
        h, m = _parse_hm(raw)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"
    except (ValueError, TypeError):
        pass
    return default


def _parse_hm(value: str) -> tuple[int, int]:
    text = (value or "").strip()
    if not text:
        return 0, 0
    parts = text.split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    return h, m


def _minutes_since_midnight(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def _hm_to_minutes(hm: str) -> int:
    h, m = _parse_hm(hm)
    return h * 60 + m


def from_mapping(data: dict[str, Any] | None) -> AvailabilityConfig:
    if not data:
        return AvailabilityConfig()
    return AvailabilityConfig(
        mode=str(data.get("availability_mode") or data.get("mode") or "always"),
        daily_start=str(data.get("availability_daily_start") or data.get("daily_start") or "22:00"),
        daily_end=str(data.get("availability_daily_end") or data.get("daily_end") or "08:00"),
        until_ts=float(data.get("availability_until") or data.get("until_ts") or 0.0),
    ).normalized()


def from_env() -> AvailabilityConfig:
    until_raw = os.environ.get("GPU_SWARM_AVAILABILITY_UNTIL", "").strip()
    until = 0.0
    if until_raw:
        try:
            until = float(until_raw)
        except ValueError:
            until = 0.0
    return AvailabilityConfig(
        mode=os.environ.get("GPU_SWARM_AVAILABILITY_MODE", "always") or "always",
        daily_start=os.environ.get("GPU_SWARM_AVAILABILITY_START", "22:00") or "22:00",
        daily_end=os.environ.get("GPU_SWARM_AVAILABILITY_END", "08:00") or "08:00",
        until_ts=until,
    ).normalized()


def to_env_dict(cfg: AvailabilityConfig) -> dict[str, str]:
    c = cfg.normalized()
    out = {
        "GPU_SWARM_AVAILABILITY_MODE": c.mode,
        "GPU_SWARM_AVAILABILITY_START": c.daily_start,
        "GPU_SWARM_AVAILABILITY_END": c.daily_end,
    }
    if c.mode == "timer" and c.until_ts > 0:
        out["GPU_SWARM_AVAILABILITY_UNTIL"] = str(int(c.until_ts))
    else:
        out["GPU_SWARM_AVAILABILITY_UNTIL"] = ""
    return out


def apply_preset(preset: str, *, now: float | None = None) -> AvailabilityConfig:
    """Map UI preset → concrete schedule fields."""
    key = (preset or PRESET_ALWAYS).strip().lower()
    now_ts = time.time() if now is None else float(now)
    if key == PRESET_NIGHTS:
        return AvailabilityConfig(
            mode="nights_weekends", daily_start="22:00", daily_end="08:00"
        )
    if key == PRESET_NEXT_2H:
        return AvailabilityConfig(mode="timer", until_ts=now_ts + 2 * 3600)
    if key == PRESET_CUSTOM:
        return AvailabilityConfig(mode="daily")
    return AvailabilityConfig(mode="always")


def is_available(cfg: AvailabilityConfig, now: datetime | None = None) -> bool:
    c = cfg.normalized()
    now = now or datetime.now()
    if c.mode == "always":
        return True
    if c.mode == "timer":
        if c.until_ts <= 0:
            return False
        return now.timestamp() < c.until_ts
    if c.mode in ("daily", "nights_weekends"):
        if c.mode == "nights_weekends" and now.weekday() >= 5:
            return True
        start_m = _hm_to_minutes(c.daily_start)
        end_m = _hm_to_minutes(c.daily_end)
        cur = _minutes_since_midnight(now)
        if start_m == end_m:
            return True
        if start_m < end_m:
            return start_m <= cur < end_m
        return cur >= start_m or cur < end_m
    return True


def next_resume_at(cfg: AvailabilityConfig, now: datetime | None = None) -> datetime | None:
    """Next moment sharing turns on (local time). None if always-on or unknown."""
    c = cfg.normalized()
    now = now or datetime.now()
    if c.mode == "always":
        return None
    if c.mode == "timer":
        if c.until_ts <= 0 or now.timestamp() < c.until_ts:
            return None
        return None
    if c.mode in ("daily", "nights_weekends"):
        if is_available(c, now):
            return None
        if c.mode == "nights_weekends" and now.weekday() < 4:
            # Mon–Thu daytime: resume tonight
            pass
        elif c.mode == "nights_weekends" and now.weekday() == 4:
            # Friday daytime: resume tonight or all weekend
            pass
        start_m = _hm_to_minutes(c.daily_start)
        h, m = divmod(start_m, 60)
        candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        if c.mode == "nights_weekends" and now.weekday() == 4 and candidate.weekday() == 5:
            # Friday before night window → weekend starts Saturday 00:00
            candidate = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return candidate
    return None


def _format_time(dt: datetime) -> str:
    h = dt.hour % 12 or 12
    ampm = "am" if dt.hour < 12 else "pm"
    return f"{h}:{dt.minute:02d} {ampm}"


def status_dict(cfg: AvailabilityConfig, now: datetime | None = None) -> dict[str, Any]:
    c = cfg.normalized()
    now = now or datetime.now()
    avail = is_available(c, now)
    resume = next_resume_at(c, now)
    resume_label = _format_time(resume) if resume else ""
    if resume and resume.date() != now.date():
        days = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        resume_label = f"{days[resume.weekday()]} {_format_time(resume)}"

    if avail:
        label = "Sharing now"
        if c.mode == "timer" and c.until_ts > 0:
            left = max(0, int(c.until_ts - now.timestamp()))
            hrs, rem = divmod(left, 3600)
            mins = rem // 60
            if hrs:
                label = f"Sharing now — for {hrs}h {mins}m more"
            else:
                label = f"Sharing now — for {mins}m more"
    elif c.mode == "timer":
        label = "Paused — timer ended (pick a new window)"
    elif resume_label:
        label = f"Paused — resumes at {resume_label}"
    else:
        label = "Paused — outside your schedule"

    return {
        "available": avail,
        "mode": c.mode,
        "daily_start": c.daily_start,
        "daily_end": c.daily_end,
        "until_ts": c.until_ts,
        "label": label,
        "resume_at": resume.isoformat() if resume else "",
        "resume_label": resume_label,
    }


def settings_to_config(settings: Any) -> AvailabilityConfig:
    return AvailabilityConfig(
        mode=str(getattr(settings, "availability_mode", "always") or "always"),
        daily_start=str(getattr(settings, "availability_daily_start", "22:00") or "22:00"),
        daily_end=str(getattr(settings, "availability_daily_end", "08:00") or "08:00"),
        until_ts=float(getattr(settings, "availability_until", 0) or 0),
    ).normalized()


def config_to_settings_fields(cfg: AvailabilityConfig) -> dict[str, Any]:
    c = cfg.normalized()
    return {
        "availability_mode": c.mode,
        "availability_daily_start": c.daily_start,
        "availability_daily_end": c.daily_end,
        "availability_until": c.until_ts,
    }


def asdict_public(cfg: AvailabilityConfig) -> dict[str, Any]:
    return asdict(cfg.normalized())


def apply_preset_to_settings(settings: Any, preset: str, *, now: float | None = None) -> Any:
    """Apply a UI preset onto joiner settings (mutates and returns settings)."""
    cfg = apply_preset(preset, now=now)
    if (preset or "").strip().lower() == PRESET_CUSTOM:
        cfg = AvailabilityConfig(
            mode="daily",
            daily_start=str(getattr(settings, "availability_daily_start", "22:00") or "22:00"),
            daily_end=str(getattr(settings, "availability_daily_end", "08:00") or "08:00"),
        ).normalized()
    for key, value in config_to_settings_fields(cfg).items():
        setattr(settings, key, value)
    setattr(settings, "availability_preset", (preset or PRESET_ALWAYS).strip().lower())
    return settings

"""Public + private endpoint discovery for friends / installer.

Order for auto-detect (first reachable wins):
  1. Explicit URL / GPU_SWARM_SCHEDULER_URL (if set and valid)
  2. data/public_endpoints.json (Cloudflare quick tunnel / published public URL)
  3. Tailscale default http://100.85.165.84:8766 (and live Tailscale IP)
  4. localhost http://127.0.0.1:8766

Coordinates with scripts/start_public_tunnel.ps1 which writes public_endpoints.json.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from gpu_swarm.joiner_settings import (
    DEFAULT_LOCAL_PORTAL_URL,
    DEFAULT_LOCAL_SCHEDULER_URL,
    DEFAULT_PORTAL_URL,
    DEFAULT_SCHEDULER_URL,
    detect_tailscale_ipv4,
)
from gpu_swarm.paths import ROOT

PUBLIC_ENDPOINTS_PATH = ROOT / "data" / "public_endpoints.json"
# Optional committed share file (safe URLs only — never secrets)
PUBLIC_ENDPOINTS_SHARE = ROOT / "data" / "public_endpoints.share.txt"

_SCHEDULER_PORT = 8766
_PORTAL_PORT = 8767


def public_endpoints_path() -> Path:
    return PUBLIC_ENDPOINTS_PATH


def load_public_endpoints(path: Path | None = None) -> dict[str, Any] | None:
    """
    Read data/public_endpoints.json written by the host public-tunnel scripts.

    Expected shape (flexible keys):
      {
        "version": 1,
        "provider": "cloudflare-quick-tunnel",
        "scheduler_url": "https://….trycloudflare.com",
        "portal_url": "https://….trycloudflare.com/portal",
        "updated_at": "…"
      }
    """
    p = path or PUBLIC_ENDPOINTS_PATH
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    sched = (
        raw.get("scheduler_url")
        or raw.get("scheduler")
        or raw.get("public_scheduler_url")
        or ""
    )
    portal = (
        raw.get("portal_url")
        or raw.get("portal")
        or raw.get("public_portal_url")
        or ""
    )
    sched = str(sched).strip().rstrip("/")
    portal = str(portal).strip().rstrip("/")
    if portal and not portal.endswith("/portal") and "trycloudflare" in portal:
        # quick tunnel to portal root — append /portal for the UI path
        if not portal.endswith("/portal"):
            portal = f"{portal}/portal"
    if not sched and not portal:
        return None
    return {
        "version": raw.get("version", 1),
        "provider": raw.get("provider") or raw.get("source") or "public",
        "scheduler_url": sched,
        "portal_url": portal,
        "updated_at": raw.get("updated_at") or raw.get("updated") or "",
        "note": raw.get("note") or "",
        "raw": raw,
        "path": str(p),
    }


def normalize_scheduler_url(url: str) -> str:
    """Strip whitespace/trailing slash; add http:// if scheme missing."""
    u = (url or "").strip().rstrip("/")
    if not u:
        return ""
    if "://" not in u:
        u = "http://" + u
    return u.rstrip("/")


def validate_scheduler_url(url: str) -> dict[str, Any]:
    """
    Validate a scheduler base URL for friends / env GPU_SWARM_SCHEDULER_URL.

    Accepts:
      - http://100.85.165.84:8766
      - http://127.0.0.1:8766
      - https://….trycloudflare.com (public tunnel, default 443 OK)
    Rejects common mistakes (bare IP without port, portal URL, missing scheme).
    """
    raw = (url or "").strip()
    if not raw:
        return {
            "ok": False,
            "url": "",
            "normalized": "",
            "error": "Incorrect Scheduler URL Environment Variable — value is empty.",
            "hint": (
                f"Set GPU_SWARM_SCHEDULER_URL={DEFAULT_SCHEDULER_URL} "
                f"(must include port {_SCHEDULER_PORT}) or use the app auto-detect."
            ),
        }

    normalized = normalize_scheduler_url(raw)
    try:
        parsed = urlparse(normalized)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "url": raw,
            "normalized": "",
            "error": f"Incorrect Scheduler URL Environment Variable — {exc}",
            "hint": f"Use a full URL like {DEFAULT_SCHEDULER_URL}",
        }

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return {
            "ok": False,
            "url": raw,
            "normalized": normalized,
            "error": "Incorrect Scheduler URL Environment Variable — need http:// or https://",
            "hint": f"Example: {DEFAULT_SCHEDULER_URL}",
        }

    host = parsed.hostname or ""
    if not host:
        return {
            "ok": False,
            "url": raw,
            "normalized": normalized,
            "error": "Incorrect Scheduler URL Environment Variable — missing host",
            "hint": f"Example: {DEFAULT_SCHEDULER_URL}",
        }

    # Portal URL mistaken for scheduler
    path = (parsed.path or "").rstrip("/")
    if path.endswith("/portal") or ":8767" in normalized:
        return {
            "ok": False,
            "url": raw,
            "normalized": normalized,
            "error": (
                "Incorrect Scheduler URL Environment Variable — that looks like the "
                f"portal (:{_PORTAL_PORT}), not the scheduler (:{_SCHEDULER_PORT})."
            ),
            "hint": (
                f"Scheduler: {DEFAULT_SCHEDULER_URL}  ·  Portal: {DEFAULT_PORTAL_URL}"
            ),
        }

    port = parsed.port
    # Bare Tailscale/LAN IP or localhost without port → almost always wrong (defaults to 80)
    is_localish = host in ("127.0.0.1", "localhost") or host.startswith("100.")
    if scheme == "http" and port is None and is_localish:
        return {
            "ok": False,
            "url": raw,
            "normalized": normalized,
            "error": (
                "Incorrect Scheduler URL Environment Variable — missing port "
                f"{_SCHEDULER_PORT} (common mistake: bare IP without :{_SCHEDULER_PORT})."
            ),
            "hint": (
                f"Use http://{host}:{_SCHEDULER_PORT}  "
                f"(Tailscale default: {DEFAULT_SCHEDULER_URL})"
            ),
            "suggested": f"http://{host}:{_SCHEDULER_PORT}",
        }

    if port is not None and port == _PORTAL_PORT:
        return {
            "ok": False,
            "url": raw,
            "normalized": normalized,
            "error": (
                f"Incorrect Scheduler URL Environment Variable — port {_PORTAL_PORT} is the "
                f"portal; scheduler is {_SCHEDULER_PORT}."
            ),
            "hint": f"Correct: http://{host}:{_SCHEDULER_PORT}",
            "suggested": f"{scheme}://{host}:{_SCHEDULER_PORT}",
        }

    return {
        "ok": True,
        "url": raw,
        "normalized": normalized,
        "error": "",
        "hint": "Scheduler URL looks valid (app will still probe /status).",
        "suggested": normalized,
    }


def scheduler_url_candidates(
    explicit: str | None = None,
    *,
    include_env: bool = True,
    include_public: bool = True,
    include_saved: str | None = None,
) -> list[dict[str, str]]:
    """Ordered candidate list with source labels (deduped)."""
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url: str, source: str) -> None:
        u = normalize_scheduler_url(url)
        if not u or u in seen:
            return
        # Soft-skip obviously invalid (portal port) but keep validated suggestions
        v = validate_scheduler_url(u)
        if not v.get("ok") and v.get("suggested"):
            u = normalize_scheduler_url(str(v["suggested"]))
            if not u or u in seen:
                return
        elif not v.get("ok"):
            return
        seen.add(u)
        out.append({"url": u, "source": source})

    if explicit:
        add(explicit, "explicit")
    if include_env:
        env = (os.environ.get("GPU_SWARM_SCHEDULER_URL") or "").strip()
        if env:
            add(env, "env:GPU_SWARM_SCHEDULER_URL")
    if include_saved:
        add(include_saved, "saved")
    if include_public:
        pub = load_public_endpoints()
        if pub and pub.get("scheduler_url"):
            add(str(pub["scheduler_url"]), "public_endpoints.json")
    add(DEFAULT_SCHEDULER_URL, "tailscale-default")
    ts = detect_tailscale_ipv4()
    if ts:
        add(f"http://{ts}:{_SCHEDULER_PORT}", "tailscale-local-ip")
    add(DEFAULT_LOCAL_SCHEDULER_URL, "localhost")
    return out


def portal_url_candidates_extended() -> list[dict[str, str]]:
    """Portal candidates including public_endpoints.json when present."""
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url: str, source: str) -> None:
        u = (url or "").strip().rstrip("/")
        if not u:
            return
        if not u.endswith("/portal"):
            u = f"{u}/portal" if u.endswith(":8767") or "trycloudflare" in u else u
        if u in seen:
            return
        seen.add(u)
        out.append({"url": u, "source": source})

    pub = load_public_endpoints()
    if pub and pub.get("portal_url"):
        add(str(pub["portal_url"]), "public_endpoints.json")
    add(DEFAULT_LOCAL_PORTAL_URL, "localhost")
    add(DEFAULT_PORTAL_URL, "tailscale-default")
    ts = detect_tailscale_ipv4()
    if ts:
        add(f"http://{ts}:{_PORTAL_PORT}/portal", "tailscale-local-ip")
    return out


def probe_scheduler(url: str, timeout: float = 2.5) -> dict[str, Any]:
    """GET {url}/status — real HTTP."""
    import httpx

    base = normalize_scheduler_url(url)
    if not base:
        return {"ok": False, "url": "", "error": "empty url", "data": None}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.get(f"{base}/status")
            r.raise_for_status()
            data = r.json()
        return {"ok": True, "url": base, "error": "", "data": data}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": base, "error": str(exc), "data": None}


def auto_detect_scheduler_url(
    explicit: str | None = None,
    *,
    saved: str | None = None,
    timeout: float = 2.5,
    probe: bool = True,
) -> dict[str, Any]:
    """
    Pick the best scheduler URL. Prefer first reachable when probe=True;
    otherwise return first valid candidate (public → Tailscale → local).
    """
    candidates = scheduler_url_candidates(explicit, include_saved=saved)
    attempts: list[dict[str, Any]] = []

    if not probe:
        first = candidates[0] if candidates else {
            "url": DEFAULT_SCHEDULER_URL,
            "source": "tailscale-default",
        }
        v = validate_scheduler_url(first["url"])
        return {
            "ok": bool(v.get("ok")),
            "url": v.get("normalized") or first["url"],
            "source": first["source"],
            "probed": False,
            "attempts": [],
            "public": load_public_endpoints(),
            "error": v.get("error") or "",
            "hint": v.get("hint") or "",
            "message": f"Selected {first['source']}: {first['url']} (not probed)",
        }

    for c in candidates:
        result = probe_scheduler(c["url"], timeout=timeout)
        attempts.append({**result, "source": c["source"]})
        if result.get("ok"):
            return {
                "ok": True,
                "url": result["url"],
                "source": c["source"],
                "probed": True,
                "attempts": attempts,
                "public": load_public_endpoints(),
                "data": result.get("data"),
                "error": "",
                "hint": "",
                "message": f"Reachable via {c['source']}: {result['url']}",
            }

    # Nothing reachable — still return best guess for the UI to show + fix text
    pub = load_public_endpoints()
    fallback = (
        (pub or {}).get("scheduler_url")
        or DEFAULT_SCHEDULER_URL
        or DEFAULT_LOCAL_SCHEDULER_URL
    )
    return {
        "ok": False,
        "url": normalize_scheduler_url(str(fallback)),
        "source": "fallback",
        "probed": True,
        "attempts": attempts,
        "public": pub,
        "error": "No scheduler URL reachable yet",
        "hint": (
            "Installer order: public_endpoints.json → Tailscale :8766 → localhost. "
            "Ask Drew for the public portal link (no Tailscale) or join the Glitch Factor tailnet. "
            f"Correct env example: GPU_SWARM_SCHEDULER_URL={DEFAULT_SCHEDULER_URL}"
        ),
        "message": "Could not reach any scheduler candidate",
    }


def connect_urls_for_ui() -> dict[str, Any]:
    """Safe URLs for portal Connect + desktop Connect panels."""
    pub = load_public_endpoints()
    return {
        "scheduler_local": DEFAULT_LOCAL_SCHEDULER_URL.rstrip("/"),
        "scheduler_tailscale": DEFAULT_SCHEDULER_URL.rstrip("/"),
        "portal_local": DEFAULT_LOCAL_PORTAL_URL,
        "portal_tailscale": DEFAULT_PORTAL_URL,
        "public": pub,
        "scheduler_public": (pub or {}).get("scheduler_url") or "",
        "portal_public": (pub or {}).get("portal_url") or "",
        "public_provider": (pub or {}).get("provider") or "",
        "no_tailscale_needed": bool(pub and (pub.get("portal_url") or pub.get("scheduler_url"))),
        "env_example": f"set GPU_SWARM_SCHEDULER_URL={DEFAULT_SCHEDULER_URL}",
        "env_note": (
            "Normal join via the EXE/portal auto-detects the scheduler — "
            "you usually do NOT need to hand-edit GPU_SWARM_SCHEDULER_URL. "
            f"If you do set it, include port {_SCHEDULER_PORT}: {DEFAULT_SCHEDULER_URL}"
        ),
    }

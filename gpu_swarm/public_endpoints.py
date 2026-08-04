"""Read/write Cloudflare (or similar) public tunnel endpoints for friend access."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from gpu_swarm.paths import ROOT

PUBLIC_ENDPOINTS_PATH = ROOT / "data" / "public_endpoints.json"
PUBLIC_SHARE_PATH = ROOT / "data" / "public_endpoints.share.txt"


def load_public_endpoints() -> dict[str, Any] | None:
    """Return public tunnel endpoints if present and usable, else None."""
    path = PUBLIC_ENDPOINTS_PATH
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    portal = str(raw.get("portal_public_url") or raw.get("portal_url") or "").rstrip("/")
    if not portal.startswith("http"):
        return None
    pool_api = str(raw.get("pool_api_public_url") or "").rstrip("/")
    if not pool_api:
        pool_api = f"{portal}/pool-api"
    portal_path = str(raw.get("portal_path") or "").rstrip("/")
    if not portal_path:
        portal_path = f"{portal}/portal"
    return {
        **raw,
        "portal_public_url": portal,
        "portal_path": portal_path,
        "pool_api_public_url": pool_api,
        "no_tailscale_needed": True,
        "active": True,
    }


def write_public_endpoints(
    *,
    portal_public_url: str,
    mode: str = "cloudflared_quick",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist endpoints for portal/app + a shareable text file for DMs."""
    portal = portal_public_url.rstrip("/")
    data: dict[str, Any] = {
        "mode": mode,
        "portal_public_url": portal,
        "portal_path": f"{portal}/portal",
        "pool_api_public_url": f"{portal}/pool-api",
        "scheduler_local": "http://127.0.0.1:8766",
        "portal_local": "http://127.0.0.1:8767",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Public HTTPS via Cloudflare quick tunnel — no Tailscale needed. "
            "Invite code auth still required on the portal. "
            "Scheduler API for friends: use pool_api_public_url (portal proxies allowlisted jobs)."
        ),
        "invite_code": "glitch-factor",
    }
    if extra:
        data.update(extra)
    PUBLIC_ENDPOINTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_ENDPOINTS_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    share = (
        "GPU Pool — public access (no Tailscale needed)\n"
        "----------------------------------------------\n"
        f"Portal:     {data['portal_path']}\n"
        f"Pool API:   {data['pool_api_public_url']}  (proxies scheduler; allowlisted jobs only)\n"
        f"Invite:     {data['invite_code']}\n"
        "\n"
        "Laptop / no NVIDIA: open Portal → sign in with invite + display name → Utilize.\n"
        "Optional: Contribute CPU/RAM/disk with VRAM=0.\n"
        "Tailscale is optional while this tunnel is running.\n"
        f"Updated:    {data['updated_at']}\n"
    )
    PUBLIC_SHARE_PATH.write_text(share, encoding="utf-8")
    return data


def clear_public_endpoints() -> None:
    for path in (PUBLIC_ENDPOINTS_PATH, PUBLIC_SHARE_PATH):
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass

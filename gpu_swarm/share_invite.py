"""Share / Invite others — copyable blurbs for viral pool growth.

UI-safe only: invite code + public/Tailscale/local URLs. Never includes
pool password, .env, tokens, or Tailscale auth keys.
"""

from __future__ import annotations

from typing import Any

from gpu_swarm.joiner_settings import (
    DEFAULT_LOCAL_PORTAL_URL,
    DEFAULT_PORTAL_URL,
    DEFAULT_SCHEDULER_URL,
    PORTAL_INVITE_CODE,
)

GITHUB_REPO_URL = "https://github.com/phoenixfire808/gpu-swarm"
GITHUB_DOWNLOAD_URL = (
    "https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe"
)
LOGIN_DOC_URL = f"{GITHUB_REPO_URL}/blob/master/LOGIN.md"


def _public_urls() -> dict[str, str]:
    portal = ""
    pool_api = ""
    try:
        from gpu_swarm.endpoints import connect_urls_for_ui

        urls = connect_urls_for_ui()
        portal = (urls.get("portal_public") or "").rstrip("/")
        pool_api = (
            urls.get("scheduler_public") or urls.get("pool_api_public") or ""
        ).rstrip("/")
    except Exception:  # noqa: BLE001
        pass
    if not portal:
        try:
            from gpu_swarm.public_endpoints import load_public_endpoints

            pub = load_public_endpoints() or {}
            portal = (pub.get("portal_public_url") or pub.get("portal_path") or "").rstrip("/")
            pool_api = (pub.get("pool_api_public_url") or "").rstrip("/")
        except Exception:  # noqa: BLE001
            pass
    return {"portal_public": portal, "pool_api_public": pool_api}


def build_share_pack() -> dict[str, Any]:
    """Everything the Share / Invite UI needs (no secrets)."""
    pub = _public_urls()
    portal_public = pub["portal_public"]
    pool_api = pub["pool_api_public"]
    portal_best = portal_public or DEFAULT_PORTAL_URL
    public_on = bool(portal_public)

    short = (
        f"Join our GPU Pool — share spare GPU/CPU or run jobs on whoever is online.\n"
        f"1) Open: {portal_best}\n"
        f"2) Invite code: {PORTAL_INVITE_CODE} + your Discord display name\n"
        f"3) Or download Windows app: {GITHUB_DOWNLOAD_URL}\n"
        f"Guide: {LOGIN_DOC_URL}"
    )

    lines = [
        "**GPU Pool** — share spare GPU/CPU, run jobs, chat, invite others",
        "",
        f"Portal: {portal_best}",
        f"Invite code: {PORTAL_INVITE_CODE}  (+ your Discord display name)",
        f"Windows download: {GITHUB_DOWNLOAD_URL}",
        f"Repo: {GITHUB_REPO_URL}",
        f"Login guide: {LOGIN_DOC_URL}",
        "",
        "No NVIDIA? Still join — Utilize the pool or Contribute CPU (VRAM=0).",
        "Private co-op — invite required. Not a public marketplace. No Docker.",
    ]
    if public_on:
        lines.insert(3, "(Public HTTPS — no Tailscale needed while this link works)")
        if pool_api:
            lines.append(f"Optional SDK: GPU_SWARM_SCHEDULER_URL={pool_api}")
    else:
        lines.insert(
            3,
            f"Tailscale/LAN portal: {DEFAULT_PORTAL_URL}  ·  Scheduler: {DEFAULT_SCHEDULER_URL}",
        )
        lines.append(
            "Public tunnel may be off — ask the host for the current public link, "
            "or join the private Tailscale network."
        )
    lines.append(f"Local (same PC as host): {DEFAULT_LOCAL_PORTAL_URL}")

    return {
        "invite_code": PORTAL_INVITE_CODE,
        "invite_note": (
            "Invite code is a product setting (configurable via GPU_SWARM_INVITE_CODES). "
            f"Current default/shared code: {PORTAL_INVITE_CODE}."
        ),
        "github_repo": GITHUB_REPO_URL,
        "github_download": GITHUB_DOWNLOAD_URL,
        "login_doc": LOGIN_DOC_URL,
        "portal_public": portal_public,
        "portal_tailscale": DEFAULT_PORTAL_URL,
        "portal_local": DEFAULT_LOCAL_PORTAL_URL,
        "portal_best": portal_best,
        "pool_api_public": pool_api,
        "scheduler_tailscale": DEFAULT_SCHEDULER_URL,
        "public_access": public_on,
        "short_message": short,
        "invite_blurb": "\n".join(lines),
        "send_to_friend": (
            "Hey — join our GPU Pool. Open the portal, use invite "
            f"**{PORTAL_INVITE_CODE}** with your Discord name, or grab the Windows app.\n\n"
            f"Portal: {portal_best}\n"
            f"Download: {GITHUB_DOWNLOAD_URL}\n"
            f"Guide: {LOGIN_DOC_URL}"
        ),
        "primary_actions": [
            "Join — open portal or app, sign in with invite + display name",
            "Share my PC — Contribute with your caps (host GPU safety ON by default)",
            "Use the pool — Utilize jobs (no NVIDIA needed on your machine)",
            "Invite others — copy the Share blurb and send it to a friend",
        ],
    }


def invite_blurb_text() -> str:
    return str(build_share_pack()["invite_blurb"])


def short_share_message() -> str:
    return str(build_share_pack()["short_message"])

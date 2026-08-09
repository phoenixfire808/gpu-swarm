"""Web portal — contribute machines + utilize allowlisted pool jobs."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from gpu_swarm import ALLOWED_JOB_TYPES
from gpu_swarm.config import PortalConfig, portal_config
from gpu_swarm.joiner_settings import (
    DEFAULT_LOCAL_PORTAL_URL,
    DEFAULT_LOCAL_SCHEDULER_URL,
    DEFAULT_PORTAL_URL,
    DEFAULT_SCHEDULER_URL,
    PORTAL_INVITE_CODE,
)
from gpu_swarm.portal_store import PortalStore
from gpu_swarm.public_endpoints import load_public_endpoints

store: PortalStore | None = None
cfg: PortalConfig = portal_config()

SESSION_COOKIE = "gpu_swarm_portal_session"
UTILIZE_JOB_TYPES = frozenset(ALLOWED_JOB_TYPES)  # v1: probe + pytorch_cuda_probe only


@asynccontextmanager
async def lifespan(app: FastAPI):
    global store, cfg
    cfg = portal_config()
    store = PortalStore(cfg.db_path)
    await store.connect()
    yield
    await store.close()


app = FastAPI(title="GPU Pool Portal", version="0.2.0", lifespan=lifespan)


def _store() -> PortalStore:
    if store is None:
        raise HTTPException(503, "portal store not ready")
    return store


def _public_base(request: Request) -> str:
    if cfg.public_url:
        return cfg.public_url.rstrip("/")
    return str(request.base_url).rstrip("/")


async def _current_user(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get(SESSION_COOKIE, "")
    return await _store().get_session_user(token)


async def _require_user(request: Request) -> dict[str, Any]:
    user = await _current_user(request)
    if not user:
        raise HTTPException(401, "login required")
    return user


class LoginBody(BaseModel):
    display_name: str = Field(min_length=1, max_length=64)
    pool_password: str = ""
    invite_code: str = ""


class MachineBody(BaseModel):
    worker_name: str = Field(min_length=1, max_length=80)
    scheduler_url: str = ""
    max_vram_mb: int = 0
    max_cpu_percent: float = 50.0
    dedicated_ram_mb: int = 0
    dedicated_disk_mb: int = 0
    dedicated_cpu_cores: float = 0.0
    notes: str | None = None
    availability_preset: str = "always"
    availability_mode: str = "always"
    availability_daily_start: str = "22:00"
    availability_daily_end: str = "08:00"
    availability_until: float = 0.0


class MachineCapsPatch(BaseModel):
    """Owner-only cap updates. Does not change another user's machine."""

    worker_name: str | None = Field(default=None, max_length=80)
    max_vram_mb: int | None = None
    max_cpu_percent: float | None = None
    dedicated_ram_mb: int | None = None
    dedicated_disk_mb: int | None = None
    dedicated_cpu_cores: float | None = None
    notes: str | None = None
    availability_preset: str | None = None
    availability_mode: str | None = None
    availability_daily_start: str | None = None
    availability_daily_end: str | None = None
    availability_until: float | None = None


class JobSubmitBody(BaseModel):
    job_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    require_gpu: bool | None = None
    min_vram_mb: int = 0
    matrix_size: int | None = Field(default=None, ge=16, le=4096)


class DiagnosticsBody(BaseModel):
    display_name: str = Field(default="", max_length=64)
    invite_code: str = Field(default="", max_length=64)
    pool_password: str = Field(default="", max_length=128)
    hostname: str = Field(default="", max_length=128)
    wizard_step: str = Field(default="", max_length=120)
    log_text: str = Field(default="", max_length=250_000)
    log_path: str = Field(default="", max_length=512)
    client_time: float | None = None


class ChatPostBody(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class SuggestionPostBody(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    category: str = Field(default="suggestion", max_length=32)


class SuggestionStatusBody(BaseModel):
    status: str = Field(min_length=1, max_length=16)


def _auth_ok(password: str, invite: str) -> tuple[bool, str]:
    """MVP auth: shared pool password and/or invite code. Real OAuth later."""
    pw = (password or "").strip()
    inv = (invite or "").strip()
    expected_pw = (cfg.pool_password or "").strip()
    codes = set(cfg.invite_codes)

    if not expected_pw and not codes:
        # Dev-friendly: allow login when nothing configured, but label method
        return True, "open-dev"

    if expected_pw and pw and secrets_equal(pw, expected_pw):
        return True, "pool_password"
    if codes and inv and inv in codes:
        return True, "invite_code"
    if expected_pw and codes:
        return False, "need_password_or_invite"
    if expected_pw:
        return False, "bad_password"
    return False, "bad_invite"


def secrets_equal(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


async def _fetch_scheduler_status() -> dict[str, Any]:
    url = f"{cfg.scheduler_url.rstrip('/')}/status"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
        return {"ok": True, "error": "", "data": data, "url": url}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "data": None, "url": url}


async def _scheduler_request(
    method: str, path: str, *, json_body: dict[str, Any] | None = None
) -> dict[str, Any]:
    url = f"{cfg.scheduler_url.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.request(method, url, json=json_body)
        try:
            data = r.json()
        except Exception:  # noqa: BLE001
            data = {"detail": r.text}
        if r.status_code >= 400:
            detail = data.get("detail") if isinstance(data, dict) else None
            raise HTTPException(r.status_code, detail or f"scheduler error {r.status_code}")
        return data if isinstance(data, dict) else {"data": data}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"scheduler unreachable: {exc}") from exc


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/portal", status_code=302)


@app.get("/health")
async def health() -> dict[str, Any]:
    pub = load_public_endpoints()
    return {
        "status": "ok",
        "service": "portal",
        "scheduler_url": cfg.scheduler_url,
        "auth": "pool_password_or_invite",
        "oauth": "later",
        "public_access": bool(pub),
        "portal_public_url": (pub or {}).get("portal_public_url") or "",
    }


@app.api_route("/pool-api", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.api_route("/pool-api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def pool_api_proxy(request: Request, path: str = "") -> Response:
    """Proxy scheduler under one public hostname. Allowlisted jobs only on scheduler."""
    suffix = path.lstrip("/")
    target = f"{cfg.scheduler_url.rstrip('/')}/{suffix}" if suffix else cfg.scheduler_url.rstrip("/")
    if request.url.query:
        target = f"{target}?{request.url.query}"
    body = await request.body()
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding", "connection")
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.request(request.method, target, content=body, headers=headers)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"scheduler unreachable via /pool-api: {exc}") from exc
    excluded = {"content-encoding", "transfer-encoding", "connection"}
    out_headers = {k: v for k, v in r.headers.items() if k.lower() not in excluded}
    return Response(
        content=r.content,
        status_code=r.status_code,
        headers=out_headers,
        media_type=r.headers.get("content-type"),
    )


@app.get("/portal", response_class=HTMLResponse)
async def portal_page() -> HTMLResponse:
    # Reload template each request so hub HTML edits apply without full redeploy.
    return HTMLResponse(_load_portal_html())


@app.get("/api/config")
async def api_config(request: Request) -> dict[str, Any]:
    from gpu_swarm.endpoints import connect_urls_for_ui, load_public_endpoints

    portal_base = _public_base(request)
    portal_path = f"{portal_base}/portal"
    sched_tailscale = DEFAULT_SCHEDULER_URL.rstrip("/")
    portal_tailscale = DEFAULT_PORTAL_URL.rstrip("/")
    if not portal_tailscale.endswith("/portal"):
        portal_tailscale = f"{portal_tailscale}/portal"
    urls = connect_urls_for_ui()
    pub = load_public_endpoints()
    sched_public = (urls.get("scheduler_public") or urls.get("pool_api_public") or "").rstrip("/")
    portal_public = (urls.get("portal_public") or "").rstrip("/")
    env_sched = sched_public or sched_tailscale
    from gpu_swarm.share_invite import build_share_pack
    from gpu_swarm.use_cases import USE_CASES

    share = build_share_pack()
    cloudflare_mode = str((pub or {}).get("mode") or "")
    cloudflare_url = str((pub or {}).get("portal_path") or "")
    cloudflare = {
        "active": bool((pub or {}).get("active")),
        "mode": cloudflare_mode,
        "portal_url": cloudflare_url,
        "named_ready": cloudflare_mode == "cloudflared_named",
        "status": (
            "Named Cloudflare Tunnel is live — this stable hostname still depends on the host staying online."
            if cloudflare_mode == "cloudflared_named"
            else "Quick Tunnel is live — the temporary URL changes when the host restarts public access."
            if cloudflare_mode == "cloudflared_quick"
            else "Cloudflare is available from the host installer. The host can publish a Quick Tunnel or create a named tunnel."
        ),
        "quick_command": "launch-public.cmd --no-browser",
        "installer_command": "scripts\\install_cloudflared.cmd",
        "named_command": "scripts\\setup_cloudflare_named.cmd -Hostname gpu-pool.example.com -TunnelName gpu-pool -Launch",
        "host_only_note": "Only the GPU Pool host runs these commands; visitors can use the resulting HTTPS portal but cannot launch the host tunnel from a browser.",
    }
    return {
        "share": share,
        "use_cases": list(USE_CASES),
        "scheduler_url": cfg.scheduler_url,
        "portal_url": portal_base,
        "public_access": bool(urls.get("no_tailscale_needed")),
        "auth_modes": {
            "pool_password": bool(cfg.pool_password),
            "invite_codes": bool(cfg.invite_codes),
            "open_dev": not cfg.pool_password and not cfg.invite_codes,
        },
        "oauth_note": "MVP uses invite code or shared pool password. Real OAuth comes later.",
        "capacity_note": (
            "v1 contributes compute to JOBS (GPU/CPU). RAM/SSD values are capacity "
            "advertisements + future job constraints — not a literal distributed filesystem yet."
        ),
        "laptop_note": (
            "No NVIDIA? You can still Utilize the pool or contribute CPU. "
            "Jobs run on online GPU workers on the host network."
        ),
        "allowed_job_types": sorted(UTILIZE_JOB_TYPES),
        "utilize_note": (
            "No GPU on your laptop? Fine. Allowlisted jobs: probe, pytorch_cuda_probe, llm_chat. "
            "For AI apps, start the Local Pool Endpoint on your machine "
            "(OPENAI_BASE_URL=http://127.0.0.1:8080/v1). See LOCAL_MODEL.md."
        ),
        "invite_code_hint": PORTAL_INVITE_CODE,
        "public_endpoints": pub,
        "cloudflare": cloudflare,
        "connect": {
            "scheduler_local": DEFAULT_LOCAL_SCHEDULER_URL.rstrip("/"),
            "scheduler_tailscale": sched_tailscale,
            "scheduler_public": sched_public,
            "pool_api_public": sched_public,
            "portal_local": DEFAULT_LOCAL_PORTAL_URL,
            "portal_tailscale": portal_tailscale,
            "portal_public": portal_public,
            "portal_this": portal_path,
            "no_tailscale_needed": bool(urls.get("no_tailscale_needed")),
            "cloudflare": cloudflare,
            "discord_primary": "Glitch Factor",
            "discord_bot": "GPU Pool",
            "discord_commands": [
                "/pool", "/workers", "/contribute",
                "/submit_probe", "/submit_compute", "/job_status",
            ],
            "docs": "CONNECTING.md · LOCAL_MODEL.md · NO_GPU_LAPTOP.md",
            "cli": [
                "python -m gpu_swarm local-endpoint",
                "python -m gpu_swarm utilize status",
                "python -m gpu_swarm utilize probe --wait",
                "python -m gpu_swarm utilize cuda --wait",
                "python -m gpu_swarm submit probe --wait",
                "python examples/coding_agent_pool.py --job probe",
            ],
            "python_sdk": (
                "from gpu_swarm.client import GPUPool\n"
                f'pool = GPUPool()  # or GPUPool("{env_sched}")\n'
                'print(pool.status()["workers_online"])\n'
                'print(pool.submit_probe(wait=True)["status"])\n'
            ),
            "http": [
                "GET  /status",
                "POST /jobs   {\"job_type\":\"probe\"}",
                "GET  /jobs/{id}",
            ],
            "local_model": {
                "title": "Local model endpoint (pool as a local AI API)",
                "honesty": (
                    "This is a network GPU via OpenAI-compatible API — "
                    "not a fake Windows display adapter / PCI device."
                ),
                "start": "python -m gpu_swarm local-endpoint   OR   start-local-endpoint.cmd",
                "url": "http://127.0.0.1:8080/v1",
                "env": "OPENAI_BASE_URL=http://127.0.0.1:8080/v1",
                "apps": "Open WebUI · LM Studio · Continue · Cursor",
                "host_worker": (
                    "Any GPU contributor on the host network: install Ollama, pull a model, "
                    "keep ollama serve on :11434, restart the GPU Pool worker "
                    "so llm_ready=yes. See LOCAL_MODEL.md."
                ),
            },
            "workspace_vm": {
                "title": "Workspace VM (agent Ubuntu — Hermes / VirtualBox)",
                "honesty": (
                    "CPU/RAM from your Contribute share only. "
                    "No NVIDIA GPU passthrough into VirtualBox — "
                    "pool GPU jobs stay on the host worker."
                ),
                "how": (
                    "Desktop app: Home → Workspace → Start / Open. "
                    "RDP 127.0.0.1:3390 · vagrant/vagrant. See ADVANCED_VM.md."
                ),
                "control_plane": "hermes agent-vm-control (not OpenClaw, no Docker)",
            },
            "env_example": (
                f"set GPU_SWARM_SCHEDULER_URL={env_sched}\n"
                "set OPENAI_BASE_URL=http://127.0.0.1:8080/v1"
            ),
            "env_note": urls.get("env_note") or (
                "EXE/portal auto-detects the scheduler — hand-editing "
                "GPU_SWARM_SCHEDULER_URL is optional. If you set it, include port 8766 "
                "or use the public …/pool-api URL."
            ),
            "private_network": (
                "Private by default (Tailscale/LAN). When the host publishes a public tunnel, "
                "use the Public URLs — no Tailscale needed."
            ),
            "friends_connect": [
                "Run the GPU Pool EXE (auto-detects scheduler) OR open the portal URL a pool member shares",
                "Public HTTPS if tunnel is up; else Tailscale → :8767/portal",
                f"Sign in with invite code {PORTAL_INVITE_CODE} + your display name",
                "No NVIDIA? Utilize first — Connect → Start local model endpoint → paste OPENAI_BASE_URL into your AI app",
                "GPU friends: Contribute worker + run Ollama so llm_chat jobs can land on you",
                f"Coding env (optional): set GPU_SWARM_SCHEDULER_URL={env_sched}",
            ],
            "rules": [
                "Prefer EXE auto-detect or portal — do not hand-edit env unless coding from CLI.",
                "Scheduler port is 8766 (not portal 8767). Bare IP without port is wrong.",
                "Public friends use …/pool-api as GPU_SWARM_SCHEDULER_URL when tunnel is on.",
                "Allowlisted jobs only — no remote shell on contributors.",
                "Local model endpoint = OpenAI API on localhost, not a PCI GPU driver.",
                "Never share .env or Discord bot tokens.",
            ],
        },
    }


@app.post("/api/login")
async def api_login(body: LoginBody, response: Response) -> dict[str, Any]:
    ok, method = _auth_ok(body.pool_password, body.invite_code)
    if not ok:
        raise HTTPException(401, "Invalid pool password or invite code")
    name = body.display_name.strip()
    if not name:
        raise HTTPException(400, "display_name required")
    user = await _store().upsert_user(name, method)
    token = await _store().create_session(user["id"], cfg.session_ttl_sec)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=cfg.session_ttl_sec,
    )
    return {"ok": True, "user": {"id": user["id"], "display_name": user["display_name"]}, "auth_method": method}


@app.post("/api/logout")
async def api_logout(request: Request, response: Response) -> dict[str, Any]:
    token = request.cookies.get(SESSION_COOKIE, "")
    if token:
        await _store().delete_session(token)
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.get("/api/me")
async def api_me(request: Request) -> dict[str, Any]:
    user = await _current_user(request)
    if not user:
        return {"ok": False, "user": None}
    return {
        "ok": True,
        "user": {
            "id": user["id"],
            "display_name": user["display_name"],
            "auth_method": user["auth_method"],
        },
    }


@app.get("/api/dashboard")
async def api_dashboard(request: Request) -> dict[str, Any]:
    await _require_user(request)
    fetched = await _fetch_scheduler_status()
    machines = await _store().list_machines()
    workers = []
    jobs = {}
    summary: dict[str, Any] = {}
    if fetched.get("ok") and fetched.get("data"):
        summary = fetched["data"]
        workers = summary.get("workers") or []
        jobs = summary.get("jobs") or {}
    # Merge portal machine intent with live heartbeats
    by_name = {str(w.get("name") or "").lower(): w for w in workers}
    enriched = []
    for m in machines:
        live = by_name.get(str(m["worker_name"]).lower())
        enriched.append(
            {
                **m,
                "online": bool(live and live.get("online")),
                "live": live,
            }
        )
    return {
        "ok": fetched.get("ok", False),
        "scheduler_error": fetched.get("error") or "",
        "scheduler_url": cfg.scheduler_url,
        "capacity_note": summary.get("capacity_note")
        or (
            "v1 contributes compute to JOBS (GPU/CPU). RAM/SSD are capacity advertisements "
            "for future constraints — not a distributed filesystem yet."
        ),
        "summary": {
            "workers_online": summary.get("workers_online", 0),
            "workers_total": summary.get("workers_total", 0),
            "free_vram_mb": summary.get("free_vram_mb", 0),
            "total_vram_mb": summary.get("total_vram_mb", 0),
            "cpu_cores": summary.get("cpu_cores", 0),
            "ram_available_mb": summary.get("ram_available_mb", 0),
            "disk_free_mb": summary.get("disk_free_mb", 0),
            "gpus": summary.get("gpus") or [],
            "jobs": jobs,
        },
        "workers": workers,
        "machines": enriched,
    }


@app.get("/api/machines")
async def api_machines(request: Request) -> dict[str, Any]:
    user = await _require_user(request)
    rows = await _store().list_machines(user["id"])
    return {"ok": True, "machines": rows}


@app.post("/api/jobs")
async def api_jobs_submit(body: JobSubmitBody, request: Request) -> dict[str, Any]:
    """Proxy allowlisted job submit to the scheduler (Utilize panel)."""
    user = await _require_user(request)
    job_type = (body.job_type or "").strip()
    if job_type not in UTILIZE_JOB_TYPES:
        raise HTTPException(
            400,
            f"job_type not allowlisted for v1. Allowed: {sorted(UTILIZE_JOB_TYPES)}",
        )
    payload = dict(body.payload or {})
    if job_type == "pytorch_cuda_probe":
        size = body.matrix_size if body.matrix_size is not None else int(
            payload.get("matrix_size") or payload.get("size") or 512
        )
        payload["size"] = size
        payload["matrix_size"] = size
    require_gpu = body.require_gpu
    if require_gpu is None:
        require_gpu = job_type == "pytorch_cuda_probe"
    if job_type == "pytorch_cuda_probe":
        require_gpu = True
    submitted_by = f"portal:{user.get('display_name') or user.get('id')}"
    job = await _scheduler_request(
        "POST",
        "/jobs",
        json_body={
            "job_type": job_type,
            "payload": payload,
            "require_gpu": require_gpu,
            "min_vram_mb": body.min_vram_mb,
            "submitted_by": submitted_by,
        },
    )
    return {"ok": True, "job": job}


@app.get("/api/jobs/{job_id}")
async def api_jobs_get(job_id: str, request: Request) -> dict[str, Any]:
    await _require_user(request)
    job = await _scheduler_request("GET", f"/jobs/{job_id}")
    return {"ok": True, "job": job}


@app.post("/api/machines")
async def api_machines_create(body: MachineBody, request: Request) -> dict[str, Any]:
    user = await _require_user(request)
    sched = (body.scheduler_url or cfg.scheduler_url).rstrip("/")
    machine = await _store().create_machine(
        user["id"],
        {
            "worker_name": body.worker_name.strip(),
            "scheduler_url": sched,
            "max_vram_mb": body.max_vram_mb,
            "max_cpu_percent": body.max_cpu_percent,
            "dedicated_ram_mb": body.dedicated_ram_mb,
            "dedicated_disk_mb": body.dedicated_disk_mb,
            "dedicated_cpu_cores": body.dedicated_cpu_cores,
            "notes": _encode_machine_notes(body),
        },
    )
    portal_base = _public_base(request)
    instructions = _worker_instructions(machine, portal_base)
    return {"ok": True, "machine": machine, "instructions": instructions}


@app.patch("/api/machines/{machine_id}")
async def api_machines_patch(
    machine_id: str, body: MachineCapsPatch, request: Request
) -> dict[str, Any]:
    """Update offer caps for a machine owned by the logged-in user only.

    Cross-user PATCH → 403. Unknown id → 404.
    Regenerates start-token launch instructions for *this* owner (token unchanged).
    """
    user = await _require_user(request)
    existing = await _store().get_machine(machine_id)
    if not existing:
        raise HTTPException(404, "machine not found")
    if str(existing.get("user_id") or "") != str(user["id"]):
        raise HTTPException(
            403,
            "forbidden: only you can change how much of your PC is offered",
        )
    try:
        machine = await _store().update_machine_caps(
            machine_id,
            user["id"],
            body.model_dump(exclude_unset=True),
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    if not machine:
        raise HTTPException(404, "machine not found")
    portal_base = _public_base(request)
    instructions = _worker_instructions(machine, portal_base)
    return {
        "ok": True,
        "machine": machine,
        "instructions": instructions,
        "ownership": (
            "Only you control how much of your PC is offered. "
            "Change anytime on your machine or in your Contribute settings."
        ),
    }


@app.get("/api/worker-bootstrap/{token}")
async def api_worker_bootstrap(token: str) -> dict[str, Any]:
    machine = await _store().bootstrap_token(token)
    if not machine:
        raise HTTPException(404, "unknown or expired start token")
    return {
        "ok": True,
        "scheduler_url": machine["scheduler_url"],
        "worker_name": machine["worker_name"],
        "discord_user": machine.get("discord_user") or machine.get("contributor_name") or "",
        "contributor_name": machine.get("contributor_name") or "",
        "max_vram_mb": machine["max_vram_mb"],
        "max_cpu_percent": machine["max_cpu_percent"],
        "max_ram_mb": machine["dedicated_ram_mb"],
        "max_disk_mb": machine["dedicated_disk_mb"],
        "dedicated_ram_mb": machine["dedicated_ram_mb"],
        "dedicated_disk_mb": machine["dedicated_disk_mb"],
        "dedicated_cpu_cores": machine["dedicated_cpu_cores"],
        **_availability_env_from_machine(machine),
    }


_DIAGNOSTICS_MAX_BYTES = 200_000
_DIAGNOSTICS_KEEP = 200


def _diagnostics_dir() -> Any:
    from pathlib import Path

    from gpu_swarm.paths import ROOT

    d = Path(ROOT) / "data" / "diagnostics"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _redact_diag_text(text: str) -> str:
    try:
        from gpu_swarm.diagnostics import redact_secrets

        return redact_secrets(text or "")
    except Exception:  # noqa: BLE001
        return text or ""


@app.get("/api/chat")
async def api_chat_list(
    request: Request, since_id: int = 0, limit: int = 80
) -> dict[str, Any]:
    """Pool room chat for authenticated portal users. Empty list when no messages."""
    await _require_user(request)
    messages = await _store().list_chat_messages(since_id=since_id, limit=limit)
    return {"ok": True, "messages": messages, "room": "pool"}


@app.post("/api/chat")
async def api_chat_post(body: ChatPostBody, request: Request) -> dict[str, Any]:
    user = await _require_user(request)
    try:
        msg = await _store().add_chat_message(
            user["id"],
            user.get("display_name") or "member",
            body.text,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "message": msg}


@app.get("/api/presence")
async def api_presence(request: Request) -> dict[str, Any]:
    """Recently active portal users (for the hub presence rail)."""
    await _require_user(request)
    users = await _store().list_recent_users(within_sec=300)
    return {"ok": True, "users": users, "window_sec": 300}


@app.get("/api/suggestions")
async def api_suggestions_list(
    request: Request, status: str = "", limit: int = 100
) -> dict[str, Any]:
    """Review inbox — authenticated members can read pool suggestions."""
    await _require_user(request)
    st = (status or "").strip().lower() or None
    items = await _store().list_suggestions(status=st, limit=limit)
    return {"ok": True, "items": items, "count": len(items)}


@app.post("/api/suggestions")
async def api_suggestions_post(
    body: SuggestionPostBody, request: Request
) -> dict[str, Any]:
    user = await _require_user(request)
    try:
        item = await _store().add_suggestion(
            user["id"],
            user.get("display_name") or "member",
            body.body,
            body.category,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "item": item}


@app.patch("/api/suggestions/{suggestion_id}")
async def api_suggestions_patch(
    suggestion_id: str, body: SuggestionStatusBody, request: Request
) -> dict[str, Any]:
    """Mark a suggestion open / read / done (friend co-op review inbox)."""
    await _require_user(request)
    try:
        item = await _store().set_suggestion_status(suggestion_id, body.status)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not item:
        raise HTTPException(404, "suggestion not found")
    return {"ok": True, "item": item}


@app.get("/api/workspace")
async def api_workspace() -> dict[str, Any]:
    """Optional agent-vms slot — real path probe, not GPU passthrough."""
    from gpu_swarm.joiner_settings import agent_vms_present

    info = agent_vms_present()
    return {
        "ok": True,
        "workspace": {
            **info,
            "title": "Workspace (agent-vms)",
            "status": "ready" if info.get("ready") else "slot",
            "honesty": (
                "Linux desktop workspaces via VirtualBox + Vagrant (Hermes / agent-vm). "
                "Not NVIDIA GPU passthrough — contribute compute with the host worker."
            ),
            "docs": "ADVANCED_VM.md",
            "control": "Hermes owns VMs — GPU Pool only detects / links this slot.",
        },
    }


@app.post("/api/diagnostics")
async def api_diagnostics_submit(body: DiagnosticsBody, request: Request) -> dict[str, Any]:
    """
    Accept friend install/join diagnostic logs (size-capped, secrets redacted).
    Auth: existing portal session cookie OR invite_code / pool_password (same as login).
    """
    import re
    import time
    import uuid
    from pathlib import Path

    user = await _current_user(request)
    auth_method = "session" if user else ""
    if not user:
        ok, method = _auth_ok(body.pool_password, body.invite_code)
        if not ok:
            raise HTTPException(401, "login or invite_code required to submit diagnostics")
        auth_method = method
        name = (body.display_name or body.hostname or "anonymous").strip()[:64]
        if name:
            user = await _store().upsert_user(name, f"diagnostics:{method}")
        else:
            user = {"id": "", "display_name": "anonymous"}

    raw = body.log_text or ""
    if not raw.strip():
        raise HTTPException(400, "log_text required")
    text = _redact_diag_text(raw)
    encoded = text.encode("utf-8")
    if len(encoded) > _DIAGNOSTICS_MAX_BYTES:
        text = encoded[:_DIAGNOSTICS_MAX_BYTES].decode("utf-8", errors="ignore") + "\n\n[truncated]\n"

    diag_dir = _diagnostics_dir()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe_host = re.sub(r"[^a-zA-Z0-9_.-]+", "-", (body.hostname or "host"))[:48].strip("-") or "host"
    diag_id = uuid.uuid4().hex[:12]
    path = Path(diag_dir) / f"{stamp}-{safe_host}-{diag_id}.log"
    meta = {
        "id": diag_id,
        "created_at": time.time(),
        "user_id": (user or {}).get("id") or "",
        "display_name": (user or {}).get("display_name") or body.display_name or "",
        "hostname": body.hostname or "",
        "wizard_step": body.wizard_step or "",
        "client_log_path": body.log_path or "",
        "auth_method": auth_method,
        "bytes": len(text.encode("utf-8")),
        "client_time": body.client_time,
    }
    path.write_text(text, encoding="utf-8")
    path.with_suffix(".json").write_text(
        __import__("json").dumps(meta, indent=2) + "\n",
        encoding="utf-8",
    )

    # Cap retention: keep newest N log files.
    logs = sorted(Path(diag_dir).glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in logs[_DIAGNOSTICS_KEEP:]:
        try:
            old.unlink(missing_ok=True)
            old.with_suffix(".json").unlink(missing_ok=True)
        except OSError:
            pass

    return {
        "ok": True,
        "id": diag_id,
        "message": f"Diagnostics stored ({meta['bytes']} bytes). The host can review in data/diagnostics/.",
        "bytes": meta["bytes"],
    }


@app.get("/api/diagnostics")
async def api_diagnostics_list(request: Request, limit: int = 50) -> dict[str, Any]:
    """Simple admin list of uploaded diagnostics (requires portal session)."""
    import json
    from pathlib import Path

    await _require_user(request)
    diag_dir = Path(_diagnostics_dir())
    items: list[dict[str, Any]] = []
    for meta_path in sorted(diag_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if len(items) >= max(1, min(limit, 200)):
            break
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {"id": meta_path.stem, "error": "unreadable"}
        meta["file"] = str(meta_path.with_suffix(".log").name)
        items.append(meta)
    return {"ok": True, "count": len(items), "items": items}


def _encode_machine_notes(body: MachineBody) -> str | None:
    import json

    from gpu_swarm.availability_schedule import AvailabilityConfig, apply_preset, config_to_settings_fields

    preset = (body.availability_preset or "always").strip().lower()
    if preset == "custom":
        cfg = AvailabilityConfig(
            mode="daily",
            daily_start=body.availability_daily_start or "22:00",
            daily_end=body.availability_daily_end or "08:00",
        )
    else:
        cfg = apply_preset(preset)
    payload: dict[str, Any] = {
        "availability_preset": preset,
        "availability": config_to_settings_fields(cfg),
    }
    if body.notes:
        payload["text"] = body.notes
    if preset == "always" and not body.notes:
        return body.notes
    return json.dumps(payload)


def _parse_machine_notes(notes: str | None) -> dict[str, Any]:
    import json

    if not notes:
        return {}
    try:
        parsed = json.loads(notes)
        return parsed if isinstance(parsed, dict) else {"text": notes}
    except json.JSONDecodeError:
        return {"text": notes}


def _availability_env_from_machine(machine: dict[str, Any]) -> dict[str, str]:
    from gpu_swarm.availability_schedule import AvailabilityConfig, to_env_dict

    meta = _parse_machine_notes(machine.get("notes"))
    avail = meta.get("availability") or {}
    cfg = AvailabilityConfig(
        mode=str(avail.get("availability_mode") or "always"),
        daily_start=str(avail.get("availability_daily_start") or "22:00"),
        daily_end=str(avail.get("availability_daily_end") or "08:00"),
        until_ts=float(avail.get("availability_until") or 0),
    )
    return to_env_dict(cfg)


def _worker_instructions(machine: dict[str, Any], portal_base: str) -> dict[str, Any]:
    token = machine["start_token"]
    sched = machine["scheduler_url"]
    name = machine["worker_name"]
    from gpu_swarm.availability_schedule import AvailabilityConfig, to_env_dict

    sched_cfg = AvailabilityConfig(
        mode=str(machine.get("availability_mode") or "always"),
        daily_start=str(machine.get("availability_daily_start") or "22:00"),
        daily_end=str(machine.get("availability_daily_end") or "08:00"),
        until_ts=float(machine.get("availability_until") or 0),
    ).normalized()
    sched_env = to_env_dict(sched_cfg)
    bat = (
        f"set GPU_SWARM_PORTAL_URL={portal_base}\r\n"
        f"set GPU_SWARM_START_TOKEN={token}\r\n"
        f"set GPU_SWARM_SCHEDULER_URL={sched}\r\n"
        f"python -m gpu_swarm worker --name {name} --start-token %GPU_SWARM_START_TOKEN% "
        f"--portal-url %GPU_SWARM_PORTAL_URL%\r\n"
    )
    bash = (
        f"export GPU_SWARM_PORTAL_URL={portal_base}\n"
        f"export GPU_SWARM_START_TOKEN={token}\n"
        f"export GPU_SWARM_SCHEDULER_URL={sched}\n"
        f"python -m gpu_swarm worker --name {name} "
        f"--start-token \"$GPU_SWARM_START_TOKEN\" --portal-url \"$GPU_SWARM_PORTAL_URL\"\n"
    )
    env_direct = (
        f"GPU_SWARM_SCHEDULER_URL={sched}\n"
        f"GPU_SWARM_WORKER_NAME={name}\n"
        f"GPU_SWARM_MAX_VRAM_MB={machine['max_vram_mb']}\n"
        f"GPU_SWARM_MAX_CPU_PERCENT={machine['max_cpu_percent']}\n"
        f"GPU_SWARM_MAX_RAM_MB={machine['dedicated_ram_mb']}\n"
        f"GPU_SWARM_MAX_DISK_MB={machine['dedicated_disk_mb']}\n"
        f"GPU_SWARM_DEDICATED_CPU_CORES={machine['dedicated_cpu_cores']}\n"
        f"GPU_SWARM_CONTRIBUTOR_NAME={machine.get('contributor_name') or ''}\n"
        f"GPU_SWARM_HOST_PROTECT=1\n"
    )
    for key, val in _availability_env_from_machine(machine).items():
        if val:
            env_direct += f"{key}={val}\n"
    return {
        "start_token": token,
        "portal_url": portal_base,
        "windows_cmd": bat,
        "bash": bash,
        "env_direct": env_direct,
        "one_liner": (
            f'python -m gpu_swarm worker --name {name} '
            f'--start-token {token} --portal-url {portal_base}'
        ),
        "note": (
            "The start token loads YOUR dedication caps from the portal, then the worker "
            "heartbeats real GPU/CPU inventory to the scheduler. Only you control how much "
            "of your PC is offered — pool admins cannot remotely raise another contributor's caps. "
            "Desktop app users save the same caps locally in joiner settings. "
            "Host GPU safety (GPU_SWARM_HOST_PROTECT=1) stays ON by default: offer ≤~55% VRAM, "
            "pause jobs when util is high / free VRAM is low so your desktop cannot freeze."
        ),
    }


def run_portal(host: str | None = None, port: int | None = None) -> None:
    import uvicorn

    c = portal_config()
    uvicorn.run(
        "gpu_swarm.portal:app",
        host=host or c.host,
        port=port or c.port,
        reload=False,
        log_level="info",
    )

def _load_portal_html() -> str:
    """Prefer external hub template; fall back to a tiny stub if missing."""
    from pathlib import Path

    path = Path(__file__).with_name("portal_hub.html")
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return (
        "<!DOCTYPE html><html><body style='font-family:sans-serif;background:#111;color:#eee;"
        "padding:2rem'><h1>GPU Pool</h1><p>portal_hub.html missing beside portal.py</p>"
        "</body></html>"
    )


PORTAL_HTML = _load_portal_html()

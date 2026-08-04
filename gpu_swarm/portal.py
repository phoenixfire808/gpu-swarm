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
    return HTMLResponse(PORTAL_HTML)


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
    return {
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
            "Jobs run on online GPU workers (e.g. Drew-Home)."
        ),
        "allowed_job_types": sorted(UTILIZE_JOB_TYPES),
        "utilize_note": (
            "No GPU on your laptop? Fine. Allowlisted jobs: probe, pytorch_cuda_probe, llm_chat. "
            "For AI apps, start the Local Pool Endpoint on your machine "
            "(OPENAI_BASE_URL=http://127.0.0.1:8080/v1). See LOCAL_MODEL.md."
        ),
        "invite_code_hint": PORTAL_INVITE_CODE,
        "public_endpoints": pub,
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
            "discord_primary": "Glitch Factor",
            "discord_bot": "GPU Pool",
            "discord_commands": [
                "/pool", "/workers", "/contribute",
                "/submit_probe", "/submit_compute", "/job_status",
            ],
            "docs": "CONNECTING.md · LOCAL_MODEL.md · FRIEND_LAPTOP.md",
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
                    "Drew (or any GPU contributor): install Ollama, pull a model, "
                    "keep ollama serve on :11434, restart the GPU Pool worker "
                    "so llm_ready=yes. See LOCAL_MODEL.md."
                ),
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
                "Private by default (Tailscale/LAN). When Drew publishes a public tunnel, "
                "use the Public URLs — no Tailscale needed."
            ),
            "friends_connect": [
                "Run the GPU Pool EXE (auto-detects scheduler) OR open the portal URL Drew shares",
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
            "notes": body.notes,
        },
    )
    portal_base = _public_base(request)
    instructions = _worker_instructions(machine, portal_base)
    return {"ok": True, "machine": machine, "instructions": instructions}


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
        "message": f"Diagnostics stored ({meta['bytes']} bytes). Drew can review in data/diagnostics/.",
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


def _worker_instructions(machine: dict[str, Any], portal_base: str) -> dict[str, Any]:
    token = machine["start_token"]
    sched = machine["scheduler_url"]
    name = machine["worker_name"]
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
    )
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
            "The start token loads your dedication caps from the portal, then the worker "
            "heartbeats real GPU/CPU inventory to the scheduler. Desktop app users can paste "
            "the same scheduler URL + caps into the joiner."
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


PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>GPU Pool — Contribute · Utilize · Connect</title>
<style>
  /* No external @import — Google Fonts blocked/slow caused blank/black portal for some friends */
  :root {
    --bg0: #0f1412;
    --bg1: #17201c;
    --bg2: #1f2b25;
    --ink: #e8f0ea;
    --muted: #9bb0a3;
    --line: #2d3d34;
    --accent: #d4a24c;
    --accent2: #3d9b7a;
    --ok: #6fbf8a;
    --font: "Segoe UI", "Helvetica Neue", ui-sans-serif, sans-serif;
    --mono: Consolas, "Cascadia Mono", ui-monospace, monospace;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    font-family: var(--font);
    color: var(--ink);
    background:
      radial-gradient(1200px 600px at 10% -10%, #24352c 0%, transparent 55%),
      radial-gradient(900px 500px at 100% 0%, #2a2418 0%, transparent 50%),
      var(--bg0);
  }
  .wrap { max-width: 1040px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
  header { margin-bottom: 1.5rem; }
  .brand {
    font-size: clamp(1.8rem, 4vw, 2.6rem);
    font-weight: 600;
    letter-spacing: -0.03em;
    margin: 0 0 0.35rem;
  }
  .brand span { color: var(--accent); }
  .lede { color: var(--muted); max-width: 44rem; line-height: 1.5; margin: 0; }
  .note {
    margin: 1rem 0 0;
    padding: 0.75rem 0.9rem;
    border-left: 3px solid var(--accent);
    background: rgba(212,162,76,0.08);
    color: #e6d3a8;
    font-size: 0.92rem;
    line-height: 1.45;
  }
  .panel {
    background: linear-gradient(180deg, var(--bg1), var(--bg2));
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1.25rem 1.35rem;
    margin-top: 1.1rem;
  }
  h2 { margin: 0 0 0.85rem; font-size: 1.15rem; font-weight: 600; }
  h3 { margin: 1.1rem 0 0.45rem; font-size: 0.95rem; font-weight: 600; color: var(--accent); }
  label { display: block; font-size: 0.85rem; color: var(--muted); margin: 0.65rem 0 0.3rem; }
  input[type="text"], input[type="password"], input[type="number"], select {
    width: 100%;
    padding: 0.55rem 0.7rem;
    border-radius: 8px;
    border: 1px solid var(--line);
    background: #0c110f;
    color: var(--ink);
    font: inherit;
  }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
  @media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
  .slider-row { display: grid; grid-template-columns: 1fr auto; gap: 0.6rem; align-items: center; }
  input[type="range"] { width: 100%; accent-color: var(--accent2); }
  .val { font-family: var(--mono); font-size: 0.85rem; color: var(--accent); min-width: 4.5rem; text-align: right; }
  .actions { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 1rem; }
  button, .btn {
    border: 0;
    border-radius: 8px;
    padding: 0.55rem 0.95rem;
    font: inherit;
    font-weight: 500;
    cursor: pointer;
    background: var(--accent2);
    color: #04120c;
  }
  button.secondary { background: transparent; color: var(--ink); border: 1px solid var(--line); }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.55rem;
  }
  .stat {
    background: rgba(0,0,0,0.22);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 0.6rem 0.7rem;
  }
  .stat b { display: block; font-family: var(--mono); font-size: 1.05rem; }
  .stat span { color: var(--muted); font-size: 0.74rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
  th, td { text-align: left; padding: 0.55rem 0.4rem; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { color: var(--muted); font-weight: 500; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }
  .pill {
    display: inline-block;
    padding: 0.12rem 0.45rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-family: var(--mono);
  }
  .pill.on { background: rgba(111,191,138,0.18); color: var(--ok); }
  .pill.off { background: rgba(196,92,74,0.18); color: #e39a90; }
  .pill.queued { background: rgba(212,162,76,0.18); color: var(--accent); }
  .pill.running { background: rgba(61,155,122,0.22); color: #8fd4ba; }
  .pill.completed { background: rgba(111,191,138,0.18); color: var(--ok); }
  .pill.failed { background: rgba(196,92,74,0.18); color: #e39a90; }
  pre {
    margin: 0.5rem 0 0;
    padding: 0.75rem;
    background: #0a0e0c;
    border: 1px solid var(--line);
    border-radius: 8px;
    overflow: auto;
    font-family: var(--mono);
    font-size: 0.78rem;
    line-height: 1.45;
    white-space: pre-wrap;
  }
  .hidden { display: none !important; }
  .err { color: #f0a399; font-size: 0.9rem; margin-top: 0.5rem; }
  .topbar { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; }
  .who { color: var(--muted); font-size: 0.9rem; }
  .nav {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin-top: 0.9rem;
    padding: 0.35rem;
    background: rgba(0,0,0,0.25);
    border: 1px solid var(--line);
    border-radius: 10px;
  }
  .nav button {
    background: transparent;
    color: var(--muted);
    border: 1px solid transparent;
    flex: 1;
    min-width: 6.5rem;
  }
  .nav button.active {
    background: rgba(61,155,122,0.18);
    color: var(--ink);
    border-color: var(--accent2);
  }
  .job-meta { font-family: var(--mono); font-size: 0.85rem; color: var(--muted); margin-top: 0.65rem; }
  .chooser {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.85rem;
    margin-top: 1rem;
  }
  @media (max-width: 860px) { .chooser { grid-template-columns: 1fr; } }
  .choice {
    text-align: left;
    background: linear-gradient(165deg, #1c2922 0%, #141c18 100%);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 1.25rem 1.2rem 1.15rem;
    color: var(--ink);
    min-height: 11.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
    transition: border-color 0.15s ease, transform 0.15s ease;
  }
  .choice:hover { border-color: var(--accent2); transform: translateY(-2px); }
  .choice .eyebrow {
    font-family: var(--mono);
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
  }
  .choice .title {
    font-size: 1.45rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    margin: 0;
  }
  .choice .blurb {
    color: var(--muted);
    font-size: 0.92rem;
    line-height: 1.45;
    flex: 1;
    margin: 0;
  }
  .choice .go {
    font-family: var(--mono);
    font-size: 0.8rem;
    color: var(--accent2);
  }
  .url-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.65rem;
  }
  @media (max-width: 720px) { .url-grid { grid-template-columns: 1fr; } }
  .url-card {
    background: rgba(0,0,0,0.22);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 0.75rem 0.85rem;
  }
  .url-card span { display: block; color: var(--muted); font-size: 0.75rem; margin-bottom: 0.25rem; }
  .url-card code { font-family: var(--mono); font-size: 0.82rem; word-break: break-all; }
  .cmd-list { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }
  .cmd-list code {
    font-family: var(--mono);
    font-size: 0.8rem;
    padding: 0.28rem 0.5rem;
    border-radius: 6px;
    background: rgba(0,0,0,0.35);
    border: 1px solid var(--line);
  }
  .workers-wrap { margin-top: 1rem; overflow: auto; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1 class="brand">GPU <span>Pool</span></h1>
    <p class="lede">Private Tailscale/LAN co-op — pick <strong>Contribute</strong>, <strong>Utilize</strong>, or <strong>Connect</strong> (how friends reach the pool from Discord / code / CLI).</p>
    <p class="note" id="laptopNote">No NVIDIA? You can still <strong>Utilize</strong> the pool or contribute <strong>CPU</strong>.</p>
    <p class="note" id="capacityNote">v1 contributes compute to JOBS (GPU/CPU). RAM/SSD figures are capacity advertisements — not a distributed filesystem yet.</p>
    <p class="note" id="networkNote" style="border-left-color:var(--accent2);background:rgba(61,155,122,0.08);color:#b8dcc9">Private Tailscale/LAN pool — not exposed to the open internet. Friends join via Tailscale, then open this portal.</p>
  </header>

  <section id="loginPanel" class="panel">
    <h2>Sign in</h2>
    <p class="lede" style="margin-bottom:0.5rem">MVP auth: invite code <code>glitch-factor</code> (or pool password) + display name. Public link or Tailscale both work. Real OAuth comes later.</p>
    <label for="displayName">Display name</label>
    <input id="displayName" type="text" placeholder="YourDiscordName" autocomplete="nickname" />
    <div class="row">
      <div>
        <label for="poolPassword">Pool password</label>
        <input id="poolPassword" type="password" placeholder="shared pool password" autocomplete="current-password" />
      </div>
      <div>
        <label for="inviteCode">Invite code</label>
        <input id="inviteCode" type="text" placeholder="optional invite" autocomplete="off" />
      </div>
    </div>
    <div class="actions">
      <button id="loginBtn" type="button">Enter portal</button>
    </div>
    <div class="err hidden" id="loginErr"></div>
  </section>

  <section id="appPanel" class="hidden">
    <div class="topbar panel" style="margin-top:0">
      <div class="who">Signed in as <strong id="who"></strong></div>
      <button class="secondary" id="logoutBtn" type="button">Log out</button>
    </div>

    <nav class="nav" aria-label="Portal sections">
      <button type="button" class="active" data-view="home" id="navHome">Home</button>
      <button type="button" data-view="contribute" id="navContribute">Contribute</button>
      <button type="button" data-view="utilize" id="navUtilize">Utilize</button>
      <button type="button" data-view="connect" id="navConnect">Connect</button>
    </nav>

    <div id="viewHome">
      <div class="panel">
        <h2>What do you want to do?</h2>
        <p class="lede">Three clear paths — same private pool.</p>
        <div class="chooser">
          <button type="button" class="choice" data-go="contribute" id="cardContribute">
            <span class="eyebrow">Path 1</span>
            <p class="title">Contribute</p>
            <p class="blurb">Plug in spare GPU/CPU. Set soft caps, get a start token, and join as a worker.</p>
            <span class="go">Register machine →</span>
          </button>
          <button type="button" class="choice" data-go="utilize" id="cardUtilize">
            <span class="eyebrow">Path 2</span>
            <p class="title">Utilize</p>
            <p class="blurb">Run an allowlisted job on the pool — probe or CUDA matmul — and watch status + result.</p>
            <span class="go">Submit a job →</span>
          </button>
          <button type="button" class="choice" data-go="connect" id="cardConnect">
            <span class="eyebrow">Path 3</span>
            <p class="title">Connect</p>
            <p class="blurb">How-to: public HTTPS (no Tailscale) or Tailscale URLs, Discord, Python / CLI.</p>
            <span class="go">See how to connect →</span>
          </button>
        </div>
      </div>

      <div class="panel" id="friendsHomeCard">
        <h2>How friends connect</h2>
        <p class="lede" id="friendsHomeLede">Public HTTPS when the tunnel is on — no Tailscale needed. Invite still required.</p>
        <ol id="friendsHomeSteps" style="margin:0.5rem 0 0; padding-left:1.2rem; color:var(--muted); line-height:1.55"></ol>
        <div class="actions">
          <button type="button" data-go="connect">Full Connect guide →</button>
          <button class="secondary" type="button" data-go="contribute">Contribute</button>
          <button class="secondary" type="button" data-go="utilize">Utilize</button>
        </div>
      </div>

      <div class="panel">
        <h2>Live pool capacity</h2>
        <p class="lede" style="margin-bottom:0.85rem">From scheduler <code>/status</code>.</p>
        <div class="stats" id="stats"></div>
        <p class="err hidden" id="dashErr" style="margin-top:0.75rem"></p>
        <div class="actions">
          <button class="secondary" id="refreshBtn" type="button">Refresh</button>
        </div>
        <div class="workers-wrap">
          <table>
            <thead>
              <tr>
                <th>Worker</th>
                <th>Status</th>
                <th>GPUs / VRAM</th>
                <th>CPU</th>
                <th>RAM ad</th>
                <th>Disk ad</th>
              </tr>
            </thead>
            <tbody id="workerRows"></tbody>
          </table>
        </div>
      </div>
    </div>

    <div id="viewUtilize" class="hidden">
      <div class="panel">
        <h2>Utilize the pool</h2>
        <p class="note" id="utilizeNote" style="margin-top:0">v1: allowlisted jobs only — <code>probe</code> and <code>pytorch_cuda_probe</code>. No arbitrary shell.</p>
        <label for="jobType">Job type</label>
        <select id="jobType">
          <option value="probe">probe — live GPU inventory</option>
          <option value="pytorch_cuda_probe">pytorch_cuda_probe — CUDA matmul</option>
        </select>
        <div id="cudaOpts" class="hidden">
          <label for="matrixSize">Matrix size (pytorch_cuda_probe)</label>
          <input id="matrixSize" type="number" min="16" max="4096" step="16" value="512" />
        </div>
        <div class="actions">
          <button id="submitJobBtn" type="button">Submit job</button>
          <button class="secondary" id="pollJobBtn" type="button" disabled>Refresh status</button>
          <button class="secondary" type="button" data-go="home">Back to Home</button>
        </div>
        <div class="err hidden" id="jobErr"></div>
        <div id="jobBox" class="hidden">
          <p class="job-meta">Job <strong id="jobId"></strong> · <span class="pill" id="jobStatusPill">—</span></p>
          <p class="lede" style="margin-top:0.5rem">Result / error</p>
          <pre id="jobResult">—</pre>
        </div>
      </div>
    </div>

    <div id="viewContribute" class="hidden">
      <div class="panel">
        <h2>Contribute — register this machine</h2>
        <p class="lede">Set dedication caps, then copy a start-token command. The worker reports real nvidia-smi / host inventory — nothing mocked.</p>
        <label for="workerName">Worker name</label>
        <input id="workerName" type="text" placeholder="My-PC-gpu" />
        <label for="schedulerUrl">Scheduler URL</label>
        <input id="schedulerUrl" type="text" />

        <label>GPU VRAM soft cap (MB) — 0 = use free VRAM</label>
        <div class="slider-row">
          <input id="vram" type="range" min="0" max="24576" step="256" value="0" />
          <span class="val" id="vramVal">0</span>
        </div>
        <label>CPU percent available for jobs</label>
        <div class="slider-row">
          <input id="cpuPct" type="range" min="5" max="100" step="5" value="50" />
          <span class="val" id="cpuPctVal">50%</span>
        </div>
        <label>CPU cores to advertise (0 = detect)</label>
        <div class="slider-row">
          <input id="cpuCores" type="range" min="0" max="64" step="1" value="0" />
          <span class="val" id="cpuCoresVal">0</span>
        </div>
        <label>RAM to advertise (MB) — capacity ad, not shared memory</label>
        <div class="slider-row">
          <input id="ram" type="range" min="0" max="65536" step="512" value="0" />
          <span class="val" id="ramVal">0</span>
        </div>
        <label>SSD / disk for jobs (MB) — capacity ad, not a DFS yet</label>
        <div class="slider-row">
          <input id="disk" type="range" min="0" max="524288" step="1024" value="0" />
          <span class="val" id="diskVal">0</span>
        </div>

        <div class="actions">
          <button id="registerBtn" type="button">Create start token</button>
          <button class="secondary" type="button" data-go="home">Back to Home</button>
        </div>
        <div class="err hidden" id="regErr"></div>
        <div id="instrBox" class="hidden" style="margin-top:1rem">
          <h2>Run worker</h2>
          <p class="lede">Windows (cmd):</p>
          <pre id="instrWin"></pre>
          <p class="lede" style="margin-top:0.75rem">One-liner:</p>
          <pre id="instrOne"></pre>
          <p class="lede" style="margin-top:0.75rem">Or set env caps directly (no token):</p>
          <pre id="instrEnv"></pre>
        </div>
      </div>
    </div>

    <div id="viewConnect" class="hidden">
      <div class="panel">
        <h2>Connect — how to reach the pool</h2>
        <p class="lede" id="connectLede">Public HTTPS when the tunnel is on — no Tailscale needed. Invite code still required.</p>

        <div id="publicBanner" class="note hidden" style="border-left-color:var(--accent);background:rgba(232,168,74,0.12);color:#f0d9a8;margin-bottom:0.85rem">
          <strong>No Tailscale needed</strong> — public access is live. Share the portal URL + invite <code>glitch-factor</code>.
        </div>

        <h3>How friends connect</h3>
        <ol id="friendsConnectSteps" style="margin:0.4rem 0 0.85rem; padding-left:1.2rem; color:var(--muted); line-height:1.55"></ol>

        <h3 id="localModelTitle">Local model endpoint</h3>
        <p class="note" id="localModelHonesty" style="margin-top:0.35rem">Pool as a local AI API (OpenAI-compatible) — not a Windows GPU driver.</p>
        <pre id="localModelBlock">—</pre>
        <p class="lede" id="localModelHost" style="margin-top:0.5rem"></p>

        <h3>URLs</h3>
        <div class="url-grid">
          <div class="url-card" id="cardPortalPublic"><span>Portal (public — no Tailscale)</span><code id="urlPortalPublic">—</code></div>
          <div class="url-card" id="cardPoolApiPublic"><span>Pool API (public /pool-api proxy)</span><code id="urlPoolApiPublic">—</code></div>
          <div class="url-card"><span>Scheduler (Tailscale)</span><code id="urlSchedTs">—</code></div>
          <div class="url-card"><span>Scheduler (localhost on host)</span><code id="urlSchedLocal">—</code></div>
          <div class="url-card"><span>Portal (Tailscale)</span><code id="urlPortalTs">—</code></div>
          <div class="url-card"><span>Portal (this session)</span><code id="urlPortalThis">—</code></div>
        </div>

        <h3>Discord · <span id="discordGuild">Glitch Factor</span> · bot <span id="discordBot">GPU Pool</span></h3>
        <div class="cmd-list" id="discordCmds"></div>

        <h3>Env (public /pool-api or Tailscale)</h3>
        <pre id="connectEnv">—</pre>

        <h3>CLI</h3>
        <pre id="connectCli">—</pre>

        <h3>Python SDK</h3>
        <pre id="connectPy">—</pre>

        <h3>HTTP</h3>
        <pre id="connectHttp">—</pre>

        <h3>Rules</h3>
        <ul id="connectRules" style="margin:0.4rem 0 0; padding-left:1.2rem; color:var(--muted); line-height:1.5"></ul>

        <p class="lede" style="margin-top:1rem">Full guide: <code id="connectDocs">CONNECTING.md</code> in the repo. Invite code (safe to share): <code id="inviteHint">—</code></p>
        <div class="actions">
          <button class="secondary" type="button" data-go="home">Back to Home</button>
          <button type="button" data-go="utilize">Go Utilize</button>
          <button class="secondary" type="button" data-go="contribute">Go Contribute</button>
        </div>
      </div>
    </div>
  </section>
</div>
<script>
const $ = (id) => document.getElementById(id);
const bindSlider = (id, valId, fmt) => {
  const el = $(id), out = $(valId);
  if (!el || !out) return;
  const paint = () => { out.textContent = fmt(el.value); };
  el.addEventListener("input", paint); paint();
};
bindSlider("vram", "vramVal", v => `${v} MB`);
bindSlider("cpuPct", "cpuPctVal", v => `${v}%`);
bindSlider("cpuCores", "cpuCoresVal", v => v);
bindSlider("ram", "ramVal", v => `${v} MB`);
bindSlider("disk", "diskVal", v => `${v} MB`);

let currentJobId = null;
let jobPollTimer = null;
let portalConfig = null;

async function api(path, opts={}) {
  const r = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(opts.headers||{}) },
    ...opts,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const detail = data.detail;
    const msg = typeof detail === "string" ? detail
      : (Array.isArray(detail) ? detail.map(x => x.msg || JSON.stringify(x)).join("; ") : null);
    throw new Error(msg || data.message || r.statusText);
  }
  return data;
}

function show(loggedIn) {
  $("loginPanel").classList.toggle("hidden", loggedIn);
  $("appPanel").classList.toggle("hidden", !loggedIn);
}

function setView(name) {
  $("viewHome").classList.toggle("hidden", name !== "home");
  $("viewUtilize").classList.toggle("hidden", name !== "utilize");
  $("viewContribute").classList.toggle("hidden", name !== "contribute");
  $("viewConnect").classList.toggle("hidden", name !== "connect");
  document.querySelectorAll(".nav button").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.view === name);
  });
  if (name === "home") refreshDash();
}

function fmtMb(n) {
  n = Number(n||0);
  if (n >= 1024) return (n/1024).toFixed(1) + " GB";
  return n + " MB";
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function syncCudaOpts() {
  $("cudaOpts").classList.toggle("hidden", $("jobType").value !== "pytorch_cuda_probe");
}

function paintConnect(c) {
  const conn = (c && c.connect) || {};
  const friends = conn.friends_connect || [];
  const publicOn = !!(c.public_access || conn.no_tailscale_needed || conn.portal_public);
  const privateNet = conn.private_network
    || (publicOn
      ? "Public HTTPS access is ON — no Tailscale needed. Invite code still required."
      : "When Drew runs start-public-access.cmd, a public HTTPS portal appears (no Tailscale). Tailscale remains optional.");
  if ($("urlPortalPublic")) $("urlPortalPublic").textContent = conn.portal_public || "(tunnel off — Drew: start-public-access.cmd)";
  if ($("urlPoolApiPublic")) $("urlPoolApiPublic").textContent = conn.pool_api_public || "—";
  if ($("publicBanner")) $("publicBanner").classList.toggle("hidden", !publicOn);
  $("urlSchedTs").textContent = conn.scheduler_tailscale || "—";
  $("urlSchedLocal").textContent = conn.scheduler_local || "—";
  $("urlPortalTs").textContent = conn.portal_tailscale || "—";
  $("urlPortalThis").textContent = conn.portal_this || c.portal_url || "—";
  $("discordGuild").textContent = conn.discord_primary || "Glitch Factor";
  $("discordBot").textContent = conn.discord_bot || "GPU Pool";
  $("discordCmds").innerHTML = (conn.discord_commands || []).map(x => `<code>${escapeHtml(x)}</code>`).join("") || "—";
  $("connectEnv").textContent = conn.env_example || "—";
  $("connectCli").textContent = (conn.cli || []).join("\n") || "—";
  $("connectPy").textContent = conn.python_sdk || "—";
  $("connectHttp").textContent = (conn.http || []).join("\n") || "—";
  $("connectDocs").textContent = conn.docs || "CONNECTING.md";
  $("inviteHint").textContent = c.invite_code_hint || "glitch-factor";
  $("connectRules").innerHTML = (conn.rules || []).map(r => `<li>${escapeHtml(r)}</li>`).join("");
  if ($("connectLede")) $("connectLede").textContent = privateNet;
  if ($("networkNote")) $("networkNote").textContent = privateNet;
  if ($("friendsHomeLede")) $("friendsHomeLede").textContent = privateNet;
  const stepsHtml = friends.map(s => `<li>${escapeHtml(s)}</li>`).join("");
  if ($("friendsConnectSteps")) $("friendsConnectSteps").innerHTML = stepsHtml || "<li>Open public portal URL (or Tailscale) → invite → Contribute or Utilize</li>";
  if ($("friendsHomeSteps")) $("friendsHomeSteps").innerHTML = stepsHtml || "<li>Open public portal URL (or Tailscale) → invite → Contribute or Utilize</li>";
  const lm = conn.local_model || {};
  if ($("localModelTitle")) $("localModelTitle").textContent = lm.title || "Local model endpoint";
  if ($("localModelHonesty")) $("localModelHonesty").textContent = lm.honesty || "OpenAI-compatible localhost API → pool llm_chat jobs. Not a PCI GPU.";
  if ($("localModelBlock")) {
    $("localModelBlock").textContent = [
      lm.start || "python -m gpu_swarm local-endpoint",
      "URL:  " + (lm.url || "http://127.0.0.1:8080/v1"),
      "Env:  " + (lm.env || "OPENAI_BASE_URL=http://127.0.0.1:8080/v1"),
      "Apps: " + (lm.apps || "Open WebUI · LM Studio · Continue · Cursor"),
    ].join("\n");
  }
  if ($("localModelHost")) $("localModelHost").textContent = lm.host_worker || "";
}

async function loadConfig() {
  const c = await api("/api/config");
  portalConfig = c;
  // Prefer Tailscale scheduler for member contribute form when config points at localhost
  const conn = c.connect || {};
  const sched = (c.scheduler_url || "").includes("127.0.0.1")
    ? (conn.scheduler_tailscale || c.scheduler_url)
    : (c.scheduler_url || conn.scheduler_tailscale || "");
  $("schedulerUrl").value = sched || "";
  if (c.capacity_note) $("capacityNote").textContent = c.capacity_note;
  if (c.laptop_note && $("laptopNote")) $("laptopNote").textContent = c.laptop_note;
  if (c.utilize_note) $("utilizeNote").textContent = c.utilize_note;
  paintConnect(c);
}

async function refreshMe() {
  const me = await api("/api/me");
  if (me.ok) {
    $("who").textContent = me.user.display_name;
    show(true);
    setView("home");
  } else {
    show(false);
  }
}

async function refreshDash() {
  $("dashErr").classList.add("hidden");
  try {
    const d = await api("/api/dashboard");
    const s = d.summary || {};
    $("stats").innerHTML = [
      ["Online", (s.workers_online != null ? s.workers_online : 0)],
      ["Free VRAM", fmtMb(s.free_vram_mb)],
      ["Total VRAM", fmtMb(s.total_vram_mb)],
      ["CPU cores", (s.cpu_cores != null ? s.cpu_cores : 0)],
      ["RAM avail (ad)", fmtMb(s.ram_available_mb)],
      ["Disk free (ad)", fmtMb(s.disk_free_mb)],
      ["Jobs queued", (s.jobs&&s.jobs.queued)||0],
      ["Jobs running", (s.jobs&&s.jobs.running)||0],
      ["Jobs done", (s.jobs&&s.jobs.completed)||0],
    ].map(([k,v]) => `<div class="stat"><b>${v}</b><span>${k}</span></div>`).join("");
    if (!d.ok) {
      $("dashErr").textContent = "Cannot reach Tailscale/LAN scheduler yet (install/login Tailscale + join Drew’s tailnet): " + (d.scheduler_error||"");
      $("dashErr").classList.remove("hidden");
    }
    const rows = (d.workers||[]).map(w => {
      const gpus = (w.gpus||[]).map(g => g.name || "?").join(", ") || "—";
      const vram = `${fmtMb(w.free_vram_mb)} free / ${fmtMb(w.total_vram_mb)}`;
      const pill = w.online ? '<span class="pill on">online</span>' : '<span class="pill off">offline</span>';
      return `<tr>
        <td><strong>${escapeHtml(w.name||"?")}</strong><br><span style="color:var(--muted);font-size:0.8rem">${escapeHtml(w.host||"")}</span></td>
        <td>${pill}<br><span style="color:var(--muted);font-size:0.78rem">${escapeHtml(w.status||"")} · ${(w.heartbeat_age_sec != null ? w.heartbeat_age_sec : "?")}s</span></td>
        <td>${escapeHtml(gpus)}<br>${vram}</td>
        <td>${(w.cpu_cores != null ? w.cpu_cores : 0)} cores · ${(w.max_cpu_percent != null ? w.max_cpu_percent : "—")}%</td>
        <td>${fmtMb(w.ram_available_mb)} avail<br>cap ${fmtMb(w.max_ram_mb)}</td>
        <td>${fmtMb(w.disk_free_mb)} free<br>cap ${fmtMb(w.max_disk_mb)}</td>
      </tr>`;
    }).join("") || `<tr><td colspan="6" style="color:var(--muted)">No workers heartbeating yet.</td></tr>`;
    $("workerRows").innerHTML = rows;
  } catch (e) {
    $("dashErr").textContent = String(e.message||e);
    $("dashErr").classList.remove("hidden");
  }
}

function renderJob(job) {
  if (!job) return;
  currentJobId = job.id;
  $("jobBox").classList.remove("hidden");
  $("pollJobBtn").disabled = false;
  $("jobId").textContent = job.id || "—";
  const st = (job.status || "unknown").toLowerCase();
  const pill = $("jobStatusPill");
  pill.textContent = st;
  pill.className = "pill " + (["queued","running","completed","failed"].includes(st) ? st : "queued");
  const payload = job.result != null ? job.result : (job.error || null);
  $("jobResult").textContent = payload == null ? "(waiting…)" : JSON.stringify(payload, null, 2);
  if (st === "completed" || st === "failed") {
    if (jobPollTimer) { clearInterval(jobPollTimer); jobPollTimer = null; }
  }
}

async function pollJobOnce() {
  if (!currentJobId) return;
  $("jobErr").classList.add("hidden");
  try {
    const data = await api("/api/jobs/" + encodeURIComponent(currentJobId));
    renderJob(data.job);
  } catch (e) {
    $("jobErr").textContent = String(e.message||e);
    $("jobErr").classList.remove("hidden");
  }
}

function startJobPoll() {
  if (jobPollTimer) clearInterval(jobPollTimer);
  jobPollTimer = setInterval(pollJobOnce, 2000);
}

$("jobType").addEventListener("change", syncCudaOpts);
syncCudaOpts();

document.querySelectorAll(".nav button").forEach(btn => {
  btn.onclick = () => setView(btn.dataset.view);
});
document.querySelectorAll("[data-go]").forEach(el => {
  el.addEventListener("click", () => setView(el.dataset.go));
});

$("loginBtn").onclick = async () => {
  $("loginErr").classList.add("hidden");
  try {
    const data = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({
        display_name: $("displayName").value.trim(),
        pool_password: $("poolPassword").value,
        invite_code: $("inviteCode").value.trim(),
      }),
    });
    $("who").textContent = data.user.display_name;
    show(true);
    setView("home");
  } catch (e) {
    $("loginErr").textContent = String(e.message||e);
    $("loginErr").classList.remove("hidden");
  }
};

$("logoutBtn").onclick = async () => {
  await api("/api/logout", { method: "POST", body: "{}" });
  if (jobPollTimer) { clearInterval(jobPollTimer); jobPollTimer = null; }
  currentJobId = null;
  show(false);
};

$("refreshBtn").onclick = () => refreshDash();
$("pollJobBtn").onclick = () => pollJobOnce();

$("submitJobBtn").onclick = async () => {
  $("jobErr").classList.add("hidden");
  try {
    const job_type = $("jobType").value;
    const body = { job_type };
    if (job_type === "pytorch_cuda_probe") {
      body.matrix_size = Number($("matrixSize").value) || 512;
    }
    const data = await api("/api/jobs", { method: "POST", body: JSON.stringify(body) });
    renderJob(data.job);
    startJobPoll();
    await refreshDash();
  } catch (e) {
    $("jobErr").textContent = String(e.message||e);
    $("jobErr").classList.remove("hidden");
  }
};

$("registerBtn").onclick = async () => {
  $("regErr").classList.add("hidden");
  try {
    const data = await api("/api/machines", {
      method: "POST",
      body: JSON.stringify({
        worker_name: $("workerName").value.trim() || "browser-worker",
        scheduler_url: $("schedulerUrl").value.trim(),
        max_vram_mb: Number($("vram").value),
        max_cpu_percent: Number($("cpuPct").value),
        dedicated_ram_mb: Number($("ram").value),
        dedicated_disk_mb: Number($("disk").value),
        dedicated_cpu_cores: Number($("cpuCores").value),
      }),
    });
    const i = data.instructions;
    $("instrWin").textContent = i.windows_cmd;
    $("instrOne").textContent = i.one_liner;
    $("instrEnv").textContent = i.env_direct;
    $("instrBox").classList.remove("hidden");
  } catch (e) {
    $("regErr").textContent = String(e.message||e);
    $("regErr").classList.remove("hidden");
  }
};

loadConfig().then(refreshMe).catch(err => {
  $("loginErr").textContent = String(err.message||err);
  $("loginErr").classList.remove("hidden");
});
setInterval(() => {
  if (!$("appPanel").classList.contains("hidden") && !$("viewHome").classList.contains("hidden")) {
    refreshDash();
  }
}, 8000);
</script>
</body>
</html>
"""

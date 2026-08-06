"""Web portal — contribute machines + utilize allowlisted pool jobs."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from gpu_swarm import ALLOWED_JOB_TYPES
from gpu_swarm.config import PortalConfig, portal_config
from gpu_swarm.portal_store import PortalStore

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
    min_vram_mb: int = 0
    require_gpu: bool | None = None


class JobSubmitBody(BaseModel):
    job_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    require_gpu: bool | None = None
    min_vram_mb: int = 0
    matrix_size: int | None = Field(default=None, ge=16, le=4096)


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
    return {
        "status": "ok",
        "service": "portal",
        "scheduler_url": cfg.scheduler_url,
        "auth": "pool_password_or_invite",
        "oauth": "later",
    }


@app.get("/portal", response_class=HTMLResponse)
async def portal_page() -> HTMLResponse:
    return HTMLResponse(PORTAL_HTML)


@app.get("/api/config")
async def api_config(request: Request) -> dict[str, Any]:
    return {
        "scheduler_url": cfg.scheduler_url,
        "portal_url": _public_base(request),
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
        "allowed_job_types": sorted(UTILIZE_JOB_TYPES),
        "utilize_note": (
            "v1 Utilize can only submit allowlisted jobs: probe and pytorch_cuda_probe. "
            "No arbitrary shell or custom code."
        ),
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


PORTAL_HTML = 
r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>GPU Pool — Contribute &amp; Utilize</title>
<style>
  @import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap");
  :root {
    --bg0: #0f1412;
    --bg1: #17201c;
    --bg2: #1f2b25;
    --ink: #e8f0ea;
    --muted: #9bb0a3;
    --line: #2d3d34;
    --accent: #d4a24c;
    --accent2: #3d9b7a;
    --danger: #c45c4a;
    --ok: #6fbf8a;
    --font: "IBM Plex Sans", "Segoe UI", sans-serif;
    --mono: "IBM Plex Mono", Consolas, monospace;
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
  .wrap { max-width: 980px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
  header { margin-bottom: 1.75rem; }
  .brand {
    font-size: clamp(1.8rem, 4vw, 2.6rem);
    font-weight: 600;
    letter-spacing: -0.03em;
    margin: 0 0 0.35rem;
  }
  .brand span { color: var(--accent); }
  .lede { color: var(--muted); max-width: 42rem; line-height: 1.5; margin: 0; }
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
  h2 { margin: 0 0 0.85rem; font-size: 1.1rem; font-weight: 600; }
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
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.65rem;
  }
  .stat {
    background: rgba(0,0,0,0.22);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 0.7rem 0.8rem;
  }
  .stat b { display: block; font-family: var(--mono); font-size: 1.15rem; }
  .stat span { color: var(--muted); font-size: 0.78rem; }
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
    min-width: 7rem;
  }
  .nav button.active {
    background: rgba(61,155,122,0.18);
    color: var(--ink);
    border-color: var(--accent2);
  }
  .job-meta { font-family: var(--mono); font-size: 0.85rem; color: var(--muted); margin-top: 0.65rem; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1 class="brand">GPU <span>Pool</span></h1>
    <p class="lede">Private co-op portal — <strong>Contribute</strong> spare GPU/CPU capacity, or <strong>Utilize</strong> the pool with allowlisted jobs.</p>
    <p class="note" id="capacityNote">v1 contributes compute to JOBS (GPU/CPU). RAM/SSD figures are capacity advertisements for future job constraints — not a literal distributed filesystem yet.</p>
  </header>

  <section id="loginPanel" class="panel">
    <h2>Sign in</h2>
    <p class="lede" style="margin-bottom:0.5rem">MVP auth: shared pool password or invite code + display name. Real OAuth comes later.</p>
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
      <button type="button" class="active" data-view="dashboard" id="navDash">Dashboard</button>
      <button type="button" data-view="utilize" id="navUtilize">Utilize</button>
      <button type="button" data-view="contribute" id="navContribute">Contribute</button>
    </nav>

    <div id="viewDashboard">
      <div class="panel">
        <h2>Pool capacity</h2>
        <p class="lede" style="margin-bottom:0.85rem">Live summary from scheduler <code>/status</code>.</p>
        <div class="stats" id="stats"></div>
        <p class="err hidden" id="dashErr" style="margin-top:0.75rem"></p>
        <div class="actions">
          <button class="secondary" id="refreshBtn" type="button">Refresh dashboard</button>
        </div>
        <div style="margin-top:1rem; overflow:auto">
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
        <p class="note" id="utilizeNote" style="margin-top:0">v1 Utilize can only submit allowlisted jobs: <code>probe</code> and <code>pytorch_cuda_probe</code>. No arbitrary shell or custom code.</p>
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
        <p class="lede">Set dedication caps, then copy a start-token command. The worker reports <em>real</em> nvidia-smi / host inventory to the scheduler — nothing is mocked.</p>
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
  </section>
</div>
<script>
const $ = (id) => document.getElementById(id);
const bindSlider = (id, valId, fmt) => {
  const el = $(id), out = $(valId);
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
  $("viewDashboard").classList.toggle("hidden", name !== "dashboard");
  $("viewUtilize").classList.toggle("hidden", name !== "utilize");
  $("viewContribute").classList.toggle("hidden", name !== "contribute");
  document.querySelectorAll(".nav button").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.view === name);
  });
  if (name === "dashboard") refreshDash();
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

async function loadConfig() {
  const c = await api("/api/config");
  $("schedulerUrl").value = c.scheduler_url || "";
  if (c.capacity_note) $("capacityNote").textContent = c.capacity_note;
  if (c.utilize_note) $("utilizeNote").textContent = c.utilize_note;
}

async function refreshMe() {
  const me = await api("/api/me");
  if (me.ok) {
    $("who").textContent = me.user.display_name;
    show(true);
    setView("dashboard");
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
      ["Online", s.workers_online ?? 0],
      ["Free VRAM", fmtMb(s.free_vram_mb)],
      ["Total VRAM", fmtMb(s.total_vram_mb)],
      ["CPU cores", s.cpu_cores ?? 0],
      ["RAM avail (ad)", fmtMb(s.ram_available_mb)],
      ["Disk free (ad)", fmtMb(s.disk_free_mb)],
      ["Jobs queued", (s.jobs&&s.jobs.queued)||0],
      ["Jobs running", (s.jobs&&s.jobs.running)||0],
      ["Jobs done", (s.jobs&&s.jobs.completed)||0],
    ].map(([k,v]) => `<div class="stat"><b>${v}</b><span>${k}</span></div>`).join("");
    if (!d.ok) {
      $("dashErr").textContent = "Scheduler unreachable: " + (d.scheduler_error||"");
      $("dashErr").classList.remove("hidden");
    }
    const rows = (d.workers||[]).map(w => {
      const gpus = (w.gpus||[]).map(g => g.name || "?").join(", ") || "—";
      const vram = `${fmtMb(w.free_vram_mb)} free / ${fmtMb(w.total_vram_mb)}`;
      const pill = w.online ? '<span class="pill on">online</span>' : '<span class="pill off">offline</span>';
      return `<tr>
        <td><strong>${escapeHtml(w.name||"?")}</strong><br><span style="color:var(--muted);font-size:0.8rem">${escapeHtml(w.host||"")}</span></td>
        <td>${pill}<br><span style="color:var(--muted);font-size:0.78rem">${escapeHtml(w.status||"")} · ${w.heartbeat_age_sec??"?"}s</span></td>
        <td>${escapeHtml(gpus)}<br>${vram}</td>
        <td>${w.cpu_cores??0} cores · ${w.max_cpu_percent??"—"}%</td>
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
    setView("dashboard");
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
  if (!$("appPanel").classList.contains("hidden") && !$("viewDashboard").classList.contains("hidden")) {
    refreshDash();
  }
}, 8000);
</script>
</body>
</html>
"""
//neeed to fix this it wrong formet and to much cna be optimize more and make better as wwell use less paython dude //
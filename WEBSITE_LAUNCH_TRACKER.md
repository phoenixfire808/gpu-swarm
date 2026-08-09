# GPU Pool Website Launch Tracker

**Project:** stable browser entry point + reliable one-click host launch for `gpu-swarm`
**Owner:** Drew / parent session
**Repository:** `C:/Users/Drew/Projects/gpu-swarm/`
**Canonical companion:** `TRACKER_FRIEND_ONBOARDING.md`
**Opened:** 2026-08-08

This file is append-oriented. Preserve prior receipts and add new state below; do not delete old evidence.

---

## Current checkpoint

**Goal:** Make the GPU Pool launch like a real website: one host action brings up the local services, verifies them, publishes the portal, and opens a usable link. Then provide a durable Cloudflare-hosted address instead of sharing ephemeral Quick Tunnel URLs.

**Current state (fresh evidence, 2026-08-08):**

- Local scheduler `http://127.0.0.1:8766/status`: **down** (`curl` HTTP 000 / connection refused).
- Local portal `http://127.0.0.1:8767/portal`: not reached because the first health probe stopped at the scheduler failure.
- `data/public_endpoints.share.txt` contains a Quick Tunnel URL updated 2026-08-08, but its origin is currently unavailable; this URL is not a stable deployment.
- The repository already has a portal, scheduler, worker, Discord bot, hidden launchers, and a Quick Tunnel wrapper; these must be scaffolded, not replaced.
- `dist/GPUPool.exe` exists from the prior build line; the prior tracker records a packaged-runtime failure that requires final rebuild/smoke acceptance.
- Existing tracker history is preserved in `TRACKER_FRIEND_ONBOARDING.md`; no old receipts are being removed.

---

## Architecture decision under evaluation

### Recommended default: local GPU origin + Cloudflare stable front door

- Keep scheduler, portal, worker, and allowlisted job execution on Drew's Windows host.
- Replace Quick Tunnel as the shared address with a **named Cloudflare Tunnel** bound to a domain/hostname Drew controls.
- Optionally add a tiny Cloudflare Worker or Pages landing page at the root that links to `/portal`, downloads, health state, and onboarding. The Worker is only a front door; it does not run GPU jobs.
- Use a host-side launcher to start the origin, wait for `/status` and `/portal`, start/reconcile the tunnel, write the current endpoint, and open the browser.

**Why:** this preserves local GPU access and avoids exposing the scheduler directly. Cloudflare Tunnel creates outbound-only connections from the host, so no inbound port-forwarding is required. A named tunnel provides a stable address; a Quick Tunnel does not.

### Alternatives researched

- **Tailscale Funnel:** useful for a temporary public URL, but still host-dependent and not the preferred durable product front door.
- **Render:** good Git-connected managed web deploys, but not a replacement for the local GPU worker; stateful scheduler/origin behavior would need redesign.
- **Fly.io:** capable app deployment and scaling, but adds container/ops complexity and still does not provide Drew's local GPU.
- **DigitalOcean App Platform:** managed web/static/worker components and public URLs, but likewise only a control plane unless the GPU worker remains separately connected.

---

## Active work (keep about five items)

- [x] Recover the local origin cleanly and identify/stop only duplicate or orphaned GPU Pool service processes.
- [x] Build `launch-public.cmd` plus a hidden Python launcher with bounded readiness checks, clear failure logs, stale-URL prevention, and browser open only after success.
- [ ] Add a durable Cloudflare deployment template (named tunnel ingress + optional Worker/Pages front door) without placing credentials in the repository.
- [ ] Rebuild and smoke-test the packaged Windows experience after the prior PyInstaller defect is resolved.
- [x] Run one final local/public acceptance batch and record exact URL/HTTP/worker receipts here and in the companion tracker.

---

## Acceptance criteria

- Double-clicking the host launcher does not create console-window spam or silently report success.
- It starts only the required services, waits for each dependency, and exits nonzero with a bounded diagnostic when a service fails.
- It never reuses a stale URL from `data/public_endpoints.json`; the public endpoint must be freshly observed or the launch fails.
- Local `/status` and `/portal` return HTTP 200 before the tunnel is considered ready.
- The public `/portal` returns HTTP 200 and its API routes reach the local scheduler without recursive tunnel routing.
- A durable mode has a stable hostname and explicitly documents that availability still depends on the local GPU host unless the control plane is moved to dedicated infrastructure.
- No credential, token, invite secret, or private database is committed or printed into public frontend assets.
- One focused real smoke proves the browser entry point and one allowlisted pool probe works.

---

## Research receipts — 2026-08-08

Local SearXNG at `127.0.0.1:8888` refused all five discovery queries, so I used direct extraction of five selected official sources and did not claim SearXNG results:

1. Cloudflare Tunnel docs — `https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/`
   - Tunnel uses outbound-only `cloudflared` connections; the origin need not have a publicly routable IP.
   - A persistent tunnel object is identified by UUID and can have multiple connectors.
2. Tailscale Funnel docs — `https://tailscale.com/docs/features/tailscale-funnel`
   - Publishes a local service through a Funnel URL while hiding the device IP; URLs and availability remain tied to the local device/tailnet setup.
3. Render deploy docs — `https://render.com/docs/deploys`
   - Supports Git-linked automatic deploys and manual deploys; suitable for a managed web service, not a direct substitute for local GPU execution.
4. Fly Launch docs — `https://fly.io/docs/launch/`
   - Uses `fly launch`, `fly.toml`, `fly deploy`, and scaling/autostop controls; operationally more involved than a stable Cloudflare front door for this existing Windows origin.
5. DigitalOcean App Platform docs — `https://docs.digitalocean.com/products/app-platform/how-to/create-apps/`
   - Managed static/web/worker/job components from repos or images with public URLs; useful for a future control plane, not the current local GPU origin.

---

## Receipts

### 2026-08-08 — Parent recovery / current failure boundary

- Recovered prior session `@session:personal/20260807_183510_e4adff` and preserved its existing changes.
- `git status --short` shows the prior installer/launcher work is uncommitted; no reset, checkout, or external push performed.
- Local health probe: scheduler connection refused on port 8766; the Quick Tunnel URL in `data/public_endpoints.share.txt` is therefore not accepted as live evidence.
- Existing `scripts/start_public_tunnel.py` correctly documents stale-URL protection in intent, but the current end-to-end launch path still needs a single orchestrator and fresh origin checks.

### 2026-08-08 — One-click launcher implementation

- Added `scripts/launch_public.py` and `launch-public.cmd`.
- The orchestrator checks/reuses local scheduler and portal, starts/reuses the worker, starts `tools/cloudflared.exe` directly with detached hidden flags, waits for a newly emitted Quick Tunnel URL, verifies public `/portal` and `/pool-api/status`, then writes endpoint files and optionally opens the browser.
- `--no-browser` provides a headless acceptance mode; `--with-bot` is explicit and was not used.
- The prior PowerShell tunnel wrapper remains for compatibility, but the new launcher no longer depends on its flaky event-handler parse/runtime path.
- **Next receipt:** run `launch-public.cmd --no-browser`, inspect the fresh public URL and logs, then record success or the exact failure boundary.

### 2026-08-08 — Acceptance receipt

- `cmd.exe /c launch-public.cmd --no-browser` exited `0`.
- Launcher log recorded scheduler ready, portal ready, worker already online, a fresh Quick Tunnel URL, and `PUBLIC READY`.
- `data/public_endpoints.json` was rewritten only after verification with portal path `https://initial-zinc-openings-wanna.trycloudflare.com/portal` and tunnel PID `14876`.
- Local scheduler `/status`: HTTP 200; `workers_online=1`, `free_vram_mb=2014`, GPUs RTX 5060 Ti + RTX 2070 SUPER.
- Local portal `/portal`: HTTP 200.
- Public portal `/portal`: HTTP 200; browser rendered `GPU Pool — Network Hub`.
- Public `/pool-api/status`: HTTP 200 with the same live worker inventory.
- Browser main flow: joined as `Jarvis Smoke`; Network Hub displayed `1 online` and Share / Use / Invite actions.
- Allowlisted CLI smoke `GPU_SWARM_SCHEDULER_URL=http://127.0.0.1:8766 python -m gpu_swarm utilize probe --wait`: exit `0`, job status `completed`, both GPUs returned in inventory.
- **Next unfinished step:** named Cloudflare or dedicated-host deployment after Drew authorizes the target account/domain.

### 2026-08-08 — Durable Cloudflare architecture selected

- Drew selected the recommended stable Cloudflare hostname path.
- Existing `C:\Users\Drew\.cloudflared\tunnel.yml` is owned by Mission Control/OpenClaw and is not reused or edited.
- Added tracked `cloudflare/README.md` and `cloudflare/gpu-pool.tunnel.yml.example`; real config/credentials remain under `%USERPROFILE%\\.cloudflared\\` and are ignored.
- Extended `scripts/launch_public.py` with `--named`, `--hostname`, `--tunnel-name`, and `--config`. Named mode starts only the GPU Pool config, verifies the same `/portal` and `/pool-api/status` routes, and writes `mode=cloudflared_named` only after success.
- Added ignored `.env` examples for the hostname, tunnel name, and config path.
- **Blocker requiring one value:** the Cloudflare-managed public hostname/domain to bind to the new `gpu-pool` tunnel.

### 2026-08-09 — Cloudflare login boundary

- Drew authorized proceeding with the stable Cloudflare path.
- `tools/cloudflared.exe tunnel login` was started locally and issued a browser authorization URL.
- Parent-side verification found the CLI still waiting for its callback; `%USERPROFILE%\\.cloudflared\\cert.pem` and a new GPU Pool tunnel credential were absent.
- The browser automation hit Cloudflare's security challenge, so no claim of account authorization or tunnel creation is made.
- The existing Mission Control/OpenClaw `tunnel.yml` remains untouched.
- **Next single action:** complete the `cloudflared tunnel login` authorization in the normal local browser, then rerun the bounded tunnel-create/DNS/ named-launch sequence.

### 2026-08-09 — Quick Tunnel kept live while named auth is pending

- Refreshed `cmd.exe /c launch-public.cmd --no-browser`: exit `0`.
- Scheduler, portal, and worker were already healthy; the old owned Quick Tunnel was stopped cleanly.
- Fresh verified temporary portal: `https://rna-reasons-warriors-where.trycloudflare.com/portal`.
- Launcher wrote `mode=cloudflared_quick` only after public portal and pool API verification.
- Named deployment is not claimed complete because the Cloudflare CLI certificate is still absent.

### 2026-08-09 — Temporary public mode selected

- Drew selected a temporary public link so people can use the pool immediately.
- Named Cloudflare deployment is intentionally deferred; Quick Tunnel is the active delivery path.
- Next action: run `launch-public.cmd --no-browser`, verify the fresh public portal and pool API, then update the ignored friend handoff file with the current URL.

### 2026-08-09 — Temporary handoff receipt

- `cmd.exe /c launch-public.cmd --no-browser` exited `0`.
- Fresh temporary portal: `https://handy-pads-resource-albert.trycloudflare.com/portal`.
- Local scheduler, portal, and worker were reused successfully; the old owned tunnel was stopped and replaced.
- Browser verification loaded title `GPU Pool — Network Hub` and the invite/join form.
- `FRIEND_HANDBOFF.md` now points to the fresh portal URL.
- Invite code remains in the local handoff file and ignored runtime config; the URL remains ephemeral and changes on tunnel restart.

### 2026-08-09 — Current endpoint rechecked

- Existing endpoint was reused without rotation: `https://handy-pads-resource-albert.trycloudflare.com`.
- `/portal`: HTTP 200, 64,729 bytes.
- `/pool-api/status`: HTTP 200, live worker JSON returned.
- The temporary public site is currently ready for people to use.

---

## Decision gate requiring Drew input

Before any external Cloudflare deployment, choose one:

- **Stable Cloudflare hostname:** provide/authorize a Cloudflare login and the domain/hostname to bind; credentials must be entered locally, never pasted into chat or stored in this tracker.
- **Temporary demo only:** keep Quick Tunnel, accepting URL rotation and host-dependent uptime.
- **Dedicated control plane:** authorize a separate hosted service design; this requires deciding where the scheduler state/database and worker authentication live.

Until a choice is authorized, local implementation and verification remain safe to continue; external deployment does not.

### 2026-08-09 — Cloudflare installer integration / release candidate

- Added `gpu_swarm/cloudflare_access.py` with bundle-safe Quick/Named modes, owned tunnel PID cleanup, bounded local/public probes, and endpoint artifact writing without response-body logging.
- Added wizard controls under **Network & Workspace**: install Cloudflare helper, publish temporary HTTPS link, and open stable hostname guide.
- Added source wrappers: `scripts/install_cloudflared.cmd` and `scripts/cloudflare-access.cmd`.
- Updated `scripts/install_cloudflared.ps1` to install into writable `%LOCALAPPDATA%\\GPUPool\\tools` for packaged users and to support JSON receipts.
- Added generic user-facing `cloudflare/README.md` and credential-safe named tunnel template; added all Cloudflare resources to `gpu_pool.spec`.
- Verification receipts: Python compile passed; PowerShell `_check_parse.ps1` passed `ALL-PARSE-OK`; isolated GPUPool venv imported the updated UI; Cloudflare helper install/status passed; real Quick Tunnel smoke passed with public `/portal` HTTP 200 and `/pool-api/status` HTTP 200.
- Resolved during smoke: duplicate Windows `creationflags` argument in the helper; rerun passed with sanitized status-only probe output.
- Release task: rebuild `dist\\GPUPool.exe`, inspect artifact, commit coherent worktree, push `master` to `origin`.

### 2026-08-09 — Release receipt

- Clean build command: `env -u PYTHONPATH powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\Users\\Drew\\Projects\\gpu-swarm\\build_exe.ps1 -Clean`.
- Build completed successfully with `dist\\GPUPool.exe` at 35,218,966 bytes.
- Packaged smoke passed: `GPUPool.exe --worker --help` and `GPUPool.exe --local-endpoint --help` both exited 0.
- Commit: `4777dbd` (`feat: add guided Cloudflare public access`).
- Push: `master` successfully advanced on `origin` from `d4083c4` to `4777dbd`.
- Follow-up tracker receipt commit is being added after this entry.

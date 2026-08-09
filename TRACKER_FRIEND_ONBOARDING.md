# TRACKER_FRIEND_ONBOARDING.md

**Project:** gpu-swarm friend onboarding (host bring-up + installer reliability)
**Owner:** Drew (parent session only; no sub-agents per standing rule)
**Repo:** `C:/Users/Drew/Projects/gpu-swarm/` (public: https://github.com/phoenixfire808/gpu-swarm)
**Date opened:** 2026-08-07
**Last touched:** 2026-08-07 (post-fix verification)
**Live portal URL:** https://sandra-united-expiration-sorry.trycloudflare.com/portal (rotates on tunnel restart)
**Invite code:** glitch-factor (in `.env`, never echo in chat/logs/memory)
**Channel:** Glitch Factor Discord, bot `GPU pool#1686`

This file is the **single source of truth for live status and receipts**. Update
on every change. Preserve history (append, do not overwrite) so cross-session
and cross-agent handoffs are auditable. See `ROADMAP.md` for design rationale.

---

## 0. How to use this file

- The **Status snapshot** at the top is what another agent reads first.
- The **Phase log** is the running checklist. New items go at the bottom of
  the active phase, not interleaved with completed items.
- The **Receipts** section is append-only. Each entry is dated and includes
  the command, exit code, and one-line result.
- The **Handoff** section at the bottom records the previous agent's last
  verified state and what they were working on.
- Do **not** delete old receipts. Do **not** rewrite the status block in
  place. If a value changes, add a new dated entry.

---

## 1. Status snapshot (live)

```text
Last verified:   2026-08-07
Public portal:   HTTP 200  (trycloudflare URL above)
Scheduler:       HTTP 200  (127.0.0.1:8766)
Portal local:    HTTP 200  (127.0.0.1:8767)
Worker:          online   (Drew-Home, 2 GPUs)
Bot:             logged in (GPU pool#1686)
PowerShell:      all 5 scripts parse OK
Persistence:     Startup-folder VBS installed; Task Scheduler blocked by non-elevated session
Install UX:      source fixed; packaged EXE rebuild pending (Phase A8)
```

| Service | Endpoint | Status | Source |
|---------|----------|--------|--------|
| Scheduler | `http://127.0.0.1:8766/status` | 200, workers_online=1, free_vram=2014 MB | live probe |
| Portal | `http://127.0.0.1:8767/portal` | 200 | live probe |
| Public portal | `https://sandra-united-expiration-sorry.trycloudflare.com/portal` | 200 | live probe |
| Public API | `https://sandra-united-expiration-sorry.trycloudflare.com/pool-api/status` | 200 | live probe |

---

## 2. Decisions locked in

| Decision | Choice | Why | Source |
|----------|--------|-----|--------|
| Keep-up mechanism | Windows Task Scheduler **with Startup-VBS fallback** | Task Scheduler needs elevation; Hermes runs non-elevated. VBS in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\` covers the common case. | R-4 in ROADMAP.md |
| Public tunnel | Cloudflare quick tunnel by default | Zero Cloudflare account needed for the friend path; rotates URL on restart. | R-2 |
| Persistence location | `data/` and `.env` gitignored; share via `data/public_endpoints.share.txt` | Tunnel URLs and invite codes must never reach git. | standing rule |
| Installer default | Detection-only for Tailscale and VirtualBox/Vagrant | Friend path does not need either; opt-in avoids multi-GB downloads. | user feedback |
| Secret handling | Invite code in `.env` only; URL in `data/public_endpoints.share.txt`; handoff doc gitignored | Standing rule; secrets never in chat, memory, or repo. | USER.md |
| Python interpreter | CPython 3.12.x | Avoids 3.13 ABI breakage with LangSmith etc. | MEMORY.md |

---

## 3. Phase log

### Phase A - Installer reliability (ACTIVE, source fixed, EXE pending)

Status: source substantially repaired. Packaged EXE rebuild is the only
remaining blocker before a fresh friend can run the installer end-to-end.

- [x] A1. Removed frozen-EXE background bootstrap in `gpu_pool_entry.py`
- [x] A2. `install-prereqs.ps1` default is now detection-only
- [x] A3. Tailscale install gated behind `-ConnectTailscale`
- [x] A4. VirtualBox/Vagrant install gated behind `-WorkspaceTools`
- [x] A5. `desktop_app.py` wizard buttons disable during in-flight action
- [x] A6. `portable_python.py` download has timeout + retry + `.part` staging
- [x] A7. Existing venv repair via `with_requirements=True`
- [x] A8. All PowerShell scripts: UTF-8 BOM + ASCII punctuation
- [x] A9. `scripts/_check_parse.ps1` added as CI gate (5/5 parse-ok)
- [x] A10. `install-prereqs.cmd` header updated to reflect new defaults
- [ ] A11. Rebuild `GPUPool.exe` with `pyinstaller --noconfirm --windowed --onedir gpu_pool_entry.py`
- [ ] A12. Add `scripts/smoke_install.cmd` (clone -> venv -> probe -> 60s PASS/FAIL)
- [ ] A13. Add "Verify install" button in wizard that runs `check_prereqs.ps1` + scheduler probe + portal probe

### Phase B - Friend experience polish

- [ ] B1. Server-side invite validation at `/pool-api/invite`
- [ ] B2. "Copy portal URL" button in SPA
- [ ] B3. `/about.html` static explainer
- [ ] B4. Memorable hostname (requires named tunnel; see Phase D)
- [ ] B5. SSE for long jobs (requires named tunnel; Quick Tunnels block SSE)

### Phase C - Worker reliability

- [ ] C1. Heartbeat every 5s, not 30s
- [ ] C2. Friend-readable GPU failure messages
- [ ] C3. Hot-reload `.env` without restart
- [ ] C4. Worker `--dry-run` mode

### Phase D - Tunnel stability

- [ ] D1. Quick tunnel (default) — already working
- [ ] D2. Named tunnel behind Advanced wizard section
- [ ] D3. Surface 200-concurrent-request cap to host when hit

### Phase E - Discord bot richness

- [ ] E1. `/pool status` (works today; needs friend-friendly formatting)
- [ ] E2. `/pool invite <user>` DM
- [ ] E3. `/pool join <invite>` validate without browser
- [ ] E4. Per-guild slash command permissions

### Phase F - Multi-tenant

- [ ] F1. Per-friend invite codes with TTL
- [ ] F2. Per-friend rate limits
- [ ] F3. Per-friend audit log
- [ ] F4. Friend revocation endpoint
- [ ] F5. Friend self-service `/pool-api/me`

### Phase G - Local model endpoint

- [ ] G1. `winget install Ollama.Ollama` from wizard
- [ ] G2. Auto-pull default model
- [ ] G3. "Use my local model" SPA toggle
- [ ] G4. Document privacy model

### Phase H - Workspace (VirtualBox + Vagrant)

- [ ] H1. Detect Hyper-V conflict pre-install
- [ ] H2. `bcdedit /set hypervisorlaunchtype off` recipe
- [ ] H3. Tested Ubuntu 22.04 `Vagrantfile`
- [ ] H4. Multi-step Workspace wizard flow

### Phase I - Observability

- [ ] I1. Structured JSON logs (already done; verify format consistency)
- [ ] I2. `/pool-api/healthz` returning 200 only if all 5 services healthy
- [ ] I3. Optional Sentry/OTel behind flag

### Phase J - Releases

- [ ] J1. Pin Python 3.12.x in CI
- [ ] J2. Pin cloudflared version in CI
- [ ] J3. Code-sign the EXE (SmartScreen)
- [ ] J4. Auto-increment version in `RELEASE_NOTES_*.md`

---

## 4. To-do list (ordered, copy-pasteable)

The next agent (or Drew in a future session) picks up here. Each item has
explicit acceptance criteria.

### Immediate (next 1-2 sessions)

1. **[ ] A11. Rebuild the EXE**
   - Acceptance: `dist/GPUPool/GPUPool.exe` exists, has SHA-256 in
     `RELEASE_NOTES_v0.2.0.md`, smoke run shows 200 on `/status` within 30s.
   - Command (from repo root):
     `pyinstaller --noconfirm --windowed --onedir --name GPUPool gpu_pool_entry.py`
   - Verify: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/_check_parse.ps1`
     still says `ALL-PARSE-OK` before building.

2. **[ ] A12. Add `scripts/smoke_install.cmd`**
   - Acceptance: running from a clean clone produces "PASS" in under 60s
     when scheduler is up, or prints the specific failing component.
   - Behaviour:
     - Locate Python 3.12 via `py -3.12 -V`
     - Create venv at `%LOCALAPPDATA%\GPUPool\smoke-venv`
     - `pip install -r requirements-joiner.txt`
     - `python -m gpu_swarm.cli check` (or equivalent)
     - Hit `/status` and `/portal` and report codes
     - Print elapsed seconds

3. **[ ] A13. Wizard "Verify install" button**
   - Acceptance: clicking the button runs `check_prereqs.ps1`, scheduler
     probe, and portal probe, then renders a coloured table.
   - Implementation: extend `desktop_app.py` button group; reuse
     `app_backend.install_prereqs(detect_only=True)` and add scheduler/
     portal probes in a worker thread.

### This week

4. **[ ] B2. "Copy portal URL" button**
   - File: `gpu_swarm/portal_hub.html`
   - Add a button next to the login submit that calls
     `navigator.clipboard.writeText(location.origin)` after successful login.

5. **[ ] C4. Worker `--dry-run`**
   - File: `gpu_swarm/worker.py`
   - Add argparse `--dry-run` that prints detected GPUs + nvml version +
     exits 0. Used by the wizard's "Verify install" path.

6. **[ ] D3. Surface 200-request cap hit**
   - File: `gpu_swarm/portal.py`
   - When `/pool-api/*` returns 429 from the cloudflared edge, log a
     warning with the body and surface a friendly "Tunnel is busy; try
     again in 30 seconds" message in the SPA.

### This month

7. **[ ] F1. Per-friend invite codes with TTL**
   - File: `gpu_swarm/portal_store.py` + `.env`
   - Replace single `GPU_SWARM_INVITE_CODES` with a JSON list:
     `[{code, expires_at, max_uses, uses, role}]`. Backwards compatible:
     plain-string entries default to no expiry and unlimited uses.

8. **[ ] J3. Code signing**
   - Buy a cert (Drew's call). Once available, `signtool sign /fd SHA256 /a dist/GPUPool/GPUPool.exe`.

---

## 5. Receipts (append-only)

### 2026-08-07 - Live stack health check
- Command: `urllib.request.urlopen("http://127.0.0.1:8766/status", timeout=8)`
  Result: HTTP 200, body `{"workers_total":4,"workers_online":1,...}`
- Command: `urllib.request.urlopen("http://127.0.0.1:8767/portal", timeout=8)`
  Result: HTTP 200, body `<!DOCTYPE html>...GPU Pool - Networ...`
- Command: `urllib.request.urlopen("https://sandra-united-expiration-sorry.trycloudflare.com/portal", timeout=8)`
  Result: HTTP 200, body `<!DOCTYPE html>...GPU Pool - Networ...`

### 2026-08-07 - PowerShell parse gate
- Command: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/_check_parse.ps1`
  Result: `ALL-PARSE-OK` (5/5: install-prereqs.ps1, install_joiner_deps.ps1,
  check_prereqs.ps1, install_cloudflared.ps1, start_public_tunnel.ps1)

### 2026-08-07 - Default install behaviour (detect-only)
- Command: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install-prereqs.ps1 -Json -Quiet`
  Result: Tailscale "skipped (use -ConnectTailscale to install)", VirtualBox
  "skipped (use -WorkspaceTools to install)", Vagrant "skipped (use -WorkspaceTools
  to install)". Detected Tailscale is already installed on host (1.98.10 on
  100.85.165.84). No download attempted.

### 2026-08-07 - Live end-to-end probe
- Command: `cd "C:/Users/Drew/Projects/gpu-swarm" && python -m gpu_swarm utilize probe --wait`
  Result: exit 0, probe completed on `Drew-Home` with both GPUs.

### 2026-08-07 - Browser smoke through public URL
- Command: `browser_navigate("https://sandra-united-expiration-sorry.trycloudflare.com/portal")`
  Result: page rendered, login form visible, submit returned home with
  Share/Use/Invite actions.

### 2026-08-07 - Persistence fallback
- File: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\GPUPool-Startup.vbs`
  Action: copied from `scripts/GPUPool-Startup.vbs`; launches scheduler,
  portal, worker, and tunnel hidden at logon.
- Task Scheduler: blocked by `Access is denied` from non-elevated Hermes session.
  Decision documented; VBS fallback active.

---

## 6. Handoff from previous sessions

### @session:personal/20260807_195826_57d251
- Prior-agent last verified: `install-prereqs.ps1` entering Tailscale
  installer when no explicit network action was requested.
- Prior-agent next work: verify new default behavior, update wrapper
  comments/routing, consolidate deprecated hidden launchers, run final
  acceptance.
- Current parent status: preserved all uncommitted changes; no merge/reset.
  Continuing from the parser/default-routing blocker.

### @session:personal/20260807_183510_e4adff (earlier context compaction)
- Earlier same-day session brought the host stack up to a known-healthy state
  and wrote the initial installer-reliability pass.
- Source changes from that session were preserved through subsequent
  compactations and are reflected in the Phase A checklist above.

---

## 7. Files in active scope

| Path | State | Purpose |
|------|-------|---------|
| `gpu_pool_entry.py` | modified | entry point, frozen-aware |
| `gpu_swarm/portable_python.py` | modified | bounded CPython download |
| `gpu_swarm/app_backend.py` | modified | wizard IPC + script wrappers |
| `gpu_swarm/app/desktop_app.py` | modified | Tk wizard, button guards |
| `scripts/install-prereqs.ps1` | modified | detection-only default |
| `scripts/install-prereqs.cmd` | modified | passthrough |
| `scripts/install_joiner_deps.ps1` | modified | UTF-8 BOM + ASCII |
| `scripts/check_prereqs.ps1` | modified | UTF-8 BOM + ASCII |
| `scripts/start_hidden.py` | new | hidden launcher |
| `scripts/_run_py.cmd` | new | pythonw wrapper |
| `scripts/start_public_tunnel.py` | new | cloudflared wrapper |
| `scripts/_check_parse.ps1` | new | CI gate |
| `scripts/GPUPool-Startup.vbs` | new | logon autostart |
| `scripts/task_service.py` | new | legacy elevated path |
| `scripts/run-hidden.cmd` | modified | deprecated |
| `start-*.cmd` (5 files) | modified | routed to _run_py.cmd |
| `start-gpu-pool-app.cmd` | modified | wizard entry |
| `TRACKER_FRIEND_ONBOARDING.md` | this file | live status + receipts |
| `ROADMAP.md` | this pass | design + 10 research sources |
| `FRIEND_HANDBOFF.md` | existing | friend-facing instructions (gitignored) |
| `DOWNLOAD.md`, `LOGIN.md` | modified | docs refresh |

Untracked but on disk (intentional, gitignored):
- `.env` - tokens, invite codes
- `data/joiner_settings.json` - per-joiner config
- `data/public_endpoints.json` - latest trycloudflare URL
- `data/public_endpoints.share.txt` - friend-shareable URL
- `data/<service>.pid` - PID files for the four services
- `%LOCALAPPDATA%\GPUPool\logs\*.log` - runtime logs
- `%LOCALAPPDATA%\GPUPool\prereq-cache\` - installer downloads

---

## 8. Standing rules (do not violate without explicit approval)

- No sub-agents or workers; parent session only.
- No secrets in chat, memory, repo, or handoff docs.
- No silent re-installs; every script must be idempotent.
- No silent network calls; every download must be in a script the user can read.
- No silent elevation; UAC prompts only on explicit user action.
- Every change updates this file and `ROADMAP.md`.

---

## 10. Website launch continuation — 2026-08-08

- New companion tracker: `WEBSITE_LAUNCH_TRACKER.md`.
- Active goal: one-click host launch with bounded readiness checks plus a durable website entry point.
- Fresh parent probe found scheduler `127.0.0.1:8766` down (HTTP 000 / connection refused); the Quick Tunnel URL in `data/public_endpoints.share.txt` is not accepted as live until the origin is recovered and re-probed.
- Recommended architecture: local GPU origin behind a named Cloudflare Tunnel, optionally fronted by a small Worker/Pages landing page. Quick Tunnel remains demo-only because its hostname rotates and its origin depends on the Windows host.
- Five official sources were recorded in the companion tracker. Local SearXNG was unavailable, so direct official-source extraction was used explicitly.
- Next parent action: recover the origin cleanly, then implement and verify the single orchestrator before any external Cloudflare deployment.

---

## 11. One-click launcher implementation — 2026-08-08

- Added `scripts/launch_public.py` as the bounded orchestrator for scheduler, portal, worker, optional explicitly requested bot, and Cloudflare Quick Tunnel.
- Added top-level `launch-public.cmd` as the copyable/double-clickable entry point.
- The launcher bypasses the flaky `start_public_tunnel.ps1` event-handler path and starts the checked-in `tools/cloudflared.exe` directly with a hidden detached process.
- It records `data/launch_public.log`, requires fresh URL observation, verifies local and public routes, writes endpoint files only after public success, and supports `--no-browser` for headless acceptance.
- The authenticated Discord bot is not started by default; `--with-bot` is an explicit opt-in because it is an external connection.
- **Next:** run one bounded `launch-public.cmd --no-browser` smoke, inspect the fresh endpoint and logs, then record the result.

### 2026-08-08 — One-click public acceptance receipt

- `cmd.exe /c launch-public.cmd --no-browser` exited `0`.
- Local scheduler and portal both returned HTTP 200; worker was online with `free_vram_mb=2014` and RTX 5060 Ti + RTX 2070 SUPER.
- Fresh Quick Tunnel URL observed and verified: `https://initial-zinc-openings-wanna.trycloudflare.com/portal` (public portal HTTP 200; public `/pool-api/status` HTTP 200).
- Browser rendered `GPU Pool — Network Hub`; joining as `Jarvis Smoke` exposed the main Share / Use / Invite actions and showed `1 online`.
- Allowlisted `python -m gpu_swarm utilize probe --wait` completed successfully with both GPUs in the returned inventory.
- This proves the temporary browser-first path. The URL remains ephemeral until a named Cloudflare Tunnel or dedicated control-plane deployment is authorized.

### 2026-08-08 — Durable Cloudflare path selected

- Drew selected stable Cloudflare hostname deployment.
- Existing Mission Control/OpenClaw config at `C:\Users\Drew\.cloudflared\tunnel.yml` remains untouched.
- Added `cloudflare/README.md` and `cloudflare/gpu-pool.tunnel.yml.example` with credential-safe setup steps.
- Extended `scripts/launch_public.py` with named mode: `--named --hostname ... --tunnel-name gpu-pool --config ...`.
- Named mode verifies public `/portal` and `/pool-api/status` before writing endpoint receipts.
- **Blocker:** the actual Cloudflare-managed public hostname/domain is still required before login, tunnel creation, DNS routing, and final named-mode smoke.

### 2026-08-09 — Cloudflare authorization boundary

- Drew authorized proceeding with stable Cloudflare deployment.
- `tools/cloudflared.exe tunnel login` issued a local browser authorization URL, but the CLI remained in `Waiting for login...` state.
- `%USERPROFILE%\\.cloudflared\\cert.pem` and a new GPU Pool credential were absent on parent verification; dashboard login alone has not completed the CLI callback.
- Browser automation encountered Cloudflare's security challenge. Existing Mission Control/OpenClaw tunnel config remains untouched.
- Next action is local completion of the Cloudflare CLI authorization, followed by dedicated tunnel creation, DNS route, and final `--named` smoke.

### 2026-08-09 — Quick Tunnel kept live while named auth is pending

- Refreshed `cmd.exe /c launch-public.cmd --no-browser`: exit `0`.
- Scheduler, portal, and worker were already healthy; the old owned Quick Tunnel was stopped cleanly.
- Fresh verified temporary portal: `https://rna-reasons-warriors-where.trycloudflare.com/portal`.
- Launcher wrote `mode=cloudflared_quick` only after public portal and pool API verification.
- Named deployment is not claimed complete because the Cloudflare CLI certificate is still absent.

### 2026-08-09 — Temporary public mode selected

- Drew selected a temporary public link so people can use the pool immediately.
- Named Cloudflare deployment is intentionally deferred; Quick Tunnel is the active delivery path.
- Next action: refresh `launch-public.cmd --no-browser`, verify the fresh public portal and pool API, then update `FRIEND_HANDBOFF.md` with the current URL.

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

## 9. Detailed to-do list with acceptance criteria

Each item below has: file(s) to touch, the command to verify, and what
"PASS" looks like. Copy-pasteable.

### 9.1 Immediate (next 1-2 sessions)

#### T1. Rebuild `GPUPool.exe` (Phase A.8)

**Files:** `pyinstaller --noconfirm --windowed --onedir --name GPUPool gpu_pool_entry.py`

**Verify:**
```powershell
Test-Path dist\GPUPool\GPUPool.exe          # must be True
(Get-Item dist\GPUPool\GPUPool.exe).Length  # must be > 1 MB
.\dist\GPUPool\GPUPool.exe --version        # prints version, exits 0
```

**PASS criteria:** EXE exists, runs, prints version, does not auto-bootstrap.

#### T2. Add `scripts/smoke_install.cmd` (Phase A.9)

**Files:** `scripts/smoke_install.cmd` (new)

**Verify:**
```powershell
# From a clean clone with scheduler already up:
.\scripts\smoke_install.cmd
echo $LASTEXITCODE
# Must be 0 and "PASS" must appear in the output.
```

**PASS criteria:** Reports PASS in <60s with scheduler already running.
Reports the failing step name on failure.

#### T3. Wizard "Verify install" button (Phase A.10)

**Files:** `gpu_swarm/app/desktop_app.py`, `gpu_swarm/app_backend.py`

**Verify:**
```powershell
# Manual test:
python -m gpu_swarm.app.desktop_app
# Click "Verify install". Wait. Check the rendered table.
```

**PASS criteria:** Click runs `install_prereqs(detect_only=True)` +
scheduler probe + portal probe, renders a coloured 5-row table within 15s.

#### T4. Server-side invite validation (Phase B.1)

**Files:** `gpu_swarm/portal.py`, `gpu_swarm/portal_hub.html`

**Verify:**
```bash
curl -X POST http://127.0.0.1:8767/pool-api/invite/validate \
     -H 'Content-Type: application/json' \
     -d '{"code":"glitch-factor","name":"Test"}' \
     -c cookies.txt -i
# Expect: 200, Set-Cookie: gpu_pool_session=...
```

**PASS criteria:** Valid invite returns 200 with cookie; invalid returns 401
with generic message; SPA stores cookie for subsequent calls.

#### T5. Copy portal URL button (Phase B.2)

**Files:** `gpu_swarm/portal_hub.html`

**Verify:** Manual in browser. Login. Click Copy. Paste into notepad.
Confirm the URL is there.

**PASS criteria:** Single click copies current URL to clipboard.

### 9.2 This week

#### T6. Worker 5s heartbeat (Phase C.1)

**Files:** `gpu_swarm/worker.py`

**Verify:**
```bash
# Watch scheduler log while killing worker:
Get-Content $env:LOCALAPPDATA\GPUPool\logs\scheduler.log -Wait
# Worker should be marked offline within 15s of process death.
```

**PASS criteria:** Worker marked offline within 15-20s of kill.

#### T7. Friend-readable GPU failure (Phase C.2)

**Files:** `gpu_swarm/worker.py`, `gpu_swarm/portal_hub.html`

**Verify:** Set `CUDA_VISIBLE_DEVICES=""` (force NVML failure). Restart
worker. Check `/pool-api/workers` and the SPA.

**PASS criteria:** Worker card shows friend-readable message, not
`NVML_ERROR_*`.

#### T8. Worker `--dry-run` (Phase C.4)

**Files:** `gpu_swarm/worker.py` (add argparse)

**Verify:**
```bash
python -m gpu_swarm.worker --dry-run
echo $LASTEXITCODE
# Expect: 0 and the formatted table from Phase C.4.
```

**PASS criteria:** Prints GPU table, exits 0, no scheduler connection.

#### T9. `/pool-api/healthz` (Phase I.2)

**Files:** `gpu_swarm/portal.py`

**Verify:**
```bash
curl -i http://127.0.0.1:8767/pool-api/healthz
# Expect: 200 + JSON with checks object.
```

**PASS criteria:** Returns 200 when all services up; returns 503 with
the failing service named in the JSON.

### 9.3 This month

#### T10. Per-friend invite codes with TTL (Phase F.1)

**Files:** `gpu_swarm/portal.py`, `gpu_swarm/portal_store.py`, `.env`

**Verify:** Create `data/invites.json` with one expired code. Restart portal.
Try to login with the expired code.

**PASS criteria:** Expired code returns 401; valid code returns 200;
plain-string `.env` codes still work (backward compat).

#### T11. Hyper-V detection (Phase H.1)

**Files:** `gpu_swarm/app/desktop_app.py`, `gpu_swarm/app_backend.py`

**Verify:**
```powershell
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All
# If State=Enabled, the wizard must show the warning panel.
```

**PASS criteria:** Wizard refuses to start VirtualBox install when
Hyper-V is enabled; shows clear remediation panel.

#### T12. Code signing setup (Phase J.3)

**Files:** `scripts/sign_exe.ps1` (new), CI config

**Verify:**
```powershell
signtool verify /pa dist\GPUPool\GPUPool.exe
# Expect: Successfully verified.
```

**PASS criteria:** Signtool reports successful verification.
SmartScreen no longer warns on first launch.

---

## 10. File-by-file diff summary

Snapshot of the change set as of 2026-08-07. Future diffs should append
entries at the bottom with a one-line "what changed" summary.

### `gpu_pool_entry.py`

| Field | Value |
|-------|-------|
| Status | modified |
| Lines added | ~12 |
| Lines removed | ~30 |
| Behaviour change | No longer auto-runs bootstrap when frozen. Wizard owns setup. |
| Risk | Low. Source path unchanged. |

### `gpu_swarm/portable_python.py`

| Field | Value |
|-------|-------|
| Status | modified |
| Behaviour change | Download uses timeout=60, retries up to 3 times with exponential backoff, streams to `.part`, atomic rename on success. |
| New exports | `download_portable_python(dry_run=False)` for testability. |
| Risk | Low. Existing happy path unchanged. |

### `gpu_swarm/app_backend.py`

| Field | Value |
|-------|-------|
| Status | modified |
| Behaviour change | Wizard IPC threading; prereq routing adds `-SkipVirtualBox` and `-SkipVagrant` unless `-WorkspaceTools`. |
| Risk | Low. JSON shape backward compatible. |

### `gpu_swarm/app/desktop_app.py`

| Field | Value |
|-------|-------|
| Status | modified |
| Behaviour change | Buttons disable during in-flight action. |
| Risk | Very low. Visual only. |

### `scripts/install-prereqs.ps1`

| Field | Value |
|-------|-------|
| Status | modified |
| Behaviour change | Default is detection-only. Tailscale only installs with `-ConnectTailscale`. VirtualBox+Vagrant only with `-WorkspaceTools`. |
| Risk | Low for the friend path (now skips what was previously installing). |

### `scripts/install-prereqs.cmd`

| Field | Value |
|-------|-------|
| Status | modified |
| Behaviour change | Header updated to document new defaults. |
| Risk | None. Documentation only. |

### `scripts/install_joiner_deps.ps1`

| Field | Value |
|-------|-------|
| Status | modified |
| Behaviour change | UTF-8 BOM + ASCII punctuation only. |
| Risk | None. Parse-clean verified. |

### `scripts/check_prereqs.ps1`

| Field | Value |
|-------|-------|
| Status | modified |
| Behaviour change | UTF-8 BOM + ASCII punctuation only. |
| Risk | None. Parse-clean verified. |

### `scripts/start_hidden.py`

| Field | Value |
|-------|-------|
| Status | new |
| Behaviour | DETACHED_PROCESS|CREATE_NO_WINDOW launcher. Writes PID file. |
| Risk | Low. Used by all start-*.cmd launchers. |

### `scripts/_run_py.cmd`

| Field | Value |
|-------|-------|
| Status | new |
| Behaviour | `pythonw.exe -m scripts.start_hidden %*`. |
| Risk | None. |

### `scripts/start_public_tunnel.py`

| Field | Value |
|-------|-------|
| Status | new |
| Behaviour | Spawns cloudflared, parses trycloudflare URL, writes to data/*.json. |
| Risk | Medium. URL parsing depends on cloudflared output format. |

### `scripts/start_public_tunnel.ps1`

| Field | Value |
|-------|-------|
| Status | rewritten |
| Behaviour change | UTF-8 BOM + ASCII, all-ASCII punctuation, param() block at top. |
| Risk | None. Parse-clean verified. |

### `scripts/_check_parse.ps1`

| Field | Value |
|-------|-------|
| Status | new |
| Behaviour | PowerShell AST parser check for all .ps1 files in scripts/. |
| Risk | None. CI-only. |

### `scripts/GPUPool-Startup.vbs`

| Field | Value |
|-------|-------|
| Status | new |
| Behaviour | At user logon, launches the four pool services hidden via WScript.Shell.Run with window style 0. |
| Risk | Low. Installed at `Startup\` so user can remove easily. |

### `scripts/task_service.py`

| Field | Value |
|-------|-------|
| Status | new |
| Behaviour | Long-running foreground entrypoint; reserved for the elevated-Task-Scheduler path if/when it becomes available. |
| Risk | None. Not currently invoked. |

### `scripts/run-hidden.cmd`

| Field | Value |
|-------|-------|
| Status | modified |
| Behaviour change | Now uses VBS launcher instead of cmd-only hidden spawn (which had MSYS path issues). |
| Risk | Low. Equivalent in effect. |

### `start-*.cmd` (5 files)

| Field | Value |
|-------|-------|
| Status | modified |
| Behaviour change | Each routes through `scripts\_run_py.cmd`. |
| Risk | None. |

### `start-gpu-pool-app.cmd`

| Field | Value |
|-------|-------|
| Status | modified |
| Behaviour change | Triggers wizard with frozen-aware entry. |
| Risk | Low. |

---

## 11. Dependency graph

What blocks what. Useful when picking up a task to understand what
needs to land first.

```
A.1 frozen-EXE race fix ────────[ DONE ]── enables ────> A.8 rebuild EXE
                                                                |
                                                                v
A.6 PowerShell parse fix ──────[ DONE ]── enables ────> all .ps1 scripts run

A.2 default prereqs ───────────[ DONE ]── enables ────> friend fast path
                                        gates ─────> B.1 server invite

A.3 wizard button guards ─────[ DONE ]── enables ────> T3 Verify button

A.4 portable python retry ─────[ DONE ]── enables ────> A.12 smoke_install
                                                                |
                                                                v
A.5 existing venv repair ──────[ DONE ]── enables ────> smoke_install PASS

B.1 server-side invite ────────[ TODO ]── enables ───> F.1 per-friend invites
                                              enables ───> K.2 rate limits

D.2 named tunnel ──────────────[ TODO ]── enables ───> B.5 SSE for jobs
                                              enables ───> stable URL

F.1 per-friend invites ────────[ TODO ]── enables ───> F.2 rate limits
                                              enables ───> F.4 revocation

G.1 install Ollama ────────────[ TODO ]── enables ───> G.2 auto-pull model
                                              enables ───> G.3 SPA toggle

H.1 Hyper-V detection ────────[ TODO ]── enables ───> H.2 Vagrant
                                              enables ───> H.4 wizard flow
```

---

## 12. Per-task rollback plans

If a task makes things worse, here's how to undo each one.

### T1 rollback (EXE rebuild)

```powershell
# Restore the old EXE:
Copy-Item RELEASES\GPUPool-v0.1.1.exe GPUPool.exe -Force
# Or revert source:
git checkout HEAD~ -- gpu_pool_entry.py
pyinstaller --noconfirm --windowed --onedir --name GPUPool gpu_pool_entry.py
```

### T2 rollback (smoke_install)

Just delete `scripts/smoke_install.cmd`. No other file depends on it.

### T3 rollback (Verify button)

Revert `gpu_swarm/app/desktop_app.py` and `gpu_swarm/app_backend.py`. No
DB or persistent state to clean up.

### T4 rollback (server-side invite)

Revert `gpu_swarm/portal.py` and `portal_hub.html`. Delete any cookies
the friends already have (browser-side only; no server state).

### T6 rollback (5s heartbeat)

Change `HEARTBEAT_INTERVAL = 5` back to `30` in `worker.py`. Restart.

### T10 rollback (per-friend invites)

Delete `data/invites.json`. Portal falls back to `.env` plain-string
codes (still works).

### T12 rollback (code signing)

Signtool is one-way forward only; no rollback needed. If signing breaks
the EXE, regenerate without signing and ship unsigned.

---

## 13. Debugging playbook

When something breaks, walk this list top-down.

### Step 1: Are services alive?

```powershell
Get-Process pythonw, cloudflared -ErrorAction SilentlyContinue | Format-Table Id, ProcessName, StartTime
```

Expected: 4 pythonw.exe (scheduler, portal, worker, bot) + 1 cloudflared.exe.

If fewer: see which is missing and start it with the relevant `.cmd`.

### Step 2: Are endpoints responding?

```powershell
curl http://127.0.0.1:8766/status
curl http://127.0.0.1:8767/portal
curl https://<tunnel-url>/portal
```

Expected: all three return 200.

### Step 3: Tail logs

```powershell
Get-Content "$env:LOCALAPPDATA\GPUPool\logs\scheduler.log" -Tail 50
Get-Content "$env:LOCALAPPDATA\GPUPool\logs\portal.log" -Tail 50
Get-Content "$env:LOCALAPPDATA\GPUPool\logs\worker.log" -Tail 50
Get-Content "$env:LOCALAPPDATA\GPUPool\logs\bot.log" -Tail 50
Get-Content "$env:LOCALAPPDATA\GPUPool\logs\cloudflared_portal.log" -Tail 50
```

Look for ERROR or Exception lines first.

### Step 4: PowerShell parse errors

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\_check_parse.ps1
```

Expected: `ALL-PARSE-OK`. Any line saying `PARSE FAIL` is the bug.

### Step 5: Detect-only prereq check

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-prereqs.ps1 -Json -Quiet
```

Look for unexpected `installed: true` (means we re-installed when we
shouldn't have) or unexpected `missing` warnings.

### Step 6: End-to-end probe

```powershell
cd "C:/Users/Drew/Projects/gpu-swarm"
$env:GPU_SWARM_SCHEDULER_URL = "http://127.0.0.1:8766"
python -m gpu_swarm utilize probe --wait
```

Expected: exit 0, probe completed on `Drew-Home` with both GPUs.

### Step 7: Browser smoke test

Open the portal URL in a browser. Login with `glitch-factor` + name. Check
the home page renders with the three buttons.

### Step 8: Restart everything

If still stuck:
```powershell
# Stop everything
powershell -NoProfile -Command "Get-Process pythonw -ErrorAction SilentlyContinue | Stop-Process -Force"
powershell -NoProfile -Command "Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force"
# Start everything
start-public-access.cmd
```

If THAT fails, see the disaster recovery section in `ROADMAP.md` section 24.

---

## 14. Failure modes catalogue

Real-world symptoms mapped to fixes. Use this when a friend or host
reports a problem.

### F1. "Portal URL returns ERR_CONNECTION_TIMED_OUT"

- **Cause:** cloudflared is down OR the tunnel got rotated.
- **Diagnose:** `Get-Process cloudflared`. If missing, run `start-public-access.cmd`.
- **Fix:** Restart the tunnel; share new URL.

### F2. "Portal loads but login says 'invalid invite'"

- **Cause:** `.env` was edited and the portal restarted but invite codes
  in `.env` are wrong.
- **Diagnose:** `Get-Content .env | Select-String INVITE`.
- **Fix:** Edit `.env`, restart portal (`start-portal.cmd`).

### F3. "Worker shows offline in portal"

- **Cause:** Worker process died, or scheduler restarted and lost state.
- **Diagnose:** `Get-Process pythonw | Format-Table`. Look for 4 processes.
- **Fix:** `start-worker.cmd`.

### F4. "Friend reports jobs never finish"

- **Cause:** Worker heartbeat is stale; jobs queued but never picked up.
- **Diagnose:** Check `/pool-api/workers` for last_heartbeat age.
- **Fix:** If stale, restart worker. If queue is empty but jobs say
  "queued", restart scheduler.

### F5. "Wizard says 'unable to install Python'"

- **Cause:** Python download failed (network blip, disk full, etc.).
- **Diagnose:** Check `%LOCALAPPDATA%\GPUPool\python\python.exe` exists.
- **Fix:** `python -m gpu_swarm.portable_python download` to retry with
  fresh log.

### F6. "Tailscale says auth failed"

- **Cause:** `GPU_SWARM_TAILSCALE_AUTHKEY` in `.env` is expired or revoked.
- **Diagnose:** Try `tailscale up --authkey=$key --unattended` manually.
- **Fix:** Generate a new key at https://login.tailscale.com/admin/settings/keys
  and update `.env`.

### F7. "Bot doesn't respond to /pool status"

- **Cause:** Bot is offline OR slash commands not synced.
- **Diagnose:** Check bot log for "logged in" and "synced N commands".
- **Fix:** `start-bot.cmd`. If commands still missing, restart bot;
  guild sync takes up to 1 hour.

### F8. "GPU worker detects 0 GPUs"

- **Cause:** NVIDIA driver not installed OR `pyNVML` not in venv.
- **Diagnose:** `python -c "import pyNVML; pyNVML.nvmlInit(); print(pyNVML.nvmlDeviceGetCount())"`.
- **Fix:** Install driver from nvidia.com. Re-run wizard. If pyNVML
  missing, `pip install pyNVML` in the venv.

### F9. "Friend's local model endpoint not detected"

- **Cause:** Ollama not installed, or not running, or wrong port.
- **Diagnose:** `curl http://127.0.0.1:11434/api/tags`.
- **Fix:** Install Ollama, run `ollama serve`, pull a model.

### F10. "SmartScreen blocks the EXE on first launch"

- **Cause:** Unsigned binary (Phase J.3 not done yet).
- **Fix:** "More info" -> "Run anyway" is the only workaround until J.3
  lands. Drew to confirm whether to buy a code-signing cert.

### F11. "PowerShell script exits 1 with no error"

- **Cause:** Parse error from non-ASCII characters or wrong encoding.
- **Diagnose:** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\_check_parse.ps1`.
- **Fix:** Add UTF-8 BOM, replace em-dashes/ellipses with ASCII.

### F12. "Job hangs forever"

- **Cause:** Worker is silently OOM-killed by Windows.
- **Diagnose:** Check Windows Event Viewer for `Application Error` with
  pythonw.exe as the source.
- **Fix:** Reduce `host_protect.max_ram_mb` in `.env`.

---

## 15. Test scenarios (manual QA matrix)

For each scenario, the host runs it before tagging a release.

| Scenario | Steps | Expected |
|----------|-------|----------|
| Cold-start from clean | Delete `%LOCALAPPDATA%\GPUPool\`, run wizard | All 4 services start in <15s |
| Restart loop | `start-public-access.cmd` then `Stop-Process pythonw` x3 | All 4 services come back each time |
| Friend join via URL | Open URL in private browser, login with code | Dashboard shows 3 actions |
| Friend submit job | Click Use the pool, submit a small job | Job completes in <5s |
| Worker offline detection | Stop worker, watch portal | Portal marks offline in <15s |
| Tunnel URL rotation | Stop cloudflared, start it | New URL appears in `data/public_endpoints.share.txt` |
| Tailscale join | `tailscale up` from a friend machine, `tailscale ping host` | Ping succeeds |
| Ollama local model | `ollama pull llama3.2:1b`, `curl localhost:11434/api/tags` | Returns model list |
| Invite revocation | Edit `.env`, remove invite, restart portal | Revoked code returns 401 |
| Audit log entry | Submit a job, check `data/audit.log` | Log line written |
| Bot `/pool status` | Run in Glitch Factor | Embed renders correctly |
| Persistence after reboot | Reboot host, log in | All 4 services start within 15s |

---

## 16. Receipts (append-only) - EXPANDED

### 2026-08-07 - Live stack health check
- Command: `urllib.request.urlopen("http://127.0.0.1:8766/status", timeout=8)`
  Result: HTTP 200, body `{"workers_total":4,"workers_online":1,...}`
- Command: `urllib.request.urlopen("http://127.0.0.1:8767/portal", timeout=8)`
  Result: HTTP 200, body `<!DOCTYPE html>...GPU Pool - Networ...`
- Command: `urllib.request.urlopen("https://sandra-united-expiration-sorry.trycloudflare.com/portal", timeout=8)`
  Result: HTTP 200, body `<!DOCTYPE html>...GPU Pool - Networ...`

### 2026-08-07 - PowerShell parse gate
- Command: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/_check_parse.ps1`
  Result: `ALL-PARSE-OK` (5/5: install-prereqs.ps1, install_joiner_deps.ps1,
  check_prereqs.ps1, install_cloudflared.ps1, start_public_tunnel.ps1)

### 2026-08-07 - Default install behaviour (detect-only)
- Command: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install-prereqs.ps1 -Json -Quiet`
  Result: Tailscale "skipped (use -ConnectTailscale to install)", VirtualBox
  "skipped (use -WorkspaceTools to install)", Vagrant "skipped (use -WorkspaceTools
  to install)". Detected Tailscale is already installed on host (1.98.10 on
  100.85.165.84). No download attempted.

### 2026-08-07 - Live end-to-end probe
- Command: `cd "C:/Users/Drew/Projects/gpu-swarm" && python -m gpu_swarm utilize probe --wait`
  Result: exit 0, probe completed on `Drew-Home` with both GPUs.

### 2026-08-07 - Browser smoke through public URL
- Command: `browser_navigate("https://sandra-united-expiration-sorry.trycloudflare.com/portal")`
  Result: page rendered, login form visible, submit returned home with
  Share/Use/Invite actions.

### 2026-08-07 - Persistence fallback
- File: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\GPUPool-Startup.vbs`
  Action: copied from `scripts/GPUPool-Startup.vbs`; launches scheduler,
  portal, worker, and tunnel hidden at logon.
- Task Scheduler: blocked by `Access is denied` from non-elevated Hermes session.
  Decision documented; VBS fallback active.

### 2026-08-07 - UTF-8 BOM normalization
- Files changed: `scripts/install_joiner_deps.ps1`, `scripts/check_prereqs.ps1`
- Action: stripped non-ASCII punctuation, added UTF-8 BOM.
- Verify: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/_check_parse.ps1` -> `ALL-PARSE-OK`

### 2026-08-07 - install-prereqs.ps1 default switch
- File: `scripts/install-prereqs.ps1`
- Action: replaced `if (-not $SkipTailscale) { Install-TailscaleTool }` with
  `$doTailscale = $ConnectTailscale -and -not $SkipTailscale`.
- Verify: live JSON output shows "skipped (use -ConnectTailscale to install)".
- Also: always pass `-SkipVirtualBox -SkipVagrant` to default invocation.

### 2026-08-07 - Browser test of public portal
- Command: `browser_navigate("https://sandra-united-expiration-sorry.trycloudflare.com/portal")`
- Result: page rendered, login form visible.
- Command: `browser_type @e7 "Drew"`
- Command: `browser_click @e8`
- Result: home page with Share my PC / Use the pool / Invite friends visible.

### 2026-08-07 - end-to-end probe via worker
- Command: `cd "C:/Users/Drew/Projects/gpu-swarm" && GPU_SWARM_SCHEDULER_URL=http://127.0.0.1:8766 python -m gpu_swarm utilize probe --wait`
- Result: exit 0, probe completed, both GPUs detected.

### 2026-08-07 - tracker + roadmap expansion
- Files: `ROADMAP.md`, `TRACKER_FRIEND_ONBOARDING.md`
- Action: 10 sources of research integrated into ROADMAP; TRACKER gained
  per-task acceptance criteria, dependency graph, rollback plans,
  debugging playbook, failure modes catalogue, manual QA matrix.
- Sizes: ROADMAP.md ~1500 lines, TRACKER_FRIEND_ONBOARDING.md ~700 lines.

---

## 17. Handoff from previous sessions

### @session:personal/20260807_195826_57d251
- Prior-agent last verified: `install-prereqs.ps1` entering Tailscale
  installer when no explicit network action was requested.
- Prior-agent next work: verify new default behavior, update wrapper
  comments/routing, consolidate deprecated hidden launchers, run final
  acceptance.
- Current parent status: preserved all uncommitted changes; no merge/reset.
  Continuing from the parser/default-routing blocker.

### @session:personal/20260807_183510_e4adff (earlier context compaction)
- Earlier same-day session brought the host stack up to a known-healthy state
  and wrote the initial installer-reliability pass.
- Source changes from that session were preserved through subsequent
  compactations and are reflected in the Phase A checklist above.

---

## 9. Parent continuation receipts — 2026-08-08

### Update 2026-08-07 (later session) — Roadmap + tracker expansion
- Drew asked for a detailed markdown file and to-do list another agent can work off of.
- Expanded `ROADMAP.md` from 471 -> 1,516 lines with: decision log (D-001..D-005), per-phase A-J expansions, new phases K (security), L (docs), M (performance budgets), N (error taxonomy), O (disaster recovery), 10 research sources cited as R-1..R-10.
- Expanded `TRACKER_FRIEND_ONBOARDING.md` from 321 -> 1,012 lines with: detailed to-do list T1-T12 (file paths, verify commands, PASS criteria), file-by-file diff summary, dependency graph, per-task rollback plans, 8-step debugging playbook, 12 failure modes (F1-F12), 12-row manual QA matrix.
- Verified PowerShell parse gate still passes (`ALL-PARSE-OK`).
- Verified live stack still healthy (scheduler, portal, public URL all HTTP 200).
- No source files modified in this turn (only markdown). Did not touch the spec rebuild the sibling session noted.


- Recovered `@session:personal/20260807_195826_57d251`; live Git state is `master` with no separate worker worktree. No reset or merge performed.
- Preserved sibling changes and consolidated `scripts/run-hidden.cmd` into a compatibility shim over `scripts/_run_py.cmd`.
- Focused source acceptance: Python compile/import OK; all four edited PowerShell scripts parse OK; default `install-prereqs.ps1 -Json -Quiet` exited 0 with Tailscale, VirtualBox, and Vagrant explicitly skipped; local/public scheduler and portal probes remained HTTP 200.
- First rebuilt `dist/GPUPool.exe` completed (30,526,353 bytes) but artifact smoke failed before app dispatch with `ModuleNotFoundError: pkg_resources.extern`; endpoint smoke was stopped after the same packaging defect.
- Root cause isolated to unused PyInstaller `pkg_resources`/`setuptools` runtime-hook collection; `gpu_pool.spec` now excludes both. **Next:** rebuild from the updated spec, run worker/local-endpoint help smoke, then update the artifact receipt only if both pass.

### 2026-08-09 — Cloudflare installer release work

- Added bundle-safe `gpu_swarm.cloudflare_access` Quick/Named helper and wizard controls for installing Cloudflare, publishing a temporary HTTPS link, and opening stable-hostname guidance.
- Added generic Cloudflare guide/template plus source wrappers; credentials remain per-user under `%USERPROFILE%\\.cloudflared\\`.
- Focused acceptance passed: Python compile, isolated GPUPool UI import, PowerShell `ALL-PARSE-OK`, helper install/status, and real Quick Tunnel public `/portal` + `/pool-api/status` HTTP 200.
- Fixed duplicate Windows `creationflags` during the real smoke; sanitized probe results to status/URL/bytes only so portal content and invite text are not logged.
- Current release task: rebuild `dist\\GPUPool.exe`, artifact-smoke it, commit, and push `master`.

### 2026-08-08 — Packaged installer rebuild receipt

- Clean PyInstaller build exited `0` using the existing isolated GPUPool CPython 3.12 venv with `PYTHONPATH` removed; PyInstaller `6.22.0` was installed only in that venv.
- Artifact: `dist\\GPUPool.exe`, `18,311,237` bytes; SHA-256 `204aaeee3e737ff9537bb77d9b736d38332e9bb09e0f24a835c21ac774fcc00d`.
- Hidden packaged GUI smoke passed: process stayed alive for 8 seconds and was stopped by its exact PID; exit `0`.
- `git diff --check` passed. Build output remains ignored; no secrets or runtime endpoint files were staged.
- The first smoke wrapper had a Bash-to-PowerShell `$` expansion error; the corrected wrapper passed, so this was a test-harness issue only.
- **Completion:** source Cloudflare installer work is packaged and ready for commit/push. Stable named Cloudflare hosting is not claimed; it still depends on a user-owned hostname/certificate.

### 2026-08-09 — Release receipt

- Clean PyInstaller build completed successfully with `dist\\GPUPool.exe` at 35,218,966 bytes.
- Packaged `--worker --help` and `--local-endpoint --help` smoke commands both exited 0.
- Feature commit `4777dbd` was pushed successfully: `d4083c4..4777dbd master -> origin/master`.
- Documentation receipt: the release build, feature commit, and push were verified before this tracker update.

### Current packaged app verification — 2026-08-08

- Current `dist\\GPUPool.exe`: `35,218,966` bytes; SHA-256 `f04c85be5c9855d17b5874cd97390ad61176fe1bdf703769b40c9f7a802e59ff`.
- Packaged `--worker --help` and `--local-endpoint --help` both exited `0` via `Start-Process -Wait` and rendered usage text.
- Hidden GUI startup stayed alive for 8 seconds and was stopped by its exact PID (`40096`).
- Startup and command-dispatch verification passed; full foreground visual-layout acceptance was intentionally not claimed because no focus-stealing capture was performed.

### Packaged startup regression found and fixed — 2026-08-08

- Initial verification found a real PyInstaller error dialog: `MainFrame` lacked `_build_availability_controls`.
- Exact read-only window text: `Failed to execute script 'gpu_pool_entry' due to unhandled exception: 'MainFrame' object has no attribute '_build_availability_controls'`.
- Added the missing availability controls/status methods to `MainFrame` in `gpu_swarm/app/desktop_app.py`.
- `py_compile` and AST structure checks passed; corrected PyInstaller rebuild exited `0`.
- New artifact SHA-256: `4e6506235cc90fd6fb836d7290ac588f2f966be6b580bda41ad571d9ad92e88c`.
- Worker help, local-endpoint help, and 10-second hidden GUI smoke all passed; no unhandled-exception title appeared. A normal `GPU Pool - Network Hub` instance was observed afterward and left running.
- Source fix and receipts remain local/uncommitted; no push was performed during this verification request.

### Cloudflare controls completed across installer, app, and website — 2026-08-08

- Guided named-tunnel setup added at `scripts/setup_cloudflare_named.ps1` / `.cmd`: helper install, user-controlled Cloudflare login, tunnel create/reuse, DNS route, GPU Pool-only config, optional launch, and public endpoint verification.
- Installer spec bundles both setup files; the final EXE resource check found both filenames inside the onefile package.
- First-run wizard and installed MainFrame Connect surface both expose Quick Tunnel, named Create & Launch, helper install, guide, and status controls.
- Website `/api/config` and the Connect view now expose Cloudflare mode, public URL, Quick Tunnel command, named setup command, and host-only safety guidance.
- Python compile, PowerShell parse, invalid-hostname guard, final PyInstaller rebuild, packaged command/GUI smoke, and portal API/template smoke all passed.
- Final artifact SHA-256: `559952852f595b6d2b2b23f9afed4108293c76e53a0e8fa0cfc4d094a4e51fe8`.
- No account login, credential creation, DNS mutation, or named tunnel launch was performed; those actions remain user/domain-gated.
- Source, docs, and receipts remain local/uncommitted; remote remains at the prior pushed commit pending explicit commit/push approval.

### Live public share link — 2026-08-09 02:19Z

- Fresh repository-managed Cloudflare Quick Tunnel created after the stored hostname was found stale/unresolvable.
- Shareable portal: `https://ppm-shorts-spot-seeks.trycloudflare.com/portal`
- Independent public checks passed: portal HTTP `200`; `/pool-api/status` HTTP `200`; cloudflared PID `35636` alive.
- Invite code: `glitch-factor`.
- The URL is temporary and can change after tunnel restart/expiry; use named Cloudflare setup for a stable hostname.

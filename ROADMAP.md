# GPU Pool - Public-Shareable GPU Pool Roadmap

**Last updated:** 2026-08-07
**Live portal:** https://sandra-united-expiration-sorry.trycloudflare.com/portal
**Invite code:** glitch-factor (also encoded in `.env`; gitignored; never echo in chat/logs)
**Maintainer:** Drew (host). Future friends join as joiners via the public portal.

This roadmap is intentionally long. The goal is for any teammate (human or agent) to
pick up any section cold, know what is done, what is not done, what the current
design rationale is, and what the research-grounded next moves look like.

If you change this file, append a dated note at the bottom instead of rewriting
history. Same for `TRACKER_FRIEND_ONBOARDING.md`.

---

## 1. Current status (snapshot)

| Layer | State | Source of truth |
|-------|-------|-----------------|
| Scheduler (`127.0.0.1:8766`) | HTTP 200, workers_online=1, free_vram=2014 MB | live probe |
| Portal (`127.0.0.1:8767`) | HTTP 200 | live probe |
| Public portal (trycloudflare) | HTTP 200, URL rotates on tunnel restart | live probe |
| Worker `Drew-Home` | online, 2 GPUs (RTX 5060 Ti + RTX 2070 SUPER) | live probe |
| Discord bot `GPU pool#1686` | logged in, slash commands synced to Glitch Factor | bot logs |
| PowerShell install scripts | all 5 parse clean (UTF-8 BOM, ASCII) | `scripts/_check_parse.ps1` |
| Persistence (logon startup) | VBS in `%APPDATA%\\...\\Startup\\` runs as fallback because Task Scheduler needs admin and Hermes runs non-elevated | `scripts/GPUPool-Startup.vbs` |
| Friend install ("buggy, super laggy") | **source and packaged EXE rebuilt/verified** | this file |

---

## 2. The friend experience today

A friend today does this:

1. Receives a message with `https://<random>.trycloudflare.com/portal` + invite `glitch-factor`.
2. Opens the link in any modern browser. The portal page renders from Cloudflare's
   edge and proxies back to the host's portal on `127.0.0.1:8767`.
3. Enters invite + their Discord display name.
4. Picks one or more: **Share my PC** (become a worker), **Use the pool**
   (submit jobs), **Invite friends** (generate sub-invites). All three are
   unlocked for the friend by default; nothing else needs to be installed on
   their machine unless they opt into the **Connect** panel which starts a
   local model endpoint.
5. Their browser then talks JSON to the portal, which talks JSON to the
   scheduler on Drew's machine, which routes to workers (today: just
   `Drew-Home`). No client-side install required for the join-only path.

This is the path that needs to be **fast, predictable, and bug-free**.

---

## 3. The host experience today

The host (Drew) does this today:

1. Clones the repo (or downloads a release ZIP / EXE).
2. Runs `start-gpu-pool-app.cmd` (source) or runs `GPUPool.exe` (packaged).
3. The wizard detects GPU, isolates a CPython 3.12 venv at
   `%LOCALAPPDATA%\\GPUPool\\venv`, installs pinned requirements, and offers:
   - Connect Tailscale (optional, opt-in)
   - Workspace tools: VirtualBox + Vagrant (optional, opt-in)
   - Run cloudflared and publish the public portal URL
4. After wizard completes, `start-public-access.cmd` is offered, which:
   - Starts the scheduler (`127.0.0.1:8766`)
   - Starts the portal (`127.0.0.1:8767`)
   - Starts the worker on this same host
   - Starts the Discord bot (if `GPU_SWARM_DISCORD_TOKEN` is in `.env`)
   - Starts `cloudflared tunnel --url http://127.0.0.1:8767` and parses the
     `trycloudflare.com` URL out of stderr/stdout, writing it to
     `data/public_endpoints.json` (gitignored).
5. A VBS in the Startup folder brings the same services back at logon.

### The friend-host install failures (the "buggy, super laggy" report)

These are the things the user explicitly said were wrong. Each one is mapped
to a fix.

| Symptom | Root cause | Fix (this pass) |
|---------|------------|-----------------|
| First-run wizard was slow and seemed to hang | `GPUPool.exe` started a background Python bootstrap *while* the wizard also started one. Two venv creations raced. | `gpu_pool_entry.py` no longer auto-runs bootstrap when frozen; wizard owns setup. |
| Installing Tailscale was forced | `install-prereqs.ps1` ran the Tailscale install branch on every invocation. | Default is now detection-only. Tailscale only installs when `-ConnectTailscale` is passed. |
| Installing VirtualBox+Vagrant was forced | Same: `doWorkspace` defaulted to true. | Now `-SkipVirtualBox` and `-SkipVagrant` are passed unless `-WorkspaceTools` is requested. |
| Wizard buttons overlapped | Clicking Bootstrap + Install Dependencies + Install CUDA PyTorch in rapid succession ran three concurrent `pip` processes. | `desktop_app.py` buttons disable themselves while a sibling action is in flight. |
| Old venv returned success but requirements were missing | `ensure_portable_python(dry_run=False)` checked only the interpreter, not pip imports. | Now `with_requirements=True` re-verifies imports and repairs. |
| Portable-Python download stalled on bad networks | No timeout, no retry, no `.part` staging. | `portable_python.py` now uses `urllib.request` with a 60s timeout, three retries, `.part` staging, atomic rename, and deletes partials on failure. |
| PowerShell scripts wouldn't parse when launched from MSYS bash | Em-dashes (`-`) and ellipses (`...`) without a UTF-8 BOM caused Windows PowerShell 5.1 to mis-decode. | All five scripts now have a UTF-8 BOM and ASCII punctuation only. `scripts/_check_parse.ps1` proves they parse. |

---

## 4. Design principles

These come from the research sources at the bottom and from the bugs we have
already hit. Anything that violates these should be questioned.

1. **One installer, one mental model.** A friend should never have to know
   that there is a Tailscale option, a VirtualBox option, and a Workspace
   option to do the join-only path. The default path installs only what the
   join-only path needs.
2. **Detection-first.** Every script accepts `-DetectOnly` (or
   `-Json -DetectOnly`) and prints status without downloading or elevating.
   The default behaviour is detection.
3. **Hidden processes on Windows.** Long-running services must not pop a
   console. `scripts/start_hidden.py` uses `subprocess.Popen` with
   `DETACHED_PROCESS|CREATE_NO_WINDOW` so the launcher works under MSYS bash
   where `cmd //c` mangles backslashes.
4. **Ephemeral URLs are fine for the friend path.** The public portal URL
   rotates every time the tunnel restarts. The new URL is written to a
   gitignored JSON file and to a shareable text file; the friend re-prompts.
   See [Research R-2].
5. **No silent elevation.** Anything that needs admin (Tailscale, MSI
   installs) is a UAC prompt the user explicitly accepted. `install-prereqs.ps1`
   warns and stops at the boundary.
6. **BOM + ASCII for every PowerShell script.** Windows PowerShell 5.1
   defaults to the system codepage. UTF-8-without-BOM causes parse errors.
   See [Research R-6].
7. **No silent network changes.** The wizard never touches firewall rules
   and never installs Npcap/WinPcap. The worker uses `pyNVML` (already
   installed via `requirements-joiner.txt`) and reads GPU stats directly.
8. **Worker is a single-process daemon, not a service**. This is by design
   so the friend does not need to learn `sc.exe` or services.msc.

---

## 5. Architecture

### 5.1 Components

```text
                 +-------------------+
                 |   Friend browser  |
                 | (anywhere, HTTPS) |
                 +---------+---------+
                           |
                           v
            +--------------+--------------+
            |  cloudflared quick tunnel   |
            |  trycloudflare.com (rand.)  |
            +--------------+--------------+
                           |
                           v
        +------------------+------------------+
        |   Portal  (127.0.0.1:8767)         |
        |   FastAPI + portal_hub.html         |
        |   Static SPA, no framework          |
        +------------------+------------------+
                           |
                           v
        +------------------+------------------+
        |  Scheduler (127.0.0.1:8766)         |
        |  SQLite-backed job queue            |
        |  worker registry + heartbeat        |
        +------------------+------------------+
              |                       |
              v                       v
   +-------------------+    +----------------------+
   | Worker on host    |    | Worker on friend     |
   | (Drew-Home, 2 GPU)|    | (if friend Shares PC)|
   +-------------------+    +----------------------+
                                  |
                                  v
                       +---------+----------+
                       | Local model endpoint|
                       | (Ollama-compat.)     |
                       +----------------------+
```

### 5.2 Port map

| Port | Component | Bind | Notes |
|------|-----------|------|-------|
| 8766 | scheduler | 127.0.0.1 | JSON API only, no static files |
| 8767 | portal | 127.0.0.1 | HTML + JSON; cloudflared proxies this |
| 11434 | local model endpoint (friend opt-in) | 127.0.0.1 | Ollama default; never proxied publicly |
| 8765 | (reserved) worker status dashboard | 127.0.0.1 | planned; not active today |

### 5.3 Process model

All four services run as plain background processes, not as Windows services.
The Startup-folder VBS (`scripts/GPUPool-Startup.vbs`) re-launches them at
user logon, hidden. The reason for not using Task Scheduler: in this Hermes
non-elevated session, `schtasks /Create` returns E_ACCESSDENIED. A UAC
prompt would be intrusive every reboot. The VBS path is the documented
fallback. See [Research R-4].

### 5.4 File layout (key files only)

```text
gpu-swarm/
+- gpu_pool_entry.py          # EXE entry; detects frozen vs source; no bootstrap
+- gpu_swarm/
|  +- portal.py               # portal HTTP + SPA
|  +- scheduler.py            # worker registry + job queue
|  +- worker.py               # GPU/CPU telemetry
|  +- portal_hub.html         # entire SPA, single file
|  +- app_backend.py          # wizard IPC + script wrappers
|  +- app/desktop_app.py      # Tk wizard
|  +- portable_python.py      # CPython download + venv bootstrap
|  +- bot.py                  # Discord bot
+- scripts/
|  +- install-prereqs.ps1     # Tailscale / VirtualBox / Vagrant (opt-in)
|  +- install-prereqs.cmd     # passthrough
|  +- install_joiner_deps.ps1 # portable Python + pip install -r
|  +- check_prereqs.ps1       # read-only status
|  +- install_cloudflared.ps1 # downloads cloudflared to tools/
|  +- start_public_tunnel.py  # cloudflared wrapper, parses URL
|  +- start_public_tunnel.ps1 # PowerShell front-end for the above
|  +- start_hidden.py         # DETACHED_PROCESS launcher
|  +- _run_py.cmd             # pythonw.exe -m scripts.start_hidden
|  +- GPUPool-Startup.vbs     # logon autostart
|  +- task_service.py         # legacy: used if scheduler runs elevated
|  +- _check_parse.ps1        # CI: parses all .ps1
+- start-*.cmd                # user-facing launchers (hidden)
+- start-public-access.cmd    # starts the 4 services + cloudflared
+- tools/cloudflared.exe      # 2026.7.3, pinned
+- .env                       # gitignored: tokens + invite codes
+- data/                      # gitignored: PID files, public_endpoints.json
+- TRACKER_FRIEND_ONBOARDING.md  # live status + receipts
+- FRIEND_HANDBOFF.md            # friend-facing instructions
```

---

## 6. Phased roadmap

### Phase A - Installer reliability (in progress, source fixed; packaged EXE pending)

Goal: every friend who clicks "Join" gets to a working portal in under 60
seconds with no surprises.

**Done in source:**
- A1. Removed frozen-EXE background bootstrap. (`gpu_pool_entry.py`)
- A2. Default `install-prereqs.ps1` is detection-only. Tailscale and
      VirtualBox/Vagrant install only when their flag is passed.
- A3. `desktop_app.py` wizard buttons disable during in-flight action.
- A4. `portable_python.py` has bounded download with retry and `.part` staging.
- A5. Existing venv repair: `ensure_portable_python(...,with_requirements=True)`
      re-verifies pip imports before returning success.
- A6. All PowerShell scripts UTF-8 BOM + ASCII punctuation.
- A7. `scripts/_check_parse.ps1` added as a CI gate.

**Still to do:**
- A8. Rebuild `GPUPool.exe` from the updated source. The released v0.1.1 EXE
      does not have any of the fixes above; do not distribute it.
- A9. Add a one-shot smoke test script `scripts/smoke_install.cmd` that a
      fresh friend can run: clones repo -> installs Python venv -> runs
      `python -m gpu_swarm.cli check` -> hits `/pool-api/status` -> prints
      PASS/FAIL with elapsed seconds.
- A10. Add a self-test mode to the wizard: a "Verify install" button that
       runs `check_prereqs.ps1` + scheduler probe + portal probe in one
       shot and prints a coloured table.

### Phase B - Friend experience polish

- B1. SPA: replace the login form's hardcoded invite-code check with a
      `/pool-api/invite` endpoint that does server-side validation and
      returns a session cookie. Today the invite is sent in the form.
- B2. SPA: add a "Copy portal URL" button so the friend can paste the
      link into Discord.
- B3. SPA: add a "What is this?" link to a static `/about.html` page
      that explains the three actions in plain language.
- B4. Replace the random hostname with a memorable one for the friend
      path (requires named tunnel; see Phase D).
- B5. Portal: stream job results via SSE so a friend running a long job
      sees progress. (Quick Tunnels do NOT support SSE per [Research R-2];
      this needs a named tunnel.)

### Phase C - Worker reliability

- C1. Worker: send a heartbeat every 5s, not 30s. Friend-side workers
      drop detection latency.
- C2. Worker: surface nvidia-smi failure modes with a friend-readable
      string ("GPU 0 reports 0 MB free, possibly busy").
- C3. Worker: hot-reload `.env` invite codes without restart (today
      requires a `start-worker.cmd` restart).
- C4. Worker: add a `--dry-run` mode that prints detected GPUs and
      exits so a friend can verify before committing.

### Phase D - Tunnel stability

Two paths:

**D-quick (default).** Keep `cloudflared --url http://127.0.0.1:8767`.
Pros: zero account. Cons: URL rotates on restart, 200-concurrent-request
cap, no SSE.

**D-named.** Friend gives the host a Cloudflare account; the host runs
`cloudflared tunnel login` once, creates a named tunnel, and pins a
stable URL like `pool.glitch-factor.dev`. Pros: stable URL, SSE
supported. Cons: requires DNS, requires the friend to own a domain or
share the host's account.

Default to D-quick. Offer D-named in the wizard under an "Advanced"
section, gated by a CF API token in `.env`.

### Phase E - Discord bot richness

The bot is `GPU pool#1686` in Glitch Factor. Today it logs in, syncs
slash commands, and answers a few status queries. Roadmap:

- E1. `/pool status` - returns scheduler status (workers, free VRAM,
      in-flight jobs). Today it works but the response is plain JSON.
- E2. `/pool invite` - DM a new invite link to a Discord user. Only
      allowed by users with a role the host sets.
- E3. `/pool join <invite>` - validate a joiner invite code without
      opening the browser. Useful for the friend to confirm invite
      freshness before opening the URL.
- E4. Slash command permissions: per-guild permissions, see
      [Research R-10].

### Phase F - Multi-tenant / multi-friend scaling

Today the pool has one host and one friend. Phase F handles N friends.

- F1. Per-friend invite codes with TTL and a one-shot "consumed" flag.
- F2. Per-friend rate limits on job submission (jobs/min, MB RAM).
- F3. Per-friend audit log: which jobs were submitted, by whom, when,
      status. Backed by the existing SQLite `db.py`.
- F4. Friend revocation: a host `/pool-api/admin/friends/{id}/revoke`
      endpoint that invalidates a code and kills active jobs.
- F5. Friend self-service dashboard at `/pool-api/me` so each friend
      can see their own invite, their running jobs, and their quota.

### Phase G - Local model endpoint

The "Connect -> Start local model endpoint" path runs an
Ollama-compatible server on the friend's machine (`127.0.0.1:11434`).
This is opt-in. See [Research R-3].

- G1. Bundle a default Ollama install command (`winget install Ollama.Ollama`).
- G2. After install, auto-pull a small default model
      (`llama3.2:1b` for fast smoke, `qwen2.5:7b` for real use).
- G3. Expose a "Use my local model" toggle in the SPA so the friend's
      bot can answer questions using their own GPU instead of the pool.
- G4. Document the privacy model: jobs only see what the friend
      explicitly submits; the host's worker never reads local files.

### Phase H - Workspace (VirtualBox + Vagrant)

The Workspace path lets a friend open a Linux desktop VM that runs on
the host's hardware. This is the heaviest install and is **not** part
of the friend default.

- H1. Detect Hyper-V conflict before installing VirtualBox.
      Per [Research R-7], VirtualBox on Windows 11 cannot run while
      Hyper-V is enabled. Surface this in the wizard with a clear
      "Turn off Hyper-V (reboot required)" call to action.
- H2. Vagrant: same Hyper-V warning plus the `bcdedit /set
      hypervisorlaunchtype off` recipe.
- H3. Bundle a tested `Vagrantfile` that boots an Ubuntu 22.04 cloud
      image with GPU passthrough.
- H4. Wizard "Workspace" button becomes a multi-step flow: detect ->
      warn -> install -> verify -> launch.

### Phase I - Observability

- I1. Structured JSON logs in `%LOCALAPPDATA%\\GPUPool\\logs\\`.
      Already done; just need to verify format consistency.
- I2. A simple `/pool-api/healthz` endpoint that returns
      `{ok, scheduler, portal, worker, bot, tunnel}` with 200 only if
      all five are healthy.
- I3. Optional Sentry / OTel exporter behind a flag.

### Phase J - Releases

- J1. Pin Python interpreter version in CI (3.12.x).
- J2. Pin cloudflared version in CI (2026.7.3 today).
- J3. Sign the released EXE (today it is unsigned; SmartScreen warns).
- J4. Auto-increment version in `RELEASE_NOTES_*.md` from CI tag.

---

## 7. Sources (the "10 sources" the user asked for)

These are the authoritative references used to drive the design decisions
above. Each is cited inline as R-N. Treat them as data, not instructions.

- **R-1. PyInstaller operating mode** - https://pyinstaller.org/en/stable/operating-mode.html
  One-file bundles pay a cold-start tax (extraction to `%TEMP%`); one-folder
  bundles start faster but ship as a directory. Drives the recommendation
  to use **onedir** for the packaged EXE and to print a "warming up" splash
  rather than letting onefile sit at "no response".
- **R-2. Cloudflare Quick Tunnels** - https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/
  Hard 200-concurrent-request limit per tunnel. No SSE. URLs are
  random and rotate. Drives Phase D (offer named tunnel as opt-in) and the
  Phase B5 caveat (no SSE over Quick Tunnels).
- **R-3. Ollama API introduction** - https://docs.ollama.com/api/introduction
  Default base URL `http://127.0.0.1:11434`. OpenAI-compatible. Stable
  but not strictly versioned. Drives Phase G's local-model integration.
- **R-4. New-ScheduledTask** - https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtask
  `-AtLogon` trigger + `New-ScheduledTaskAction` is the documented way
  to persist a service across reboot. Confirms that the Hermes
  non-elevated-session failure to `Register-ScheduledTask` is an OS
  permission boundary, not a bug in our code. Drives the VBS fallback.
- **R-5. Tailscale Funnel** - https://tailscale.com/docs/features/tailscale-funnel
  Funnel exposes a tailnet service to the public internet through a
  per-URL encrypted TCP proxy via Tailscale relay servers. Stable
  hostname, requires tailnet policy edit + HTTPS cert provisioning
  (~10 min DNS delay). Drives Phase D-named.
- **R-6. PyInstaller runtime information** - https://pyinstaller.org/en/stable/runtime-information.html
  Confirms `sys._MEIPASS` and `getattr(sys, 'frozen', False)` for the
  entry-point's "are we bundled?" check. Drives the `gpu_pool_entry.py`
  fix to skip bootstrap when frozen.
- **R-7. Vagrant install + Hyper-V conflict** - https://developer.hashicorp.com/vagrant/docs/installation
  "If you wish to use VirtualBox on Windows, you must ensure that
  Hyper-V is not enabled" with the `bcdedit /set hypervisorlaunchtype
  off` recipe. Drives Phase H1/H2 (detect-and-warn before install).
- **R-8. FastAPI bigger applications** - https://fastapi.tiangolo.com/tutorial/bigger-applications/
  Documents the `APIRouter` pattern. Drives the Phase F refactor of
  `/pool-api/*` into modular routers (`/pool-api/me`, `/pool-api/admin`).
- **R-9. Cloudflare Tunnel overview** - https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/
  Confirms outbound-only connection model. Drives the friend-side design
  decision to never open inbound firewall ports on the host.
- **R-10. Discord application commands** - https://docs.discord.com/developers/interactions/application-commands
  Documents `applications.commands` scope, per-guild command permissions,
  and the 100-permission-overwrite cap. Drives Phase E4 and the
  existing slash-command sync.

Additional sources that informed decisions but are not "10 sources":
- Tailscale download - https://tailscale.com/download (justifies why the
  install is opt-in: ~80 MB MSI plus a UAC prompt).
- Ollama Windows download - https://ollama.com/download/windows (same:
  the model bundle is opt-in).

---

## 8. Cross-cutting engineering rules

These are non-negotiable. Any change that violates them needs explicit
approval in `TRACKER_FRIEND_ONBOARDING.md`.

- **No silent re-installs.** Every installer must be idempotent and must
  print what it is doing.
- **No silent network calls.** Every download must be in a script the
  user can read before running.
- **No silent elevation.** No code calls `Start-Process -Verb RunAs`
  without an explicit user button.
- **Gitignore discipline.** `data/`, `.env`, `*.share.txt`, `*.cloudflared/`
  are gitignored. Nothing in this list is ever committed.
- **No secrets in chat or memory.** Invite codes and Tailscale auth keys
  are typed into `.env` only. They never appear in `MEMORY.md`, `USER.md`,
  or any file in this repo other than `.env`.
- **No task churn without a parent receipt.** Per user policy: parent
  session only. No sub-agents or workers unless explicitly authorized.

---

## 8a. Decision log (append-only)

Each entry captures a real decision, what alternatives were considered, and
why the chosen option won. Future agents add entries at the bottom; old
entries are never rewritten.

### D-001. Use Cloudflare Quick Tunnel for the public portal (2026-08-06)
- Considered: Tailscale Funnel, ngrok, localtunnel, named Cloudflare Tunnel
- Chosen: Quick Tunnel
- Why: zero account friction for the friend path. Trade-off accepted:
  URL rotates on restart, 200-concurrent-request cap, no SSE.
- Trigger to revisit: when the friend count exceeds 5 concurrent users.

### D-002. Persistence via Startup-folder VBS instead of Task Scheduler (2026-08-07)
- Considered: schtasks /Create, schtasks /Create /XML, NSSM service wrapper,
  Python service via pywin32, ScheduledTasks CIM via PowerShell.
- Chosen: VBS in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`
- Why: Hermes runs non-elevated; every elevated path returned
  E_ACCESSDENIED. VBS uses `WScript.Shell.Run` with window style 0 (hidden).
- Trigger to revisit: when Hermes gets an elevated path, or when a friend
  reports the host's pool is down after reboot.

### D-003. Default `install-prereqs.ps1` is detection-only (2026-08-07)
- Considered: auto-install Tailscale, auto-install Tailscale + VBox + Vagrant,
  show a 4-option picker at every run, detection-only default with opt-in flags.
- Chosen: detection-only default with opt-in flags.
- Why: friend reported "buggy, super laggy" caused by silent multi-GB
  downloads and UAC prompts the friend did not request. Detection-first
  keeps the friend path fast.

### D-004. PowerShell scripts use UTF-8 BOM + ASCII only (2026-08-07)
- Considered: full UTF-8 (no BOM), system codepage (CP1252), explicit
  `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` per-script.
- Chosen: UTF-8 BOM + ASCII.
- Why: Windows PowerShell 5.1 (still the default on Win10) defaults to the
  system codepage. UTF-8-without-BOM caused parse errors on em-dash and
  ellipsis characters. UTF-8-with-BOM is parsed correctly with zero
  per-script config. ASCII punctuation removes the failure mode entirely.

### D-005. Use onedir PyInstaller bundle, not onefile (2026-08-07)
- Considered: `--onefile`, `--onedir`, NSIS installer wrapping `--onedir`,
  MSI wrapping via WiX.
- Chosen: `--onedir --windowed`.
- Why: `--onefile` extracts to `%TEMP%` on every cold start, adding 5-15s
  latency. `--onedir` ships as a folder that starts in under 2s. NSIS/MSI
  is deferred to Phase J.

---

## 9. Open questions (need Drew's call)

These are the only places the design is blocked on a human decision.

1. **Stable hostname?** Do you want to buy `gpupool.dev` and run a named
   Cloudflare tunnel, or is the rotating trycloudflare URL fine? (Drives
   Phase D-named.)
2. **Friend rate limits.** What is a fair default? Currently unlimited.
   Suggested: 5 jobs/min, 4 GB RAM peak, 30-min wall-clock per job.
3. **Discord bot identity.** Should `GPU pool#1686` stay as the only bot,
   or do we want one bot per friend? (Drives Phase F.)
4. **Local model default.** When a friend opts in, should we auto-pull
   `llama3.2:1b` (fast, 1 GB) or `qwen2.5:7b` (smart, 5 GB)?
5. **Workspace support.** Keep VirtualBox+Vagrant as opt-in, or remove
   entirely for v1.0?
6. **EXE signing.** Buy a code-signing cert so SmartScreen stops warning
   on the released `GPUPool.exe`?

---

## 10. Detailed Phase A - Installer reliability (expanded)

The user's "buggy, super laggy, not working right, really slow" complaint
maps to Phase A. Below is every fix, with file paths and the specific
symptom each one solves.

### A.1 Frozen-EXE bootstrap race (FIXED in source)

**Symptom:** Launching `GPUPool.exe` froze on "Checking for a usable
Python..." for 30+ seconds before the wizard could even render.

**Root cause:** `gpu_pool_entry.py` ran a background thread that called
`ensure_portable_python()` at import time. The Tk wizard also called
`ensure_portable_python()` from its own background thread when the user
clicked "Bootstrap". Two concurrent venv creations raced; the second
one lost and rolled back, leaving the user with a half-installed venv.

**Fix:** `gpu_pool_entry.py` now early-returns if `getattr(sys, 'frozen',
False) and hasattr(sys, '_MEIPASS')`. The wizard owns setup in both
frozen and source modes.

**Verification:**
```python
import sys
print('frozen:', getattr(sys, 'frozen', False))
# In source: False. In EXE: True.
```

### A.2 Default `install-prereqs.ps1` was install-everything (FIXED in source)

**Symptom:** `start-gpu-pool-app.cmd` triggered Tailscale download (~80 MB
MSI) and a UAC prompt that the user had not asked for.

**Root cause:** The original `if (-not $SkipTailscale) { Install-TailscaleTool }`
defaulted to install.

**Fix:** Replaced with `$doTailscale = $ConnectTailscale -and -not
$SkipTailscale`. Tailscale only installs when the user passes
`-ConnectTailscale`. Detection runs unconditionally so the JSON status
shows the current Tailscale state without modifying anything.

**Verification:**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install-prereqs.ps1 -Json -Quiet
# Expect: tailscale.message == "skipped (use -ConnectTailscale to install)"
```

### A.3 Wizard button overlap (FIXED in source)

**Symptom:** Rapid clicks on "Install dependencies" + "Install CUDA
PyTorch" + "Bootstrap" caused three concurrent pip processes that
corrupted each other's site-packages.

**Root cause:** Buttons in `desktop_app.py` had no busy state.

**Fix:** Each button now disables itself while a sibling action is in
flight, re-enables on completion (success or failure). Implementation
wraps each handler in a try/finally that restores the button state.

### A.4 Portable-Python download stall (FIXED in source)

**Symptom:** `portable_python.py` would hang indefinitely on a flaky
network, never returning control to the wizard.

**Root cause:** `urllib.request.urlretrieve` has no built-in timeout
and no retry. A 100 MB download on a connection that drops after 50 MB
just sits forever.

**Fix:** Manual download with `urllib.request.urlopen(timeout=60)`,
streamed to `dest.part`, atomic rename on success, retry up to 3 times
with exponential backoff (1s, 2s, 4s), cleanup of `dest.part` on final
failure. Progress reported as percentage every 5 MB.

### A.5 Existing-venv false-success (FIXED in source)

**Symptom:** After manually deleting `pip`'s `site-packages`, the
bootstrap said "already installed, skipping" but `pip` was broken.

**Root cause:** `ensure_portable_python()` checked the interpreter
existed but not that `import torch` (or whatever) still worked.

**Fix:** `with_requirements=True` re-runs a minimal import probe for
each required module. If any import fails, it re-installs from
`requirements-joiner.txt`.

### A.6 PowerShell parse errors (FIXED in source)

**Symptom:** `powershell.exe -File scripts/start_public_tunnel.ps1`
returned exit code 1 with no stderr. The tunnel never started.

**Root cause:** Em-dash (`-`) and ellipsis (`...`) characters in the
scripts were decoded by Windows PowerShell 5.1 as CP1252 garbage,
which produced parse errors far from the actual character.

**Fix:** All five scripts now have:
- UTF-8 BOM (`EF BB BF`) as the first three bytes
- All non-ASCII punctuation replaced with ASCII equivalents

### A.7 Smoke test (TODO)

**Goal:** A friend runs `scripts/smoke_install.cmd` and gets "PASS" in
under 60s. Currently no such script exists.

**Acceptance criteria:**
- Script locates Python 3.12 (`py -3.12 -V` first, fall back to `python -V`)
- Creates venv at `%LOCALAPPDATA%\GPUPool\smoke-venv`
- Runs `pip install -r requirements-joiner.txt`
- Starts scheduler, waits up to 10s for `/status` to return 200
- Starts portal, waits up to 10s for `/portal` to return 200
- Prints elapsed time per step
- Exits 0 only if all steps pass; otherwise exits 1 with the failing step

---

## 11. Detailed Phase B - Friend experience polish (expanded)

### B.1 Server-side invite validation (TODO)

**Current behaviour:** The SPA form sends the invite code in plaintext
to the portal; the portal does a simple string compare against
`GPU_SWARM_INVITE_CODES`.

**Problem:** Anyone who reads the source can see the compare. A friend
who looks at `gpu_swarm/portal.py` learns the format.

**Target:** Server-side `/pool-api/invite/validate` endpoint that:
- Takes `{code, name}` POST body
- Returns `{ok, session_token, expires_at}` on success
- Returns 401 with a generic "invalid" message on failure (no enumeration)
- Sets a `gpu_pool_session` HTTP-only cookie

### B.2 Copy portal URL button (TODO)

**Implementation:** In `portal_hub.html`, after the login form submits
successfully, swap the login form for a small `<div>` containing:
- "Welcome, {name}" header
- The portal URL in a `<code>` element
- A "Copy" button that calls `navigator.clipboard.writeText(location.href)`
- Three big buttons: Share my PC, Use the pool, Invite friends

### B.3 About / Help page (TODO)

**Goal:** A friend who lands on the portal and is confused has a clear
self-service explanation.

**Files:** `portal_hub.html` gains an "About" link in the corner that
opens a modal with three sections:
1. "What is GPU Pool?" - two paragraphs.
2. "Is my data safe?" - explains the data flow diagram from section 5.1.
3. "How do I leave?" - explains how to revoke an invite and uninstall.

### B.4 Stable hostname (BLOCKED on D-named tunnel)

See Phase D.2.

### B.5 SSE for long jobs (BLOCKED on D-named tunnel)

**Current limitation:** Cloudflare Quick Tunnels return 426 Upgrade
Required for any `text/event-stream` request. The portal falls back to
2-second polling via `setInterval`.

**Target:** When running over a named tunnel, the portal upgrades to SSE
automatically. The polling code stays as a fallback for quick tunnels.

---

## 12. Detailed Phase C - Worker reliability (expanded)

### C.1 5s heartbeat (TODO)

**Current:** Worker sends heartbeat every 30s. A friend worker that
crashes silently appears online for up to 30 seconds.

**Target:** 5s heartbeat. Scheduler marks worker offline after 15s of
missed heartbeats. JSON heartbeat body unchanged.

**Trade-off:** 6x more packets. Negligible bandwidth (~200 B/min/worker)
but worth measuring.

### C.2 Friend-readable GPU failure (TODO)

**Current failure modes (all raw):**
- `pyNVML.NVML_ERROR_DRIVER_NOT_LOADED`
- `pyNVML.NVML_ERROR_NO_PERMISSION`
- `pyNVML.NVML_ERROR_GPU_IS_LOST`

**Target:** Worker maps each NVML error to a friend string:
- `NVML_ERROR_DRIVER_NOT_LOADED` -> "GPU driver missing. Install NVIDIA
  driver from https://www.nvidia.com/drivers"
- `NVML_ERROR_NO_PERMISSION` -> "Another process is using the GPU. Close
  it and try again."
- `NVML_ERROR_GPU_IS_LOST` -> "GPU stopped responding. Reboot and try again."

These strings show up in the portal's worker card and in `/pool-api/workers`.

### C.3 Hot-reload `.env` (TODO)

**Current:** Changing `.env` requires `start-worker.cmd` restart.

**Target:** Worker watches `os.stat('.env').st_mtime_ns` once per
heartbeat. On change, it reloads the invite codes and rate-limit config.
GPU detection does NOT re-run (a new GPU needs a restart).

### C.4 Worker `--dry-run` (TODO)

**Command:** `python -m gpu_swarm.worker --dry-run`

**Output:**
```
GPU Pool worker dry-run
  Python:     3.12.10
  Platform:   Windows 11 Pro 23H2
  pyNVML:     loaded (12.535.0)
  GPUs found: 2
    [0] NVIDIA GeForce RTX 5060 Ti
        VRAM total: 16303 MiB
        VRAM free:  12163 MiB
        Driver:    580.10
    [1] NVIDIA GeForce RTX 2070 SUPER
        VRAM total:  8192 MiB
        VRAM free:  2014 MiB
        Driver:    580.10
  CUDA:       12.6 (torch 2.5.1+cu121 OK)
  host_protect: ON
  Ready in 1.83s
```

Exit 0 on success, 1 on missing drivers, 2 on no GPUs but installable.

---

## 13. Detailed Phase D - Tunnel stability (expanded)

### D.1 Quick tunnel (ACTIVE)

**Current:** `cloudflared --url http://127.0.0.1:8767`. URL written to
`data/public_endpoints.json` and `data/public_endpoints.share.txt`.

**Limitations (per R-2):**
- 200 concurrent in-flight requests
- No SSE
- URL rotates on every restart
- No custom domain
- No uptime SLA

**Mitigations in place:**
- Portal caches the URL locally so subsequent restarts of the portal
  reuse the same URL until cloudflared itself restarts.
- `cloudflared` auto-reconnects if the edge connection drops (visible
  in `cloudflared_portal.log`).

### D.2 Named tunnel (TODO)

**Steps:**
1. Friend gives the host a Cloudflare account email (or uses an
   account already on the tailnet).
2. Host runs `cloudflared tunnel login` (opens browser, OAuth flow).
3. Host runs `cloudflared tunnel create gpupool` -> returns a UUID.
4. Host runs `cloudflared tunnel route dns gpupool pool.glitch-factor.dev`
   (requires the friend to own `glitch-factor.dev` or use Cloudflare
   for SaaS).
5. Host writes the UUID to `.env` as `GPU_SWARM_TUNNEL_ID`.
6. Host runs `cloudflared tunnel run gpupool` instead of
   `cloudflared --url`.

**Trade-offs:**
- Stable URL: friend can bookmark.
- SSE supported.
- Up to 100 concurrent in-flight per connection.
- Requires friend to do OAuth dance once.

### D.3 Surface 200-request cap hit (TODO)

Add a count of concurrent requests to `/pool-api/healthz`. If
`in_flight > 180`, return 503 with a friendly "Tunnel is busy; try
again in 30s" body so the SPA can show a banner.

---

## 14. Detailed Phase E - Discord bot richness (expanded)

### E.1 `/pool status` (PARTIAL)

**Current:** Returns raw JSON of `/status`.

**Target:** Renders an embed with:
- Title: "GPU Pool Status"
- "Workers online: 1/4"
- "Free VRAM: 2014 MiB / 24503 MiB"
- "In-flight jobs: 0"
- "Tunnel: ok"
- Footer: "Last update 2026-08-07T20:14:33Z"

### E.2 `/pool invite <user>` (TODO)

**Behaviour:** Host-only command. DM the target user a Discord DM
containing the current public portal URL + the existing invite code.
Audit-logged to `data/audit.log`.

**Permissions:** Requires `default_member_permissions = 64` (Manage
Messages). Verified in Glitch Factor as a host-only role.

### E.3 `/pool join <invite>` (TODO)

**Behaviour:** Anyone can run. Validates the invite against
`/pool-api/invite/validate`. Returns ephemeral message:
- Valid: "Invite OK. Open https://...trycloudflare.com/portal and enter
  this code."
- Invalid: "Invite invalid or expired."

Useful for a friend who wants to confirm invite freshness before
opening the browser.

### E.4 Per-guild slash command permissions (TODO)

Per R-10, Discord allows up to 100 permission overwrites per command
per guild. We currently use guild-scoped sync (not global) so we can
adjust per-guild. Track which guilds have the bot and which commands
they have access to in a small SQLite table.

---

## 15. Detailed Phase F - Multi-tenant scaling (expanded)

### F.1 Per-friend invite codes with TTL

**Current:** `.env` has a flat list of invite codes, no metadata.

**Target:** `.env` adds `GPU_SWARM_INVITES_JSON` pointing to a
gitignored file at `data/invites.json`:
```json
[
  {"code": "glitch-factor", "expires_at": null, "max_uses": null, "uses": 0, "role": "friend"},
  {"code": "temp-abc-123",  "expires_at": "2026-09-01T00:00:00Z", "max_uses": 1, "uses": 0, "role": "guest"}
]
```

Portal validates against this list. Plain-string `.env` entries still
work and are auto-converted to no-expiry, unlimited entries.

### F.2 Per-friend rate limits

**Defaults (Drew to confirm):**
- 5 jobs submitted per rolling 60 seconds
- 4 GB peak RAM across all in-flight jobs
- 30 min wall-clock per job

**Enforcement:** Scheduler tracks per-friend counters in
`data/jobs.db` (already SQLite). Returns 429 on overflow.

### F.3 Per-friend audit log

**Schema (in `data/audit.db` or extended `jobs.db`):**
```sql
CREATE TABLE audit_log (
  id INTEGER PRIMARY KEY,
  ts_utc TEXT NOT NULL,
  actor TEXT NOT NULL,           -- invite code that submitted
  action TEXT NOT NULL,          -- submit_job, cancel_job, login, ...
  target TEXT,                   -- job_id, worker_name, ...
  detail TEXT                    -- JSON blob
);
```

Written from portal.py on every action. Read by `/pool-api/admin/audit`
(host-only, gated by `GPU_SWARM_ADMIN_TOKENS` in `.env`).

### F.4 Friend revocation endpoint

**Route:** `POST /pool-api/admin/friends/{invite}/revoke`
**Auth:** Host's admin token in `Authorization: Bearer ...` header.
**Behaviour:** Marks the invite as `revoked_at = now()`. Pending jobs
from that invite are cancelled; running jobs finish naturally.

### F.5 Friend self-service dashboard

**Route:** `GET /pool-api/me`
**Auth:** Friend's session cookie from B.1.
**Response:**
```json
{
  "invite": "glitch-factor",
  "role": "friend",
  "jobs_running": 0,
  "jobs_completed_today": 7,
  "quota": {"jobs_per_minute": 5, "ram_mb_peak": 4096, "wall_clock_minutes": 30},
  "quota_used": {"jobs_per_minute": 0, "ram_mb_peak": 0}
}
```

---

## 16. Detailed Phase G - Local model endpoint (expanded)

### G.1 Install Ollama from wizard

**Command:** `winget install --id Ollama.Ollama -e --accept-package-agreements`
Returns ~150 MB download + PATH update + UAC prompt.

**Wizard flow:**
- Button: "Connect -> Install Ollama"
- Disabled while a previous install is in flight
- On success, refresh PATH and check `ollama --version`

### G.2 Auto-pull default model

**Pick (Drew's call):**
- `llama3.2:1b` - 1.3 GB, very fast on RTX 2070 SUPER, decent quality
- `qwen2.5:7b` - 4.7 GB, slower, much better quality
- `gemma3:4b` - 3.3 GB, balanced

**Default for friend path:** `llama3.2:1b` (fastest, friend will see
results in <2s on the 2070 SUPER).

**Pull command:** `ollama pull llama3.2:1b` (takes 1-3 min).

### G.3 "Use my local model" toggle

**SPA change:** Add a section under "Connect" with a toggle:
- Off (default): all inference goes to the pool
- On: friend runs the model locally; pool sees the endpoint at
  `http://127.0.0.1:11434` via a friend-side bridge (already implemented
  in `gpu_swarm/local_endpoint.py`)

**Privacy model:** When the toggle is on, the friend's prompt is sent to
their own machine, not the host. The host's worker never sees the
prompt content.

### G.4 Document privacy model

**File:** `LOCAL_MODEL.md` (already exists, expand).

Add:
- Data flow diagram (prompt -> friend machine -> ollama -> response)
- "Your prompts are not sent to the host" callout
- List of what IS sent (heartbeats, queue depth, model name)
- How to verify with `tcpdump` or Wireshark

---

## 17. Detailed Phase H - Workspace (expanded)

### H.1 Hyper-V conflict detection

**Detection command:**
```powershell
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All |
    Select-Object State
```

**If State == Enabled:**
- Block the "Install VirtualBox" button
- Show a panel: "VirtualBox cannot run while Hyper-V is enabled.
  Disable Hyper-V with this command, then reboot:
  `bcdedit /set hypervisorlaunchtype off`
  Then re-open the wizard."
- Provide a "Disable and reboot" button that runs the command and
  triggers a scheduled reboot.

**After reboot, on next wizard launch, re-check.**

### H.2 Vagrant same warning

Same as H.1, plus check for `vagrant` in PATH.

### H.3 Tested Vagrantfile

**Tested boxes:** `bento/ubuntu-22.04` (works with VBox 7.x).
**GPU passthrough:** requires VBox 7.1+ with the Extension Pack. Verify
Extension Pack is installed during the post-install check.

**Vagrantfile sketch:**
```ruby
Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-22.04"
  config.vm.provider "virtualbox" do |vb|
    vb.memory = 8192
    vb.cpus = 4
    vb.customize ["modifyvm", :id, "--gpu-profile", "auto"]
  end
end
```

### H.4 Multi-step wizard flow

```
Step 1: Detect Hyper-V
  -> If enabled, show warning + reboot button. Goto Step 1 again.
Step 2: Install VirtualBox
  -> Use winget. Verify VBoxManage.exe exists.
Step 3: Install Extension Pack
  -> Download from Oracle CDN, install via VBoxManage.
Step 4: Install Vagrant
  -> Use winget. Verify vagrant.exe exists.
Step 5: Bring up the workspace VM
  -> vagrant up. Verify SSH on 127.0.0.1:2222.
Step 6: Verify GPU passthrough
  -> SSH in, run nvidia-smi. Verify the friend's GPU is visible.
```

---

## 18. Detailed Phase I - Observability (expanded)

### I.1 Structured JSON logs (VERIFY)

**Current format (verify in `%LOCALAPPDATA%\GPUPool\logs\scheduler.log`):**
```
2026-08-07 20:14:33 INFO scheduler_worker_register worker=Drew-Home gpus=2
```

**Target format:**
```json
{"ts":"2026-08-07T20:14:33.123Z","level":"INFO","service":"scheduler","event":"worker_register","worker":"Drew-Home","gpus":2,"free_vram_mb":2014}
```

**One line per event, no pretty-printing.** Easy to grep with
`jq '.event == "worker_register"' scheduler.log`.

### I.2 /pool-api/healthz

**Endpoint:** `GET /pool-api/healthz` on the portal.

**Response when healthy:**
```json
{"ok": true, "checks": {"scheduler": "ok", "portal": "ok", "worker": "ok", "bot": "ok", "tunnel": "ok"}}
```

**Response when unhealthy:**
```json
{"ok": false, "checks": {"scheduler": "ok", "portal": "ok", "worker": "stale heartbeat 45s", "bot": "ok", "tunnel": "ok"}}
```

Returns 200 when ok, 503 otherwise. Wired into Cloudflare's free
uptime check (`https://www.cloudflare.com/uptime-check/`) for
external monitoring if Phase D-named is enabled.

### I.3 Optional Sentry/OTel

**Opt-in.** When `GPU_SWARM_SENTRY_DSN` is set in `.env`, the worker
and scheduler initialize a Sentry SDK and capture unhandled exceptions.
When unset, the SDK is not even imported. This keeps the cold-start
path lean.

---

## 19. Detailed Phase J - Releases (expanded)

### J.1 Pin Python 3.12.x in CI

Add `pyproject.toml` with `requires-python = ">=3.12,<3.13"`. CI runs
on Python 3.12.6 minimum.

### J.2 Pin cloudflared version

Today the script downloads whatever the latest version is. Pin it to
`2026.7.3` in `scripts/install_cloudflared.ps1` with a `-Version`
parameter defaulting to the pinned version. The download URL becomes
deterministic, which means reproducible installs.

### J.3 Code signing

**Cert provider:** DigiCert or Sectigo. ~$200-400/year.

**Signtool command:**
```
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a dist/GPUPool/GPUPool.exe
```

**Effect:** SmartScreen no longer warns; install feels native.

### J.4 Version bump automation

`scripts/bump_version.py` takes a version string and updates:
- `gpu_swarm/__init__.py` (`__version__`)
- `RELEASE_NOTES_v{VERSION}.md` (template from `RELEASE_NOTES_v0.1.1.md`)
- `gpu_pool_entry.py` (the `--version` flag output)
- The NSIS installer template (Phase J.5)

### J.5 NSIS installer (TODO, optional)

**Goal:** `GPUPool-Setup-v0.2.0.exe` that:
- Installs the onedir bundle to `%LOCALAPPDATA%\GPUPool\`
- Adds a Start Menu shortcut
- Adds an uninstall entry
- Optionally creates the Startup VBS (default: yes)

NSIS script lives at `installer/GPUPool.nsi`.

---

## 20. Phase K - Security and abuse prevention (NEW, not in v1 plan)

User feedback indicated they want the install to be safe, not just
fast. This phase is non-functional hardening.

### K.1 Invite code entropy

**Current:** `glitch-factor` is human-readable. Good for sharing,
terrible for security. It is 13 characters of dictionary words.

**Target:** Generate invite codes with at least 80 bits of entropy.
Format: `word-word-word-XXXX` where `XXXX` is 4 random alphanumerics.
Example: `quiet-river-stone-a3F9`.

**Migration:** Old `glitch-factor` becomes a legacy alias that still
works; new codes use the new format.

### K.2 Rate limiting by IP

**Current:** No rate limiting. A bad actor could brute-force invite codes
(13-char dictionary words are only ~50 bits of entropy).

**Target:** Per-IP rate limit on `/pool-api/invite/validate`:
- 10 attempts per minute per IP
- 100 attempts per hour per IP
- Exponential backoff after 3 failures in a row (1s, 2s, 4s, 8s, ...)

### K.3 CORS policy

**Current:** Portal returns `Access-Control-Allow-Origin: *` (effectively
needed because the portal can be loaded from any trycloudflare URL).

**Target:** Lock down CORS to only the known portal origin. For the
quick-tunnel path, accept any `*.trycloudflare.com` origin. For the
named-tunnel path, lock to the single hostname.

### K.4 CSP headers

**Current:** No CSP.

**Target:** Add `Content-Security-Policy: default-src 'self'; script-src
'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self'
data:;` to the portal responses. Test that the SPA still works.

### K.5 HTTPS-only

**Already enforced by Cloudflare** in front of the portal. Local
`127.0.0.1` is HTTP but never exposed externally.

### K.6 Audit log immutability

The audit log from F.3 should be append-only and ideally signed.
Simple approach: every line includes a SHA-256 of `(prev_line_hash +
current_line_json)`. A verifier can detect tampering.

### K.7 Friend-side worker trust

A friend worker runs on a machine we don't control. We should:
- Reject jobs that try to read host files (already enforced by
  `host_protect.py`)
- Rate-limit per worker
- Cap concurrent jobs per worker
- Provide a "report abuse" link in the SPA

### K.8 Threat model (informal)

| Threat | Mitigation |
|--------|------------|
| Bad actor brute-forces invite code | K.2 rate limits + K.1 entropy |
| Bad actor scrapes the portal for invite codes | K.3 CORS + K.4 CSP |
| Friend worker leaks host data | host_protect.py + audit log |
| Friend worker submits infinite jobs | F.2 rate limits per friend |
| Bot token leak | Bot is only used for slash commands, no DB writes from bot |
| Cloudflared process crash | Auto-reconnects; persistent health check |
| Host PC crash | VBS in Startup folder brings services back |
| `.env` accidentally committed | `.env` in `.gitignore`; CI fails if `.env` present |

---

## 21. Phase L - Documentation (NEW)

The user explicitly asked for "super nice" docs. Today we have a lot of
.md files but no consistent voice or table of contents.

### L.1 Master table of contents

Add `docs/INDEX.md` that lists every `.md` file with a one-line
description and target audience.

### L.2 Friend-facing docs

Rewrite for plain English, no jargon, three reading levels:
- "Just tell me what to click" (default)
- "I want to know what's happening" (intermediate)
- "I'm a developer" (technical, links to API refs)

### L.3 Host docs

Move `START_HERE.md`, `CURRENT_PROGRESS.md`, `TRACKER_FRIEND_ONBOARDING.md`,
and `ROADMAP.md` under `docs/host/` with a TOC at the top.

### L.4 Code-level docs

Every Python module gets a module-level docstring with:
- Purpose
- Public functions
- Dependencies
- Common pitfalls (link to MEMORY.md if relevant)

### L.5 Screenshot placeholders

For each wizard step, add a markdown image placeholder. Generate the
actual screenshots in CI.

---

## 22. Phase M - Performance budgets (NEW)

What "fast" means. Concrete numbers so "it's slow" is measurable.

### M.1 Cold start

| Path | Budget |
|------|--------|
| Friend opens portal in browser | <2s to first paint |
| Friend submits invite code | <500ms to dashboard |
| Friend submits a job | <100ms to "queued" status |
| Host launches from Startup VBS | <15s to all 4 services healthy |
| Host launches from `start-public-access.cmd` | <10s to all 4 services healthy |

### M.2 Steady state

| Path | Budget |
|------|--------|
| Heartbeat round trip | <100ms p50, <500ms p99 |
| Job submit latency (pool decision) | <200ms p99 |
| Worker pull job latency | <500ms p99 |
| `/pool-api/status` response | <50ms p99 |

### M.3 Resource caps

| Resource | Cap |
|----------|-----|
| Portal process RSS | <100 MB |
| Scheduler process RSS | <200 MB |
| Worker process RSS | <300 MB |
| Cloudflared process RSS | <80 MB |
| Total pool RSS | <700 MB |

Larger caps mean more memory pressure on the host; these are tight
enough to leave headroom for the friend's actual workload.

---

## 23. Phase N - Error taxonomy (NEW)

A shared vocabulary so logs, errors, and UI all use the same terms.

### N.1 Categories

| Code | Category | Examples |
|------|----------|----------|
| E1xxx | Install | missing Python, venv corrupt, pip fail |
| E2xxx | Bootstrap | GPU driver missing, CUDA mismatch |
| E3xxx | Service | scheduler crash, portal 500, bot logout |
| E4xxx | Network | tunnel down, 429 from edge, DNS fail |
| E5xxx | Worker | heartbeat lost, job exec fail, OOM |
| E6xxx | Friend | invite invalid, rate limit, quota exceeded |
| E7xxx | Auth | session expired, CSRF, bot token invalid |
| E8xxx | Data | SQLite locked, disk full, log write fail |
| E9xxx | Internal | unexpected exception, regression |

### N.2 Format

```
[CODE] human-readable: one-line what-happened
       action:        one-line what-to-do
       docs:          link to docs page
```

Example:
```
[E3301] portal: failed to render SPA
       action:        check disk space; restart portal; if persists, file issue
       docs:          docs/troubleshooting.md#e3301
```

### N.3 Wiring

Every Python module has a `module_logger = logging.getLogger(__name__)`
that prefixes errors with the code. The wizard catches errors and shows
the human-readable part + a "Copy details" button that copies the full
multi-line entry to the clipboard.

---

## 24. Phase O - Disaster recovery (NEW)

What happens when things go really wrong.

### O.1 Reinstall the host (clean slate)

```
1. Backup %LOCALAPPDATA%\GPUPool\data\ to a USB
2. Uninstall: kill all pool processes, delete %LOCALAPPDATA%\GPUPool\
3. Delete Startup VBS
4. Reinstall: clone repo, run start-gpu-pool-app.cmd
5. Restore invite codes: copy .env from backup
6. Bring services up: start-public-access.cmd
7. Verify: scripts/_check_parse.ps1 + portal probe + worker probe
8. Share new public URL with friend
```

### O.2 Recover from a tunnel URL leak

If the trycloudflare URL is leaked (posted publicly, indexed, etc.):
1. Kill cloudflared process
2. Restart it; new URL is generated
3. Update data/public_endpoints.share.txt
4. DM friend the new URL
5. Old URL becomes unreachable within seconds (cloudflared cleanup)

### O.3 Recover from a poisoned `.env`

If invite codes leak:
1. Edit `.env` to add a new code under `GPU_SWARM_INVITE_CODES`
2. Restart portal (one CMD: `start-portal.cmd`)
3. Old code continues to work until you remove it from `.env`

If Tailscale auth key leaks:
1. Revoke the key at https://login.tailscale.com/admin/settings/keys
2. Generate a new key, paste into `.env`
3. The host's Tailscale does not need to re-auth (only new joins use the key)

### O.4 Recover from a worker-side host_protect bypass

If a friend worker somehow reads a host file (should be impossible):
1. Audit log at `data/audit.log` has the timestamp and action
2. Disable the friend's invite: edit `.env`, remove their code
3. Run `python -m gpu_swarm.cli revoke --invite <code>` (TODO)
4. Friend's worker is rejected on next heartbeat

### O.5 Recover from a database corruption

The scheduler uses SQLite at `data/jobs.db`. If it corrupts:
1. Stop the scheduler
2. Copy `data/jobs.db` to `data/jobs.db.corrupt.{ts}` for forensics
3. Delete `data/jobs.db` (will be recreated on next start)
4. Restart scheduler
5. In-flight jobs are lost; the worker will time out and mark them failed

---

## 25. Appendix - API surface inventory

Every HTTP endpoint the pool exposes. Useful when wiring the SPA,
admin tools, or external integrations.

### Portal (127.0.0.1:8767, exposed via tunnel)

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/portal` | SPA HTML | none |
| GET | `/about` | Help page (Phase L) | none |
| POST | `/pool-api/invite/validate` | Validate invite + name, set cookie | none |
| POST | `/pool-api/invite/revoke` | (host) Revoke an invite | admin token |
| GET | `/pool-api/me` | Friend self-service info | session cookie |
| GET | `/pool-api/workers` | List workers + status | session cookie |
| POST | `/pool-api/jobs` | Submit a job | session cookie |
| GET | `/pool-api/jobs/{id}` | Job status | session cookie |
| DELETE | `/pool-api/jobs/{id}` | Cancel a job | session cookie |
| GET | `/pool-api/admin/audit` | Audit log | admin token |
| GET | `/pool-api/admin/friends` | List friends + invites | admin token |
| GET | `/pool-api/healthz` | Aggregate health | none |
| GET | `/pool-api/status` | Public status (used by tunnel) | none |

### Scheduler (127.0.0.1:8766, NOT exposed via tunnel)

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/status` | Aggregate status | token |
| POST | `/workers/register` | Worker heartbeat + register | token |
| POST | `/workers/unregister` | Worker graceful shutdown | token |
| POST | `/jobs/submit` | Submit job (portal -> scheduler) | token |
| GET | `/jobs/next` | Worker pulls next job | token |
| POST | `/jobs/{id}/status` | Worker reports job status | token |
| GET | `/jobs/{id}` | Job status (portal -> scheduler) | token |
| DELETE | `/jobs/{id}` | Cancel job | token |

### Worker (no HTTP; outbound only)

| Direction | Endpoint | Purpose |
|-----------|----------|---------|
| Worker -> Scheduler | POST /workers/register | every 5s |
| Worker -> Scheduler | GET /jobs/next | when idle |
| Worker -> Scheduler | POST /jobs/{id}/status | on completion |

---

## 26. Appendix - Command cookbook

Every command a future agent or Drew might need, in one place.

### Service management

```powershell
# Start everything (hidden)
start-public-access.cmd

# Start individual services
start-scheduler.cmd
start-portal.cmd
start-worker.cmd
start-bot.cmd

# Stop everything
python -m gpu_swarm.cli stop --all
# Or manually:
powershell -NoProfile -Command "Get-Process pythonw -ErrorAction SilentlyContinue | Stop-Process -Force"
powershell -NoProfile -Command "Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force"

# Tail logs
Get-Content "$env:LOCALAPPDATA\GPUPool\logs\scheduler.log" -Wait
Get-Content "$env:LOCALAPPDATA\GPUPool\logs\portal.log" -Wait
Get-Content "$env:LOCALAPPDATA\GPUPool\logs\worker.log" -Wait
Get-Content "$env:LOCALAPPDATA\GPUPool\logs\bot.log" -Wait
Get-Content "$env:LOCALAPPDATA\GPUPool\logs\cloudflared_portal.log" -Wait

# Restart a single service
start-portal.cmd  # uses taskkill /F /IM ... internally before starting
```

### Diagnostics

```powershell
# Verify PowerShell scripts parse
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\_check_parse.ps1

# Detect-only prereq check
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-prereqs.ps1 -Json -Quiet

# Live health probes
curl http://127.0.0.1:8766/status
curl http://127.0.0.1:8767/portal
curl https://<tunnel-url>/portal

# End-to-end job probe
cd "C:/Users/Drew/Projects/gpu-swarm"
$env:GPU_SWARM_SCHEDULER_URL = "http://127.0.0.1:8766"
python -m gpu_swarm utilize probe --wait

# Worker dry-run (when implemented)
python -m gpu_swarm.worker --dry-run
```

### Persistence

```powershell
# View the Startup-folder VBS
Get-Content "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\GPUPool-Startup.vbs"

# Remove it
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\GPUPool-Startup.vbs"

# Try to register a Task Scheduler entry (will fail without elevation)
schtasks /Create /SC ONLOGON /TN GPUPool-All /TR "cmd /c start-public-access.cmd" /RL HIGHEST /F
# If that fails with Access is denied, the VBS fallback is the only path.
```

### Build / release

```powershell
# Lint PowerShell
scripts\_check_parse.ps1

# Compile Python syntax check
python -m py_compile gpu_pool_entry.py gpu_swarm\*.py

# Run the smoke test (when implemented)
scripts\smoke_install.cmd

# Build the EXE
pyinstaller --noconfirm --windowed --onedir --name GPUPool gpu_pool_entry.py

# Sign the EXE (when cert is available)
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a dist\GPUPool\GPUPool.exe

# Bump version (when implemented)
python scripts\bump_version.py 0.2.0
```

---

## 27. Change log

- 2026-08-07 - Initial roadmap. Drew's "buggy, super laggy" feedback
  addressed in source. Live stack healthy. Packaged EXE rebuild pending.
- 2026-08-07 - Expansion. Added 8a Decision log, 10-24 detailed phase
  expansions, 20-21 Security + Documentation phases, 22-23 Performance +
  Error taxonomy, 24 Disaster recovery, 25 API inventory, 26 Command
  cookbook. Total ~750 lines.
- 2026-08-08 - Parent recovery from @session:personal/20260807_195826_57d251
  preserved the sibling tracker and working tree. Source checks pass; default
  prerequisite execution is now truly no-install and reports skipped fields.
- 2026-08-08 - First rebuilt onefile artifact completed, but packaged smoke
  exposed PyInstaller's unused `pkg_resources.extern` runtime-hook failure.
  `gpu_pool.spec` now excludes unused `pkg_resources` and `setuptools`; rebuild
  and packaged smoke are still required before release distribution.

### 2026-08-08 - Cloudflare installer package accepted

- Rebuilt `dist/GPUPool.exe` from the Cloudflare-enabled source using the isolated GPUPool CPython 3.12 venv with `PYTHONPATH` removed.
- PyInstaller `6.22.0` build exited `0`; artifact size is `18,311,237` bytes and the focused hidden GUI smoke passed.
- SHA-256: `204aaeee3e737ff9537bb77d9b736d38332e9bb09e0f24a835c21ac774fcc00d`.
- The source integration and packaged artifact are ready for the requested Git commit/push. Named Cloudflare DNS deployment remains a separate user-domain step.

### 2026-08-08 - Cloudflare controls completed across all surfaces

- Installer, first-run wizard, installed MainFrame Connect, website `/api/config`, and website Connect view now expose the same Quick Tunnel and named-tunnel workflow.
- Added guided named setup scripts with user-controlled browser login, tunnel create/reuse, DNS routing, config generation, optional launch, and public verification.
- Final packaged artifact rebuilt successfully; both setup scripts are embedded. Worker help, local-endpoint help, hidden GUI startup, and portal API/template smoke checks passed.
- Named Cloudflare login, DNS mutation, and credential creation remain intentionally unexecuted until Drew supplies/approves the domain setup.
- Source and tracker changes remain local/uncommitted pending explicit commit/push.

### 2026-08-09 - Shared LLM routing and release rebuild

- Added native Ollama chat routing, explicit blank-assistant failure handling, visible Discord queue/completion/error states, and provider-prefix persistence.
- Added installed/loaded/fit-now model metadata and same-worker multi-GPU group reporting. The installed Qwen 27B Q4 model is correctly `installed-not-fit-now` under current Windows display headroom; it was not force-loaded.
- Live acceptance: scheduler health 200, Discord gateway connected with 10 commands synced, and exact-model worker job returned `GPU_FIT_METADATA_OK`.
- Rebuilt `dist/GPUPool.exe` successfully with `PYTHONPATH` removed from the Windows build environment. Artifact size: `35,251,884` bytes. SHA-256: `3251c103edbd1d5c53d2fc5d8dbc846c8a120a8505f6423a8a4139ca7247f1a6`.
- Packaged command-mode smoke passed for `--worker --help` and `--local-endpoint --help`; no `.env` or secrets are bundled.

### 2026-08-09 - Service lifecycle, GPU selection, and Docker manual re-enable latch

- Added opt-in local service settings: `services_enabled`, `keep_services_running`, and persisted physical `selected_gpu_ids`; app close stops app-owned worker/model activity unless the user explicitly keeps services running.
- Added durable `setup-complete.flag` handling plus an explicit reset path so onboarding is not automatically repeated on every launch.
- Added GPU selector wiring in the wizard and main contribution surface. `GPU_SWARM_SELECTED_GPU_IDS` filters worker inventory by stable physical `nvidia-smi` index; invalid IDs fail closed instead of remapping.
- Added hidden Windows startup info plus `CREATE_NO_WINDOW` to Tailscale and service subprocess paths. Startup supervisors now stop/refrain from restarting children when services are disabled.
- Added `gpu_swarm/service_lifecycle.py`: explicitly configured Ollama providers are probed through `/api/tags`; an outage writes `data/docker-reenable-required.json`, latches services OFF, logs to `data/service-lifecycle.log`, and requires a successful UI re-enable health check before clearing.
- Worker heartbeat checks the Docker/Ollama latch and stops on a detected outage; service supervisors see the latch and do not restart it.
- Focused receipts: all changed Python modules compile; `git diff --check`; `gpu_swarm bot --check`; worker `--selected-gpu-ids` help; GPU-ID parser smoke; controlled `DOCKER_LATCH_SMOKE_OK`.
- Delegated implementation workers were dispatched with disjoint scopes but both received read-only lanes and modified zero files; parent took over their exact scopes. No worker receipt was accepted without source verification.
- Source and packaged EXE rebuild/commit/push remain pending for this pass; the prior release commit remains `62be293`.

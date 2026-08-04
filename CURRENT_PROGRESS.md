# CURRENT_PROGRESS — GPU Pool (gpu-swarm)

Living scorecard for Drew’s private Discord GPU/CPU co-op.  
**Updated:** 2026-08-04 ~13:25 CDT · **Ready-to-go source tip** (shared agent-dev + install-prereqs).

**GitHub:** https://github.com/phoenixfire808/gpu-swarm (public)

| Service | Local | Tailscale |
|---------|-------|-----------|
| Scheduler | `http://127.0.0.1:8766` | `http://100.85.165.84:8766` |
| Portal | `http://127.0.0.1:8767/portal` | `http://100.85.165.84:8767/portal` |
| **Local model endpoint** | `http://127.0.0.1:18080/v1` (8080 busy → fallback) | localhost only |
| Public portal (when tunnel up) | see `data/public_endpoints.share.txt` | — |
| Robinhood CC | `127.0.0.1:8765` | **do not steal** |

**Discord:** App **GPU Pool** · Primary guild **Glitch Factor** · Invite code `glitch-factor`  
**v1 jobs:** `probe`, `pytorch_cuda_probe`, **`llm_chat`** · Auth MVP: invite/password (OAuth later)  
**Rules:** No Docker · No mock GPU/host data · Never commit `.env` / token paste files / `data/public_endpoints*`  
**Living docs:** [`TODO.md`](TODO.md) · [`ROADMAP.md`](ROADMAP.md) · [`CHANGELOG.md`](CHANGELOG.md) · [`SHARED_AGENT_DEV.md`](SHARED_AGENT_DEV.md)

---

## Ready-to-go checklist (2026-08-04 ~13:25 CDT)

**Verdict: YES — usable today from repo tip (source).** Friend EXE still stale until v0.1.1.

| # | Check | Result |
|---|--------|--------|
| 1 | Scheduler + portal + hub UI | **PASS** — `/portal` Network Hub / Workspace / Sign in |
| 2 | Workers online | **PASS** — Drew-Home + Wizard-OneStop; **`llm_ready=yes`** after Ollama serve |
| 3 | `install-prereqs` detect | **PASS** — Tailscale + VirtualBox + Vagrant present / skipped |
| 4 | Wizard **Network & Workspace** step | **SHIPPED (source)** — Detect / Install & connect / Tailscale-only |
| 5 | Local endpoint `/v1/models` | **PASS** — `:18080` lists `gpu-pool` |
| 6 | Workspace bridge | **PASS** — Hermes ready; agent-ubuntu poweroff; RDP plan 3390; caps mapped |
| 7 | Public Cloudflare path | **PASS** — tunnel active (URL in share file; rotates) |
| 8 | Light chat completion | **SKIPPED** — local model is ~27B GGUF; avoid loading (host_protect already pausing on util) |
| 9 | Published EXE freshness | **FAIL** — Release v0.1.0 stale; use source |

### How Drew launches (ready copy)

```bat
cd C:\Users\Drew\Projects\gpu-swarm
scripts\install-prereqs.cmd
start-scheduler-lan.cmd
start-portal.cmd
start-worker.cmd
ollama serve
start-local-endpoint.cmd
start-gpu-pool-app.cmd
REM optional friends without Tailscale:
start-public-access.cmd
```

Friend: `scripts\install-prereqs.cmd` → `start-gpu-pool-app.cmd` → invite `glitch-factor` → Contribute/Utilize.  
Shared agent story: [`SHARED_AGENT_DEV.md`](SHARED_AGENT_DEV.md).  
Workspace RDP: `mstsc /v:127.0.0.1:3390` · `vagrant`/`vagrant`.  
Harness: `OPENAI_BASE_URL=http://127.0.0.1:18080/v1` (or `:8080/v1` when free).

### Automated vs still manual

| Automated | One clear manual click |
|-----------|------------------------|
| Detect/skip Tailscale, VirtualBox, Vagrant | UAC Yes on install |
| winget / MSI / Oracle installer when missing | Tailscale browser login (or env `GPU_SWARM_TAILSCALE_AUTHKEY`) |
| Wizard progress + Python bootstrap | Invite + display name |
| Contribute caps → VM CPU/RAM | First cold `vagrant up` (once) |
| Public portal alternative | — |

### Remaining one-click gaps

- Publish **GPUPool.exe v0.1.1+** (hub + workspace + install-prereqs + host_protect)
- Pool UI for multi-session `session create` (CLI works)
- Lighter default chat model for smoke (don’t load 27B during desktop use)
- host_protect may **pause leases** when GPU util ≥65% — expected desktop safety

---

## Done (this turn)

- [x] `scripts/install-prereqs.ps1` + `.cmd` — Tailscale / VirtualBox / Vagrant detect-or-install, verbose steps, JSON for app
- [x] Wizard step **Network & Workspace** wired via `app_backend.install_prereqs`
- [x] `check_prereqs` reports tailscale/virtualbox/vagrant
- [x] `SHARED_AGENT_DEV.md` + DOWNLOAD / LOGIN / FRIEND / ROADMAP / CHANGELOG updates
- [x] Ollama started; Drew-Home **`llm_ready=yes`**; endpoint models listed
- [x] Spec bundles prereq scripts + SHARED_AGENT_DEV for next EXE

---

## Do not

- Commit `.env`, tokens, `data/public_endpoints*`, Tailscale auth keys
- Use Docker / OpenClaw for these VMs
- Steal port `8765`
- Heavy CUDA / load 27B GGUF / PyInstaller during agent sessions unless Drew asks

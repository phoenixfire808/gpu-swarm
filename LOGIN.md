# How to log in to GPU Pool

Step-by-step for friends in **Glitch Factor** Discord. No screenshots needed — follow the numbered steps.

**Repo:** https://github.com/phoenixfire808/gpu-swarm  
**Primary Discord:** Glitch Factor · Bot: **GPU Pool**

---

## 0) What GPU Pool is for (30 seconds)

**GPU Pool** lets friends on your network **share spare GPU/CPU**, **run jobs** on whoever is online, **chat** on the Network Hub, **suggest** improvements, and **invite others**. It is a private co-op — not a public marketplace, not Docker.

| Mode | Plain English |
|------|----------------|
| **Join** | Open the portal or app → invite code + Discord display name. |
| **Share my PC** | Contribute spare GPU/CPU with caps you control. Host GPU safety stays ON. |
| **Use the pool** | Utilize allowlisted jobs. **No NVIDIA required** on your laptop. |
| **Invite others** | Copy a friend message / portal URL / download link and send it to grow the pool. |
| **Connect / Workspace** | Tools + optional Linux desktop (CPU/RAM only — no GPU passthrough). |
| **Chat / Suggest** | Talk with the pool and send ideas (web Network Hub). |

Invite code **`glitch-factor`** is a product setting (configurable via `GPU_SWARM_INVITE_CODES`) — not a person.

During EXE / from-source install you’ll see steps like “Downloading Python runtime…” and “Installing dependencies (1/5)…” — leave the window open until it finishes.

---

## 1) What “login” means

GPU Pool uses **MVP invite auth** (Discord OAuth comes later). You are not creating a public account.

| Field | Required? | What to enter |
|-------|-----------|---------------|
| **Invite code** | Yes (usual path) | Shared code from the host / admin — currently `glitch-factor` |
| **Display name** | Yes | Your Discord name (so the pool can show who you are) |
| **Pool password** | Optional | Only if a pool admin gave you the shared pool password instead of (or in addition to) the invite |

**Rule of thumb:** invite code + display name is enough for almost everyone.

---

## 2) WHERE to get login info

| Item | Where |
|------|--------|
| **Invite code** | From **the host / admin in Discord (Glitch Factor)** — not a public website signup |
| **Current invite** | `glitch-factor` (the host can rotate this anytime) |
| **Pool password** | Only if a pool admin shares it — never posted publicly; lives in host `.env` |
| **Public portal URL** | From the host (DM / Discord). Host file: `data/public_endpoints.share.txt` (URL **rotates** when the tunnel restarts) |
| **Tailscale portal** | Stable: `http://100.85.165.84:8767/portal` (you must be on the host’s tailnet) |
| **Windows EXE** | [GitHub Releases](https://github.com/phoenixfire808/gpu-swarm/releases/latest) → `GPUPool.exe` |

The host rotates auth via host `.env` keys (see [.env.example](.env.example)):

- `GPU_SWARM_INVITE_CODES` — comma-separated invite codes  
- `GPU_SWARM_POOL_PASSWORD` — optional shared password  

If login suddenly fails after it worked before, ask the host whether the invite was rotated.

---

## 3) Pick a path into the portal

### Path A — Public HTTPS portal (no Tailscale) — preferred for friends

1. the host starts the tunnel on the host PC (see [For the host](#for-drew-host) below): `start-public-access.cmd` (portal + scheduler already running).
2. Get the **current** public URL from the host, or (on the host PC) open:
   - `data/public_endpoints.share.txt`  
   - Shape: `https://….trycloudflare.com/portal`
3. Open that URL in a browser (Chrome / Edge / Firefox).
4. You should see the **Sign in** panel. Continue to [§4 Login form](#4-exact-login-form-fields).

**Notes**

- Public links are `https://….trycloudflare.com/portal` — **no** `:8767` on the public hostname.
- Quick-tunnel hostnames **change** when the host restarts `start-public-access.cmd`. Do not reuse an old link from chat history.

### Path B — Tailscale portal (private network)

1. **Automated (preferred):** from a gpu-swarm checkout run `scripts\install-prereqs.cmd` (or wizard step **Network & Workspace** → **Install & connect**). It detects Tailscale, installs if missing, then opens login. Approve UAC if asked; finish the **one** Tailscale browser login. Optional unattended: set `GPU_SWARM_TAILSCALE_AUTHKEY` (never commit).
2. Or install manually from [Tailscale](https://tailscale.com/download) and join the Glitch Factor tailnet (ask the host).
3. Open exactly:  
   `http://100.85.165.84:8767/portal`
4. Continue to [§4 Login form](#4-exact-login-form-fields).

**Common mistake:** opening `http://100.85.165.84` without **`:8767`** and `/portal` — that will not load the portal.

### Path C — Windows desktop app (source tip ready; EXE v0.1.1 pending)

**Ready today from source:**

```bat
cd C:\Users\Drew\Projects\gpu-swarm
scripts\install-prereqs.cmd
start-gpu-pool-app.cmd
```

Published EXE: https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe  
(see [`DOWNLOAD.md`](DOWNLOAD.md) — **v0.1.0 is stale**; prefer source until **v0.1.1+**).

1. Run app / EXE. SmartScreen on unsigned EXE → **More info** → **Run anyway** (only if you trust this repo’s release).
2. Wizard: **Network & Workspace** → Detect / Install & connect (Tailscale; optional VirtualBox+Vagrant for Workspace).
3. Prefer the **public pool-api / portal** URL a pool member shared when the tunnel is up; else Tailscale.
4. Enter invite **`glitch-factor`** + your Discord display name.
5. Set **your** resource caps (VRAM can be **0** if you have no NVIDIA GPU) → **Save + Join**.
6. Home → **Contribute** or **Utilize**. Optional: Workspace / Connect local model.

Shared agent-dev steps: [`SHARED_AGENT_DEV.md`](SHARED_AGENT_DEV.md).

**Personal offer control:** Only you control how much of your PC is offered. Change anytime on your machine or in Contribute settings. Nobody else can remotely raise your caps.

**Host GPU safety:** Default ON — the worker will not peg your GPU hard enough to freeze Windows. You can raise caps; the safety ceiling still leaves desktop headroom. Details: [`CONNECTING.md`](CONNECTING.md).

---

## 4) Exact login form fields

On `/portal` → **Sign in**:

1. **Display name** — your Discord name (e.g. `YourDiscordName`).
2. **Invite code** — `glitch-factor` (unless a pool admin gave you a newer code).
3. **Pool password** — leave blank unless a pool admin told you to use it.
4. Click **Enter portal**.

You should land on **Home** signed in as your display name.

---

## 5) After login — what to click

| Path | What it does | Who it’s for |
|------|--------------|--------------|
| **Contribute** | Register this PC, set **your** GPU/CPU/RAM/disk offer caps, run a worker that takes allowlisted jobs. Only you can change your offer. Host GPU safety ON by default. | Friends with spare compute (GPU optional — VRAM=0 = CPU-only) |
| **Utilize** | Submit allowlisted jobs (`probe`, CUDA probe, `llm_chat` when a worker is ready); they run on online workers | Anyone — especially laptops with **no NVIDIA** |
| **Connect** | URLs, local model endpoint, Discord slash commands, CLI / Python SDK | Coders and agents |
| **Workspace** | Optional Ubuntu VM via Hermes — uses your CPU/RAM share only | When you want a Linux desktop; **not** GPU passthrough |
| **Chat / Suggest** | Pool chat + suggestion inbox on the web Network Hub | Everyone |

More detail: [`CONNECTING.md`](CONNECTING.md) · Workspace: [`ADVANCED_VM.md`](ADVANCED_VM.md).

**Laptop / no NVIDIA?** Use **Utilize** (jobs run on pool GPUs). Optional: Contribute with VRAM=0.

---

## 6) Troubleshooting

| Symptom | Fix |
|---------|-----|
| **Black / blank portal screen** | Hard refresh (**Ctrl+F5**). Confirm you opened the **latest** public URL from the host (tunnels rotate). Try another browser. |
| **Wrong URL / page won’t load** | Public: must end with `/portal`. Tailscale: must include **`:8767`** and `/portal`. Bare IP with no port will fail. |
| **“Invalid pool password or invite code”** | Re-check invite spelling (`glitch-factor`). Ask the host if the code was rotated. Pool password is optional — leave blank if you only have the invite. |
| **No NVIDIA / no nvidia-smi** | Expected on many laptops. Use **Utilize**, or Contribute with VRAM=0. |
| **Windows SmartScreen on GPUPool.exe** | Unsigned builds warn by default → More info → Run anyway if you trust the GitHub release from this repo. |
| **Tunnel URL expired / 404** | Ask the host for a fresh link; host: re-run `start-public-access.cmd` and read `data/public_endpoints.share.txt`. |
| **CLI / SDK can’t connect** | Public: `GPU_SWARM_SCHEDULER_URL=https://….trycloudflare.com/pool-api` · Tailscale: `http://100.85.165.84:8766` — not the portal URL. |

---

## For the host

### Share invite / password safely

1. Open `.env.example` for the **key names** (do not paste real `.env` into Discord or git):
   - `GPU_SWARM_INVITE_CODES`
   - `GPU_SWARM_POOL_PASSWORD`
2. On the host, read your local `.env` (never commit it) and DM friends only what they need — usually the **invite code**, not the pool password.
3. To rotate: change the value in `.env`, restart portal (`start-portal.cmd`), tell friends the new invite.

### Share the current public URL / invite others

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-portal.cmd
start-public-access.cmd
```

Then either:

- Portal / desktop app → **Invite others** → one-click copy (friend message, full blurb, portal URL, invite code, GitHub download)
- Copy the Portal line from `data\public_endpoints.share.txt`
- Ask a pool member for the current public link

`data/` is gitignored — do **not** commit `public_endpoints.json` / `.share.txt` / `.env`.

Stable private fallback for friends already on Tailscale:  
`http://100.85.165.84:8767/portal`

---

## Related docs

- [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md) — short / paste-ready  
- [`DOWNLOAD.md`](DOWNLOAD.md) — Windows EXE  
- [`NO_GPU_LAPTOP.md`](NO_GPU_LAPTOP.md) — no-GPU laptop path  
- [`CONNECTING.md`](CONNECTING.md) — Contribute / Utilize / Connect from code  

---

## Paste-ready Discord blurb

Copy everything inside the fence into Discord:

```text
**GPU Pool — join in under 30 seconds**
Private co-op: Share my PC · Use the pool · Invite others.
Full guide: https://github.com/phoenixfire808/gpu-swarm/blob/master/LOGIN.md
Download: https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe

1) Invite **glitch-factor** + your Discord display name (from a pool member — not public signup)
2) Open the portal (pick one):
   • Public HTTPS (no Tailscale) — ask the host for the **current** link
   • Tailscale: http://100.85.165.84:8767/portal
   • Or EXE (SmartScreen → More info → Run anyway if you trust the GitHub release)
3) Home → **Use the pool** (no NVIDIA needed) or **Share my PC** (VRAM=0 OK) or **Invite others** (copy blurb)

Pool password is optional (only if a pool admin shares it). Never share .env / bot tokens.
```

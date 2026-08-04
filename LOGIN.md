# How to log in to GPU Pool

Step-by-step for friends in **Glitch Factor** Discord. No screenshots needed — follow the numbered steps.

**Repo:** https://github.com/phoenixfire808/gpu-swarm  
**Primary Discord:** Glitch Factor · Bot: **GPU Pool**

---

## 1) What “login” means

GPU Pool uses **MVP invite auth** (Discord OAuth comes later). You are not creating a public account.

| Field | Required? | What to enter |
|-------|-----------|---------------|
| **Invite code** | Yes (usual path) | Shared code from Drew / admin — currently `glitch-factor` |
| **Display name** | Yes | Your Discord name (so the pool can show who you are) |
| **Pool password** | Optional | Only if Drew gave you the shared pool password instead of (or in addition to) the invite |

**Rule of thumb:** invite code + display name is enough for almost everyone.

---

## 2) WHERE to get login info

| Item | Where |
|------|--------|
| **Invite code** | From **Drew / admin in Discord (Glitch Factor)** — not a public website signup |
| **Current invite** | `glitch-factor` (Drew can rotate this anytime) |
| **Pool password** | Only if Drew DMs it — never posted publicly; lives in host `.env` |
| **Public portal URL** | From Drew (DM / Discord). Host file: `data/public_endpoints.share.txt` (URL **rotates** when the tunnel restarts) |
| **Tailscale portal** | Stable: `http://100.85.165.84:8767/portal` (you must be on Drew’s tailnet) |
| **Windows EXE** | [GitHub Releases](https://github.com/phoenixfire808/gpu-swarm/releases/latest) → `GPUPool.exe` |

Drew rotates auth via host `.env` keys (see [.env.example](.env.example)):

- `GPU_SWARM_INVITE_CODES` — comma-separated invite codes  
- `GPU_SWARM_POOL_PASSWORD` — optional shared password  

If login suddenly fails after it worked before, ask Drew whether the invite was rotated.

---

## 3) Pick a path into the portal

### Path A — Public HTTPS portal (no Tailscale) — preferred for friends

1. Drew starts the tunnel on the host PC (see [For Drew](#for-drew-host) below): `start-public-access.cmd` (portal + scheduler already running).
2. Get the **current** public URL from Drew, or (on Drew’s PC) open:
   - `data/public_endpoints.share.txt`  
   - Shape: `https://….trycloudflare.com/portal`
3. Open that URL in a browser (Chrome / Edge / Firefox).
4. You should see the **Sign in** panel. Continue to [§4 Login form](#4-exact-login-form-fields).

**Notes**

- Public links are `https://….trycloudflare.com/portal` — **no** `:8767` on the public hostname.
- Quick-tunnel hostnames **change** when Drew restarts `start-public-access.cmd`. Do not reuse an old link from chat history.

### Path B — Tailscale portal (private network)

1. Install [Tailscale](https://tailscale.com/download) and join Drew’s Glitch Factor tailnet (ask Drew).
2. Open exactly:  
   `http://100.85.165.84:8767/portal`
3. Continue to [§4 Login form](#4-exact-login-form-fields).

**Common mistake:** opening `http://100.85.165.84` without **`:8767`** and `/portal` — that will not load the portal.

### Path C — Windows desktop app (`GPUPool.exe`)

1. Download:  
   https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe  
   (also: [`DOWNLOAD.md`](DOWNLOAD.md))
2. Run the EXE. If Windows SmartScreen appears → **More info** → **Run anyway** (only if you trust Drew’s release).
3. In the wizard:
   - Prefer the **public pool-api / portal** URL Drew shared (no Tailscale needed when the tunnel is up).
   - Enter invite **`glitch-factor`** + your Discord display name.
   - Set **your** resource caps (VRAM can be **0** if you have no NVIDIA GPU). Caps save locally and apply to **your** worker only.
   - **Save + Join**.
4. Optional: open the browser portal (Path A or B) for Utilize / Connect UI.

**Personal offer control:** Only you control how much of your PC is offered. Change anytime on your machine or in Contribute settings. Nobody else can remotely raise your caps.

---

## 4) Exact login form fields

On `/portal` → **Sign in**:

1. **Display name** — your Discord name (e.g. `aariff01`).
2. **Invite code** — `glitch-factor` (unless Drew gave you a newer code).
3. **Pool password** — leave blank unless Drew told you to use it.
4. Click **Enter portal**.

You should land on **Home** signed in as your display name.

---

## 5) After login — Contribute vs Utilize vs Connect

| Path | What it does | Who it’s for |
|------|--------------|--------------|
| **Contribute** | Register this PC, set **your** GPU/CPU/RAM/disk offer caps, run a worker that takes allowlisted jobs. Only you can change your offer. | Friends with spare compute (GPU optional — VRAM=0 = CPU-only) |
| **Utilize** | Submit allowlisted jobs (`probe`, CUDA probe, etc.); they run on online workers | Anyone — especially laptops with **no NVIDIA** |
| **Connect** | URLs, Discord slash commands, CLI / Python SDK how-to | Coders and agents |

More detail: [`CONNECTING.md`](CONNECTING.md).

**Laptop / no NVIDIA?** Use **Utilize** (jobs run on pool GPUs). Optional: Contribute with VRAM=0.

---

## 6) Troubleshooting

| Symptom | Fix |
|---------|-----|
| **Black / blank portal screen** | Hard refresh (**Ctrl+F5**). Confirm you opened the **latest** public URL from Drew (tunnels rotate). Try another browser. |
| **Wrong URL / page won’t load** | Public: must end with `/portal`. Tailscale: must include **`:8767`** and `/portal`. Bare IP with no port will fail. |
| **“Invalid pool password or invite code”** | Re-check invite spelling (`glitch-factor`). Ask Drew if the code was rotated. Pool password is optional — leave blank if you only have the invite. |
| **No NVIDIA / no nvidia-smi** | Expected on many laptops. Use **Utilize**, or Contribute with VRAM=0. |
| **Windows SmartScreen on GPUPool.exe** | Unsigned builds warn by default → More info → Run anyway if you trust the GitHub release from this repo. |
| **Tunnel URL expired / 404** | Ask Drew for a fresh link; host: re-run `start-public-access.cmd` and read `data/public_endpoints.share.txt`. |
| **CLI / SDK can’t connect** | Public: `GPU_SWARM_SCHEDULER_URL=https://….trycloudflare.com/pool-api` · Tailscale: `http://100.85.165.84:8766` — not the portal URL. |

---

## For Drew (host)

### Share invite / password safely

1. Open `.env.example` for the **key names** (do not paste real `.env` into Discord or git):
   - `GPU_SWARM_INVITE_CODES`
   - `GPU_SWARM_POOL_PASSWORD`
2. On the host, read your local `.env` (never commit it) and DM friends only what they need — usually the **invite code**, not the pool password.
3. To rotate: change the value in `.env`, restart portal (`start-portal.cmd`), tell friends the new invite.

### Share the current public URL

```bat
cd C:\Users\Drew\Projects\gpu-swarm
start-scheduler-lan.cmd
start-portal.cmd
start-public-access.cmd
```

Then either:

- Copy the Portal line from `data\public_endpoints.share.txt`, or  
- Ask an agent/friend to “ask Drew for the current public link”

`data/` is gitignored — do **not** commit `public_endpoints.json` / `.share.txt` / `.env`.

Stable private fallback for friends already on Tailscale:  
`http://100.85.165.84:8767/portal`

---

## Related docs

- [`DISCORD_MEMBER_QUICKSTART.md`](DISCORD_MEMBER_QUICKSTART.md) — short / paste-ready  
- [`DOWNLOAD.md`](DOWNLOAD.md) — Windows EXE  
- [`FRIEND_LAPTOP.md`](FRIEND_LAPTOP.md) — no-GPU laptop path  
- [`CONNECTING.md`](CONNECTING.md) — Contribute / Utilize / Connect from code  

---

## Paste-ready Discord blurb

Copy everything inside the fence into Discord:

```text
**GPU Pool — how to log in**
Full guide: https://github.com/phoenixfire808/gpu-swarm/blob/master/LOGIN.md

1) Get invite from Drew in Glitch Factor (current: **glitch-factor**) + use your Discord display name
2) Open the portal (pick one):
   • Public HTTPS (no Tailscale) — ask Drew for the **current** link
     (host: data/public_endpoints.share.txt · rotates when tunnel restarts)
   • Tailscale: http://100.85.165.84:8767/portal
   • Or EXE: https://github.com/phoenixfire808/gpu-swarm/releases/latest/download/GPUPool.exe
3) Sign in → Home → **Utilize** (run jobs) or **Contribute** (plug in PC; VRAM=0 OK if no NVIDIA)

Pool password is optional (only if Drew DMs it). Never share .env / bot tokens.
```

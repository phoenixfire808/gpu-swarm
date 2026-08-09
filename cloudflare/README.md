# GPU Pool Cloudflare public access

GPU Pool can publish **each host's own local portal** through Cloudflare. This is
optional and host-specific; it does not reuse another machine's tunnel or
credentials.

## Easiest path: the installer wizard

1. Start `GPUPool.exe`.
2. Open **Network & Workspace**.
3. In **Public access with Cloudflare**, click **Install Cloudflare helper**.
4. When the local GPU Pool portal is running, click **Publish temporary HTTPS link**.
5. Share the generated `/portal` URL and the pool invite code with friends.
6. For a stable hostname, enter the Cloudflare-managed hostname and tunnel name, then click **Create & launch named tunnel**. The wizard opens a separate setup window for browser login, tunnel creation, DNS routing, config generation, launch, and public verification.
7. **Stable hostname guide** remains available when you want to inspect the exact files and commands.

### The two modes

| Mode | Account required | URL | Best for |
|---|---:|---|---|
| Quick Tunnel | No | Temporary `trycloudflare.com` URL | Demos and friend testing |
| Named Tunnel | Yes, plus a domain in Cloudflare | Your hostname | A stable shared address |

The installer never publishes port `8766` directly. The public browser path is
`/portal`, and the portal's `/pool-api` route is the only scheduler path exposed
to the browser. Invite authentication and allowlisted jobs remain enabled.

## Source/CLI fallback

From a full GPU Pool checkout, with the local portal already running on
`http://127.0.0.1:8767`:

```bat
python -m gpu_swarm.cloudflare_access --install
python -m gpu_swarm.cloudflare_access --quick
scripts\setup_cloudflare_named.cmd -Hostname gpu-pool.example.com -TunnelName gpu-pool -Launch
```

Use `--no-browser` when the URL should be printed without opening a browser:

```bat
python -m gpu_swarm.cloudflare_access --quick --no-browser
```

The verified endpoint is written to the ignored files:

```text
data\public_endpoints.json
data\public_endpoints.share.txt
```

## Named Tunnel setup

1. Choose a hostname on a domain managed in the user's Cloudflare account, for
   example `gpu-pool.example.com`.
2. Install the helper from the wizard or source command above.
3. Authenticate locally. This opens the browser and stores the certificate under
   `%USERPROFILE%\.cloudflared\`; no secret belongs in chat or the repository:

   ```bat
   cloudflared.exe tunnel login
   ```

4. Create a dedicated tunnel. Use a unique name for this host, such as
   `gpu-pool-my-pc`:

   ```bat
   cloudflared.exe tunnel create gpu-pool-my-pc
   ```

5. Copy `cloudflare\gpu-pool.tunnel.yml.example` to:

   ```text
   %USERPROFILE%\.cloudflared\gpu-pool.yml
   ```

   Set:

   - `tunnel:` to the new tunnel name or UUID;
   - `credentials-file:` to that tunnel's credential JSON;
   - `hostname:` to the user's Cloudflare-managed hostname.

6. Route DNS to that new tunnel:

   ```bat
   cloudflared.exe tunnel route dns gpu-pool-my-pc gpu-pool.example.com
   ```

7. Start and verify the named tunnel:

   ```bat
   python -m gpu_swarm.cloudflare_access --named ^
     --hostname gpu-pool.example.com ^
     --tunnel-name gpu-pool-my-pc ^
     --config "%USERPROFILE%\.cloudflared\gpu-pool.yml" ^
     --no-browser
   ```

   PowerShell users can put the arguments on one line instead of using `^`.

Acceptance requires both routes to respond successfully:

```bat
curl.exe https://gpu-pool.example.com/portal
curl.exe https://gpu-pool.example.com/pool-api/status
```

The endpoint artifact must report `mode=cloudflared_named`.

## Credential and safety rules

- Cloudflare credentials stay under `%USERPROFILE%\.cloudflared\`.
- Never commit `.cloudflared`, tunnel JSON files, `.env`, or `data\public_endpoints*`.
- Do not reuse the Mission Control/OpenClaw tunnel configuration.
- A stable hostname still depends on the host computer, local portal, and
  `cloudflared` process remaining online.
- The Cloudflare helper is a connector, not a GPU execution service.

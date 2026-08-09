"""
start_public_tunnel.py — invoke scripts/start_public_tunnel.ps1 as a detached
hidden process, then wait for the new trycloudflare.com URL to appear in
data/cloudflared_portal.log and write it into data/public_endpoints.json (the
PS script does this itself; we just verify).

Mirrors start_hidden.py so Task Scheduler can register the tunnel with the
same lifecycle / hidden-window guarantees.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000080

REPO_ROOT = Path(__file__).resolve().parent.parent
PS_SCRIPT = REPO_ROOT / "scripts" / "start_public_tunnel.ps1"
DATA = REPO_ROOT / "data"
LOG = DATA / "cloudflared_portal.log"
JSON_OUT = DATA / "public_endpoints.json"
URL_RE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")


def _powershell() -> str:
    for cand in (
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "powershell.exe",
    ):
        if Path(cand).exists():
            return cand
    raise SystemExit("ERROR: powershell.exe not found")


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)

    # Truncate the old log so the URL regex matches only the fresh tunnel
    if LOG.exists():
        try:
            LOG.unlink()
        except OSError:
            pass

    ps = _powershell()
    args = [
        ps,
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", str(PS_SCRIPT),
        "-SkipPortalCheck",  # we already verified portal above
    ]

    # Forward stdout/stderr to a small log so we can scrape the URL
    ps_log = DATA / "start_public_tunnel.log"
    ps_logf = ps_log.open("ab", buffering=0)
    ps_logf.write(b"\n--- start_public_tunnel.py launch ---\n")

    proc = subprocess.Popen(
        args,
        cwd=str(REPO_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=ps_logf,
        stderr=subprocess.STDOUT,
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
    )
    print(f"Started tunnel (powershell pid {proc.pid}). Log: {ps_log}")

    # Wait up to 90s for the URL to appear. Require either a JSON mtime bump
    # or a fresh cloudflared_portal.log line -- never trust the pre-existing
    # JSON which may still contain a stale URL from a previous tunnel.
    deadline = time.time() + 90
    url = None
    json_mtime_before = JSON_OUT.stat().st_mtime if JSON_OUT.exists() else 0.0
    while time.time() < deadline:
        # JSON file was rewritten by the PS script with the new URL
        if JSON_OUT.exists():
            try:
                if JSON_OUT.stat().st_mtime > json_mtime_before + 0.5:
                    txt = JSON_OUT.read_text(encoding="utf-8", errors="replace")
                    m = URL_RE.search(txt)
                    if m:
                        url = m.group(0).rstrip("/")
                        break
            except OSError:
                pass
        # cloudflared log line is more immediate
        if LOG.exists():
            try:
                m = URL_RE.search(LOG.read_text(encoding="utf-8", errors="replace"))
                if m:
                    url = m.group(0).rstrip("/")
            except OSError:
                pass
        time.sleep(1)

    if not url:
        print("BLOCKER: no trycloudflare.com URL appeared in 60s.", file=sys.stderr)
        print(f"Check {ps_log} and {LOG}.", file=sys.stderr)
        return 2

    print(f"Public URL: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

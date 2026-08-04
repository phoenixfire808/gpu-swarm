"""Bridge GPU Pool → Hermes agent-vm (VirtualBox/Vagrant).

Maps Contribute / host_protect offer caps onto VM CPU + RAM. Does **not**
passthrough host NVIDIA GPUs into VirtualBox — pool jobs keep using the host
worker for real GPU share.
"""

from __future__ import annotations

import os
import re
import subprocess
import webbrowser
from pathlib import Path
from typing import Any

from gpu_swarm.host import query_host
from gpu_swarm.host_protect import apply_offer_caps, load_host_protect
from gpu_swarm.joiner_settings import (
    AGENT_VMS_DEFAULT,
    JoinerSettings,
    agent_vms_present,
    load_settings,
)

PRIMARY_SESSION = "agent-ubuntu"
DEFAULT_DISPLAY_VRAM_MB = 64
MIN_VM_RAM_MB = 1024
HOST_RAM_RESERVE_MB = 2048
MAX_VM_CPUS = 8
MAX_VM_RAM_MB = 16384

GPU_HONESTY = (
    "VirtualBox on Windows does not pass through host NVIDIA GPUs. "
    "The workspace VM gets capped CPU/RAM only. Shared GPU/VRAM stays on the "
    "host contributor worker for pool jobs (probe / llm_chat / CUDA)."
)


def _localappdata() -> Path:
    raw = os.environ.get("LOCALAPPDATA", "").strip()
    if raw:
        return Path(raw)
    return Path.home() / "AppData" / "Local"


def resolve_agent_vm_controller(settings: JoinerSettings | None = None) -> dict[str, Any]:
    """Locate Hermes/project agent-vm entrypoints (prefer project bin)."""
    s = settings or load_settings()
    project = Path(s.agent_vms_path or AGENT_VMS_DEFAULT)
    cmd = project / "bin" / "agent-vm.cmd"
    ps1 = project / "bin" / "agent-vm.ps1"
    hermes = _localappdata() / "hermes" / "scripts" / "agent-vm.ps1"
    present = agent_vms_present(project)
    controller: Path | None = None
    kind = ""
    if cmd.is_file():
        controller = cmd
        kind = "cmd"
    elif ps1.is_file():
        controller = ps1
        kind = "ps1"
    elif hermes.is_file():
        controller = hermes
        kind = "hermes_ps1"
    return {
        "ok": controller is not None and bool(present.get("ready")),
        "controller": str(controller) if controller else "",
        "kind": kind,
        "project": str(project),
        "hermes_shim": str(hermes),
        "present": present,
        "control_plane": "hermes",
    }


def compute_vm_resource_plan(
    settings: JoinerSettings | None = None,
    *,
    host: dict[str, Any] | None = None,
    total_vram_mb: int = 0,
    free_vram_mb: int = 0,
) -> dict[str, Any]:
    """Map real Contribute + host_protect offer caps → VirtualBox CPU/RAM.

    Uses live host inventory (no mocks). GPU offer is recorded for honesty only.
    """
    s = settings or load_settings()
    h = host if host is not None else query_host()
    cores = max(0, int(h.get("cpu_cores") or 0))
    ram_total = max(0, int(h.get("ram_total_mb") or 0))
    ram_avail = max(0, int(h.get("ram_available_mb") or 0))

    hp = load_host_protect(enabled_override=bool(getattr(s, "host_protect", True)))
    offered = apply_offer_caps(
        total_vram_mb=int(total_vram_mb or 0),
        free_vram_mb=int(free_vram_mb or 0),
        max_vram_mb=int(s.max_vram_mb or 0),
        max_cpu_percent=float(s.max_cpu_percent or 50.0),
        cfg=hp,
    )
    cpu_pct = float(offered["max_cpu_percent"])
    # apply_offer_caps only clamps CPU when total_vram>0; VM path always respects
    # the host_protect CPU ceiling so the guest cannot exceed the safety share.
    if hp.enabled and cpu_pct > hp.max_cpu_percent:
        cpu_pct = float(hp.max_cpu_percent)
        offered = {**offered, "max_cpu_percent": cpu_pct}

    if cores <= 0:
        vm_cpus = 1
    else:
        raw = max(1, int(cores * (cpu_pct / 100.0)))
        # Leave at least one host logical CPU when possible.
        host_keep = 1 if cores > 1 else 0
        vm_cpus = max(1, min(raw, cores - host_keep, MAX_VM_CPUS))

    user_ram = int(getattr(s, "max_ram_mb", 0) or 0)
    if user_ram > 0:
        vm_ram = user_ram
    else:
        # Soft default from CPU share of available RAM (not whole machine).
        share = max(0.15, min(cpu_pct / 100.0, 0.75))
        vm_ram = int(ram_avail * share) if ram_avail > 0 else MIN_VM_RAM_MB

    # Never starve the host desktop; clamp to offer + hard ceilings.
    if ram_avail > 0:
        vm_ram = min(vm_ram, max(MIN_VM_RAM_MB, ram_avail - HOST_RAM_RESERVE_MB))
    if ram_total > 0:
        vm_ram = min(vm_ram, max(MIN_VM_RAM_MB, ram_total - HOST_RAM_RESERVE_MB))
    vm_ram = max(MIN_VM_RAM_MB, min(vm_ram, MAX_VM_RAM_MB))

    disk_gb = float(getattr(s, "max_disk_gb", 0.0) or 0.0)
    return {
        "session": PRIMARY_SESSION,
        "cpus": int(vm_cpus),
        "memory_mb": int(vm_ram),
        "display_vram_mb": DEFAULT_DISPLAY_VRAM_MB,
        "offer": {
            "max_cpu_percent": cpu_pct,
            "max_ram_mb": user_ram,
            "max_vram_mb": int(offered["max_vram_mb"]),
            "max_disk_gb": disk_gb,
            "host_protect": offered.get("host_protect") or hp.summary(),
        },
        "host": {
            "cpu_cores": cores,
            "ram_total_mb": ram_total,
            "ram_available_mb": ram_avail,
        },
        "disk_note": (
            "max_disk_gb is a pool scheduling soft-cap / capacity ad. "
            "Linked-clone disk size is not resized for the VM in this MVP."
        ),
        "gpu_note": GPU_HONESTY,
        "mapping": (
            f"CPU offer {cpu_pct:.0f}% of {cores} host cores → vm.cpus={vm_cpus}; "
            f"RAM offer {user_ram or 'auto'} → vm.memory_mb={vm_ram}; "
            f"GPU/VRAM offer {int(offered['max_vram_mb'])} MiB stays on host worker."
        ),
    }


def _parse_kv_output(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key:
            out[key] = val.strip()
    return out


def run_agent_vm(
    *args: str,
    settings: JoinerSettings | None = None,
    timeout: float = 90.0,
) -> dict[str, Any]:
    """Run Hermes agent-vm CLI. Light commands only (status/resources/ip)."""
    resolved = resolve_agent_vm_controller(settings)
    controller = resolved.get("controller") or ""
    if not controller:
        return {
            "ok": False,
            "error": "agent-vm controller not found",
            "detail": (
                "Install/clone agent-vms and ensure bin/agent-vm.cmd exists, "
                "or %LOCALAPPDATA%\\hermes\\scripts\\agent-vm.ps1"
            ),
            "resolved": resolved,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
        }

    kind = resolved.get("kind")
    if kind == "cmd":
        cmd = ["cmd.exe", "/c", controller, *[str(a) for a in args]]
    else:
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            controller,
            *[str(a) for a in args],
        ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=resolved.get("project") or None,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": "agent-vm timed out",
            "detail": f"timeout={timeout}s args={list(args)}",
            "resolved": resolved,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
        }
    except OSError as exc:
        return {
            "ok": False,
            "error": "failed to launch agent-vm",
            "detail": str(exc),
            "resolved": resolved,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
        }

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "kv": _parse_kv_output(stdout),
        "args": list(args),
        "resolved": resolved,
        "error": "" if proc.returncode == 0 else (stderr.strip() or stdout.strip() or "agent-vm failed"),
    }


def workspace_status(settings: JoinerSettings | None = None) -> dict[str, Any]:
    """Light status: controller + primary session resources + RDP hint."""
    s = settings or load_settings()
    plan = compute_vm_resource_plan(s)
    resolved = resolve_agent_vm_controller(s)
    result: dict[str, Any] = {
        "ok": bool(resolved.get("ok")),
        "ready": bool(resolved.get("ok")),
        "control_plane": "hermes",
        "session": PRIMARY_SESSION,
        "plan": plan,
        "resolved": resolved,
        "gpu_note": GPU_HONESTY,
        "rdp_host": "127.0.0.1",
        "rdp_port": 3390,
        "rdp_user": "vagrant",
        "rdp_password": "vagrant",
        "hint_rdp": "mstsc /v:127.0.0.1:3390",
        "vm_status": "unknown",
        "vm_cpus": None,
        "vm_memory_mb": None,
        "caps_match": None,
        "message": "",
    }
    if not resolved.get("ok"):
        result["message"] = (
            "agent-vms not ready on this machine. "
            f"Expected {resolved.get('project')} with Vagrantfile + bin/agent-vm.cmd."
        )
        return result

    # Prefer resources show (fast) over full status.
    res = run_agent_vm("resources", "show", PRIMARY_SESSION, settings=s, timeout=45.0)
    if not res.get("ok"):
        # Fallback: ip (also light)
        res = run_agent_vm("ip", settings=s, timeout=45.0)
    kv = res.get("kv") or {}
    result["agent_vm_ok"] = bool(res.get("ok"))
    result["agent_vm_error"] = res.get("error") or ""
    result["raw"] = (res.get("stdout") or "")[:4000]
    if kv.get("status"):
        result["vm_status"] = kv["status"]
    if kv.get("cpus") and kv["cpus"].isdigit():
        result["vm_cpus"] = int(kv["cpus"])
    if kv.get("memory_mb") and re.fullmatch(r"\d+", kv["memory_mb"]):
        result["vm_memory_mb"] = int(kv["memory_mb"])
    if kv.get("rdp_port") and kv["rdp_port"].isdigit():
        result["rdp_port"] = int(kv["rdp_port"])
    if kv.get("rdp_host"):
        result["rdp_host"] = kv["rdp_host"]
    if kv.get("hint_rdp"):
        result["hint_rdp"] = kv["hint_rdp"]
    if kv.get("user"):
        result["rdp_user"] = kv["user"]
    if kv.get("password"):
        result["rdp_password"] = kv["password"]

    cur_c = result.get("vm_cpus")
    cur_m = result.get("vm_memory_mb")
    if cur_c is not None and cur_m is not None:
        result["caps_match"] = (
            int(cur_c) <= int(plan["cpus"]) and int(cur_m) <= int(plan["memory_mb"])
        )
    running = str(result.get("vm_status") or "").lower() == "running"
    if running and result.get("caps_match") is False:
        result["message"] = (
            f"VM running at {cur_c} CPU / {cur_m} MiB RAM; offer maps to "
            f"{plan['cpus']} CPU / {plan['memory_mb']} MiB. "
            "Halt then Start workspace to clamp (modifyvm needs power-off)."
        )
    elif running:
        result["message"] = (
            f"Workspace running — RDP {result['rdp_host']}:{result['rdp_port']} "
            f"(login {result['rdp_user']}/{result['rdp_password']}). {plan['mapping']}"
        )
    elif result.get("agent_vm_ok"):
        result["message"] = (
            f"Workspace stopped ({result.get('vm_status')}). "
            f"Start applies offer caps: {plan['cpus']} CPU / {plan['memory_mb']} MiB RAM."
        )
    else:
        result["message"] = result.get("agent_vm_error") or "agent-vm status failed"
        result["ok"] = False
    return result


def apply_workspace_caps(
    settings: JoinerSettings | None = None,
    *,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply CPU/RAM caps to primary VM (must be powered off)."""
    s = settings or load_settings()
    p = plan or compute_vm_resource_plan(s)
    res = run_agent_vm(
        "resources",
        "apply",
        PRIMARY_SESSION,
        "--cpus",
        str(int(p["cpus"])),
        "--memory-mb",
        str(int(p["memory_mb"])),
        "--vram-mb",
        str(int(p.get("display_vram_mb") or DEFAULT_DISPLAY_VRAM_MB)),
        settings=s,
        timeout=60.0,
    )
    return {
        "ok": bool(res.get("ok")),
        "plan": p,
        "kv": res.get("kv") or {},
        "stdout": res.get("stdout") or "",
        "error": res.get("error") or "",
        "gpu_note": GPU_HONESTY,
        "message": (
            "Applied VM CPU/RAM caps from Contribute offer."
            if res.get("ok")
            else (res.get("error") or "Failed to apply caps")
        ),
    }


def open_rdp_session(
    host: str = "127.0.0.1",
    port: int = 3390,
) -> dict[str, Any]:
    """Launch Windows Remote Desktop to the guest XFCE session."""
    target = f"{host}:{int(port)}"
    mstsc = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "mstsc.exe"
    try:
        if mstsc.is_file():
            subprocess.Popen(
                [str(mstsc), f"/v:{target}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {
                "ok": True,
                "method": "mstsc",
                "target": target,
                "message": f"Opened Remote Desktop → {target} (vagrant/vagrant)",
            }
        # Fallback: rdp URL handler
        webbrowser.open(f"rdp://full%20address=s:{target}")
        return {
            "ok": True,
            "method": "rdp_url",
            "target": target,
            "message": f"Opened RDP URL → {target}",
        }
    except OSError as exc:
        return {
            "ok": False,
            "method": "none",
            "target": target,
            "error": str(exc),
            "message": f"Could not open RDP. Run manually: mstsc /v:{target}",
        }


def open_workspace(
    settings: JoinerSettings | None = None,
    *,
    start_if_needed: bool = True,
    open_rdp: bool = True,
    allow_vagrant_up: bool = False,
) -> dict[str, Any]:
    """Start (if safe) + open the agent Ubuntu workspace under offer caps.

    By default does **not** run a cold ``vagrant up`` (can be long). If the VM
    already exists and is powered off, starts it with caps. If missing, returns
    instructions unless ``allow_vagrant_up=True``.
    """
    s = settings or load_settings()
    plan = compute_vm_resource_plan(s)
    st = workspace_status(s)
    actions: list[str] = []
    status = str(st.get("vm_status") or "").lower()

    if status == "missing" or (
        not st.get("agent_vm_ok") and "missing" in str(st.get("raw") or "").lower()
    ):
        if not allow_vagrant_up:
            return {
                "ok": False,
                "started": False,
                "rdp": None,
                "plan": plan,
                "status": st,
                "gpu_note": GPU_HONESTY,
                "message": (
                    "Primary VM not found. Bring it up once via Hermes "
                    "(agent-vm up) — then GPU Pool can start/open with caps. "
                    "Skipping automatic vagrant up to avoid a long download/boot."
                ),
                "actions": actions,
            }

    if status != "running" and start_if_needed:
        # Apply caps then start primary (uses VBox start path when already imported).
        start = run_agent_vm(
            "up",
            "--cpus",
            str(int(plan["cpus"])),
            "--memory-mb",
            str(int(plan["memory_mb"])),
            "--vram-mb",
            str(int(plan.get("display_vram_mb") or DEFAULT_DISPLAY_VRAM_MB)),
            settings=s,
            timeout=180.0 if allow_vagrant_up else 90.0,
        )
        actions.append("up")
        if not start.get("ok"):
            err = start.get("error") or ""
            # If vagrant up is heavy/missing, surface cleanly.
            return {
                "ok": False,
                "started": False,
                "rdp": None,
                "plan": plan,
                "status": st,
                "start": start,
                "gpu_note": GPU_HONESTY,
                "message": err or "Failed to start workspace",
                "actions": actions,
            }
        actions.append("caps_on_start")
        st = workspace_status(s)
    elif status == "running" and st.get("caps_match") is False:
        actions.append("caps_deferred_needs_halt")

    rdp_result = None
    if open_rdp:
        rdp_result = open_rdp_session(
            host=str(st.get("rdp_host") or "127.0.0.1"),
            port=int(st.get("rdp_port") or 3390),
        )
        actions.append("rdp")

    running = str(st.get("vm_status") or "").lower() == "running"
    msg_parts = [
        st.get("message") or "",
        plan.get("mapping") or "",
        GPU_HONESTY,
    ]
    if rdp_result and rdp_result.get("message"):
        msg_parts.insert(0, str(rdp_result["message"]))
    return {
        "ok": running or bool(rdp_result and rdp_result.get("ok")),
        "started": "up" in actions,
        "rdp": rdp_result,
        "plan": plan,
        "status": st,
        "gpu_note": GPU_HONESTY,
        "message": " ".join(p for p in msg_parts if p),
        "actions": actions,
    }


def halt_workspace(settings: JoinerSettings | None = None) -> dict[str, Any]:
    """Stop primary agent-ubuntu via Hermes agent-vm."""
    s = settings or load_settings()
    res = run_agent_vm("halt", settings=s, timeout=120.0)
    return {
        "ok": bool(res.get("ok")),
        "stdout": res.get("stdout") or "",
        "error": res.get("error") or "",
        "message": (
            "Workspace halted."
            if res.get("ok")
            else (res.get("error") or "Halt failed")
        ),
    }

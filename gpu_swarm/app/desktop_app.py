"""
GPU Pool desktop joiner — customtkinter UI (Worker 1).

Calls only gpu_swarm.app_backend stable APIs.
Browser portal = easiest remote path; this app = power-user native joiner.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

import customtkinter as ctk

from gpu_swarm import app_backend as be

APP_TITLE = "GPU Pool"
ACCENT = "#2DD4A8"
WARN = "#F0B429"
MUTED = "#9AA4B2"
BG = "#0F1419"
PANEL = "#1A2332"
DANGER = "#E85D5D"
OK_GREEN = "#3DDC97"


def run_app() -> int:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = GpuPoolApp()
    app.mainloop()
    return 0


class GpuPoolApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} — Native Joiner")
        self.geometry("980x720")
        self.minsize(860, 640)
        self.configure(fg_color=BG)

        self.settings = be.load_config()
        self._poll_after: str | None = None
        self._busy = False

        self._container = ctk.CTkFrame(self, fg_color=BG)
        self._container.pack(fill="both", expand=True)

        if not self.settings.wizard_completed:
            self._show_wizard()
        else:
            self._show_main()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # --- navigation ------------------------------------------------------------

    def _clear(self) -> None:
        for child in self._container.winfo_children():
            child.destroy()

    def _show_wizard(self) -> None:
        self._clear()
        WizardFrame(self._container, self, on_done=self._wizard_done).pack(fill="both", expand=True)

    def _wizard_done(self) -> None:
        self.settings = be.load_config()
        self._show_main()

    def _show_main(self) -> None:
        self._clear()
        MainFrame(self._container, self).pack(fill="both", expand=True)

    def _on_close(self) -> None:
        if self._poll_after:
            try:
                self.after_cancel(self._poll_after)
            except Exception:  # noqa: BLE001
                pass
        self.destroy()


# =============================================================================
# Setup wizard
# =============================================================================


class WizardFrame(ctk.CTkFrame):
    STEPS = ("Welcome", "Hardware", "Deps", "Identity", "Connect", "Caps")

    def __init__(self, master: Any, app: GpuPoolApp, on_done: Callable[[], None]) -> None:
        super().__init__(master, fg_color=BG)
        self.app = app
        self.on_done = on_done
        self.step = 0
        self.settings = be.load_config()
        self._gpu_info: dict[str, Any] = {}
        self._host_info: dict[str, Any] = {}
        self._build()
        self._render_step()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="GPU Pool Setup",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=22),
            text_color=ACCENT,
        ).pack(side="left", padx=24, pady=16)
        self.step_label = ctk.CTkLabel(header, text="", text_color=MUTED, font=ctk.CTkFont(size=13))
        self.step_label.pack(side="right", padx=24)

        self.body = ctk.CTkFrame(self, fg_color=BG)
        self.body.pack(fill="both", expand=True, padx=28, pady=18)

        nav = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0, height=64)
        nav.pack(fill="x", side="bottom")
        nav.pack_propagate(False)
        self.back_btn = ctk.CTkButton(nav, text="Back", width=110, command=self._back, fg_color="#2A3544")
        self.back_btn.pack(side="left", padx=24, pady=14)
        self.next_btn = ctk.CTkButton(
            nav, text="Next", width=140, command=self._next, fg_color=ACCENT, text_color="#0A1210"
        )
        self.next_btn.pack(side="right", padx=24, pady=14)

    def _render_step(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        name = self.STEPS[self.step]
        self.step_label.configure(text=f"Step {self.step + 1} / {len(self.STEPS)} — {name}")
        self.back_btn.configure(state="normal" if self.step > 0 else "disabled")
        self.next_btn.configure(text="Finish" if self.step == len(self.STEPS) - 1 else "Next")

        {
            0: self._step_welcome,
            1: self._step_hardware,
            2: self._step_deps,
            3: self._step_identity,
            4: self._step_connect,
            5: self._step_caps,
        }[self.step]()

    def _title(self, text: str, sub: str = "") -> None:
        ctk.CTkLabel(self.body, text=text, font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w")
        if sub:
            ctk.CTkLabel(self.body, text=sub, text_color=MUTED, wraplength=820, justify="left").pack(
                anchor="w", pady=(6, 14)
            )

    def _step_welcome(self) -> None:
        self._title(
            "Welcome to GPU Pool",
            "Plug spare GPUs, RAM, CPU, and disk into Drew's private co-op pool.",
        )
        banner = ctk.CTkFrame(self.body, fg_color=PANEL, corner_radius=10)
        banner.pack(fill="x", pady=8)
        ctk.CTkLabel(
            banner,
            text="Easiest remote path: the web portal (browser login + dynamic machines).",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT,
            wraplength=800,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            banner,
            text=(
                "This desktop app is the power-user native joiner: local nvidia-smi detection, "
                "fine-grained dedication sliders, and one-click Join/Leave for a host worker."
            ),
            text_color=MUTED,
            wraplength=800,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 14))

        portal = be.get_portal_url(self.settings)
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", pady=12)
        ctk.CTkLabel(row, text=f"Portal: {portal}", text_color=MUTED).pack(side="left")
        ctk.CTkButton(
            row,
            text="Open portal",
            width=130,
            fg_color="#2A3544",
            command=lambda: be.open_portal_url(self.portal_entry.get() if hasattr(self, "portal_entry") else portal),
        ).pack(side="right")

        ctk.CTkLabel(self.body, text="Portal URL (editable)", text_color=MUTED).pack(anchor="w", pady=(8, 2))
        self.portal_entry = ctk.CTkEntry(self.body, height=36)
        self.portal_entry.pack(fill="x")
        self.portal_entry.insert(0, portal)

    def _step_hardware(self) -> None:
        self._title("Detect hardware", "Live nvidia-smi + host RAM/disk (no mock data).")
        self.hw_box = ctk.CTkTextbox(self.body, height=280, fg_color=PANEL)
        self.hw_box.pack(fill="both", expand=True, pady=8)
        ctk.CTkButton(self.body, text="Refresh detection", command=self._scan_hw, fg_color="#2A3544").pack(
            anchor="e", pady=6
        )
        self._scan_hw()

    def _scan_hw(self) -> None:
        gpus = be.get_gpus()
        self._host_info = be.detect_host_resources()
        nv = be.check_nvidia()
        total_vram = sum(int(g.get("memory_total_mb") or 0) for g in gpus)
        free_vram = sum(int(g.get("memory_free_mb") or 0) for g in gpus)
        self._gpu_info = {
            "gpus": gpus,
            "gpu_count": len(gpus),
            "total_vram_mb": total_vram,
            "free_vram_mb": free_vram,
        }
        lines = [
            f"NVIDIA: {'OK' if nv.get('ok') else 'MISSING'} — {nv.get('message')}",
            f"Path: {nv.get('path') or 'n/a'}",
            "",
            f"GPUs: {len(gpus)}",
            f"Total VRAM: {total_vram} MiB",
            f"Free VRAM:  {free_vram} MiB",
        ]
        for g in gpus:
            lines.append(
                f"  [{g.get('index')}] {g.get('name')} — "
                f"{g.get('memory_total_mb')} MiB total / {g.get('memory_free_mb')} MiB free"
            )
        if not gpus and not nv.get("ok"):
            lines.append("GPU error: nvidia-smi unavailable (via app_backend.get_gpus)")
        lines += [
            "",
            f"RAM total/avail: {self._host_info.get('total_ram_mb', 0)} / "
            f"{self._host_info.get('avail_ram_mb', 0)} MiB",
            f"Disk total/free: {self._host_info.get('total_disk_gb', 0)} / "
            f"{self._host_info.get('free_disk_gb', 0)} GiB",
        ]
        if self._host_info.get("error"):
            lines.append(f"Host note: {self._host_info['error']}")
        self.hw_box.delete("1.0", "end")
        self.hw_box.insert("1.0", "\n".join(lines))

    def _step_deps(self) -> None:
        self._title("Python dependencies", "Uses existing installs when possible.")
        status = be.check_python_deps()
        msg = "All required packages present." if status.get("ok") else f"Missing: {', '.join(status.get('missing') or [])}"
        ctk.CTkLabel(
            self.body,
            text=msg,
            text_color=OK_GREEN if status.get("ok") else WARN,
            font=ctk.CTkFont(size=14),
        ).pack(anchor="w", pady=8)
        self.deps_log = ctk.CTkTextbox(self.body, height=180, fg_color=PANEL)
        self.deps_log.pack(fill="x", pady=8)
        ctk.CTkButton(
            self.body,
            text="Install from requirements.txt",
            command=self._install_deps,
            fg_color="#2A3544",
        ).pack(anchor="e")

    def _install_deps(self) -> None:
        self.deps_log.delete("1.0", "end")
        self.deps_log.insert("1.0", "Installing (may take a minute)…\n")

        def work() -> None:
            result = be.install_requirements()
            self.after(0, lambda: self._deps_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _deps_done(self, result: dict[str, Any]) -> None:
        self.deps_log.insert("end", result.get("message") or str(result))
        status = be.check_python_deps()
        if status.get("ok"):
            self.deps_log.insert("end", "\n\nDeps OK.")

    def _step_identity(self) -> None:
        self._title("Worker identity", "Name shown in the pool + optional Discord username.")
        ctk.CTkLabel(self.body, text="Display name", text_color=MUTED).pack(anchor="w")
        self.name_entry = ctk.CTkEntry(self.body, height=36)
        self.name_entry.pack(fill="x", pady=(0, 10))
        self.name_entry.insert(0, self.settings.worker_name)
        ctk.CTkLabel(self.body, text="Discord username (optional)", text_color=MUTED).pack(anchor="w")
        self.discord_entry = ctk.CTkEntry(self.body, height=36)
        self.discord_entry.pack(fill="x")
        self.discord_entry.insert(0, self.settings.discord_user or "")

    def _step_connect(self) -> None:
        self._title("Scheduler connection", "Tailscale URL for remote; localhost for same-machine demos.")
        ts = be.get_tailscale_ipv4()
        ctk.CTkLabel(
            self.body,
            text=f"Detected Tailscale IPv4: {ts or 'not found'}",
            text_color=MUTED,
        ).pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(self.body, text="Scheduler URL", text_color=MUTED).pack(anchor="w")
        self.sched_entry = ctk.CTkEntry(self.body, height=36)
        self.sched_entry.pack(fill="x", pady=(0, 8))
        default = self.settings.scheduler_url or be.get_default_scheduler_url()
        self.sched_entry.insert(0, default)
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkButton(row, text="Use Tailscale default", fg_color="#2A3544", command=self._use_ts).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(row, text="Use localhost", fg_color="#2A3544", command=self._use_local).pack(side="left")
        ctk.CTkButton(row, text="Test /status", fg_color=ACCENT, text_color="#0A1210", command=self._test_sched).pack(
            side="right"
        )
        self.connect_log = ctk.CTkTextbox(self.body, height=160, fg_color=PANEL)
        self.connect_log.pack(fill="x", pady=12)

    def _use_ts(self) -> None:
        self.sched_entry.delete(0, "end")
        self.sched_entry.insert(0, be.get_default_scheduler_url())

    def _use_local(self) -> None:
        self.sched_entry.delete(0, "end")
        self.sched_entry.insert(0, "http://127.0.0.1:8766")

    def _test_sched(self) -> None:
        url = self.sched_entry.get().strip()
        self.connect_log.delete("1.0", "end")
        self.connect_log.insert("1.0", f"Testing {url} …\n")

        def work() -> None:
            result = be.test_scheduler(url)
            self.after(0, lambda: self._test_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _test_done(self, result: dict[str, Any]) -> None:
        if result.get("ok"):
            data = result.get("data") or {}
            self.connect_log.insert(
                "end",
                f"OK — {result.get('url')}\n"
                f"Workers online: {data.get('workers_online')}  "
                f"Free VRAM: {data.get('free_vram_mb')} MiB\n",
            )
        else:
            self.connect_log.insert("end", f"FAILED — {result.get('error')}\n")
            for a in result.get("attempts") or []:
                self.connect_log.insert("end", f"  tried {a.get('url')}: {'ok' if a.get('ok') else a.get('error')}\n")

    def _step_caps(self) -> None:
        self._title(
            "Resource dedication",
            "Soft caps for what this machine contributes. 0 VRAM/RAM/Disk = no extra soft cap.",
        )
        gpus = be.get_gpus()
        host = be.detect_host_resources()
        total_vram = max(sum(int(g.get("memory_total_mb") or 0) for g in gpus), 1024)
        total_ram = max(int(host.get("total_ram_mb") or 0), 1024)
        total_disk = max(float(host.get("total_disk_gb") or 0), 10.0)

        self.vram_var = ctk.IntVar(value=int(self.settings.max_vram_mb or 0))
        self.cpu_var = ctk.DoubleVar(value=float(self.settings.max_cpu_percent or 50))
        self.ram_var = ctk.IntVar(value=int(self.settings.max_ram_mb or 0))
        self.disk_var = ctk.DoubleVar(value=float(self.settings.max_disk_gb or 0))

        self._slider_row(self.body, "Max VRAM (MiB)", self.vram_var, 0, total_vram, f"Detected total {total_vram} MiB")
        self._slider_row(self.body, "Max CPU (%)", self.cpu_var, 5, 100, "Soft advertise cap")
        self._slider_row(self.body, "Max RAM (MiB)", self.ram_var, 0, total_ram, f"Host total {total_ram} MiB")
        self._slider_row(self.body, "Max Disk (GiB)", self.disk_var, 0, total_disk, f"Host total {total_disk} GiB")

        vm = be.get_agent_vms_info(self.settings.agent_vms_path)
        note = ctk.CTkFrame(self.body, fg_color=PANEL, corner_radius=8)
        note.pack(fill="x", pady=12)
        ctk.CTkLabel(
            note,
            text="Advanced: agent-vms (optional) — Linux desktop workspaces, not GPU passthrough.",
            text_color=MUTED,
            wraplength=820,
            justify="left",
        ).pack(anchor="w", padx=12, pady=10)
        ctk.CTkLabel(
            note,
            text=f"Detected: {'yes' if vm.get('ready') else 'no'} @ {vm.get('path')}",
            text_color=MUTED,
        ).pack(anchor="w", padx=12, pady=(0, 10))

    def _slider_row(
        self,
        parent: Any,
        label: str,
        variable: ctk.Variable,
        lo: float,
        hi: float,
        hint: str,
    ) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=6)
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=label).pack(side="left")
        val_lbl = ctk.CTkLabel(top, text=str(variable.get()), text_color=ACCENT)
        val_lbl.pack(side="right")

        def on_change(_v: str = "") -> None:
            raw = variable.get()
            if isinstance(raw, float) and not isinstance(variable, ctk.IntVar):
                val_lbl.configure(text=f"{raw:.0f}" if hi >= 20 else f"{raw:.1f}")
            else:
                val_lbl.configure(text=str(int(raw)))

        ctk.CTkSlider(frame, from_=lo, to=hi, variable=variable, command=on_change).pack(fill="x", pady=2)
        ctk.CTkLabel(frame, text=hint, text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w")
        on_change()

    def _persist_partial(self) -> None:
        if hasattr(self, "portal_entry"):
            self.settings.portal_url = self.portal_entry.get().strip() or self.settings.portal_url
        if hasattr(self, "name_entry"):
            self.settings.worker_name = self.name_entry.get().strip() or self.settings.worker_name
        if hasattr(self, "discord_entry"):
            self.settings.discord_user = self.discord_entry.get().strip()
        if hasattr(self, "sched_entry"):
            self.settings.scheduler_url = self.sched_entry.get().strip() or self.settings.scheduler_url
        if hasattr(self, "vram_var"):
            self.settings.max_vram_mb = int(self.vram_var.get())
            self.settings.max_cpu_percent = float(self.cpu_var.get())
            self.settings.max_ram_mb = int(self.ram_var.get())
            self.settings.max_disk_gb = float(self.disk_var.get())
        be.save_config(self.settings)

    def _back(self) -> None:
        self._persist_partial()
        if self.step > 0:
            self.step -= 1
            self._render_step()

    def _next(self) -> None:
        self._persist_partial()
        if self.step < len(self.STEPS) - 1:
            self.step += 1
            self._render_step()
            return
        self.settings.wizard_completed = True
        be.save_config(self.settings)
        self.on_done()


# =============================================================================
# Main control panel
# =============================================================================


class MainFrame(ctk.CTkFrame):
    def __init__(self, master: Any, app: GpuPoolApp) -> None:
        super().__init__(master, fg_color=BG)
        self.app = app
        self.settings = be.load_config()
        # Prefer Tailscale portal URL for sharing / Twitch demos
        if "127.0.0.1" in (self.settings.portal_url or ""):
            self.settings.portal_url = "http://100.85.165.84:8767/portal"
            be.save_config(self.settings)
        self._build()
        self._refresh_gpus()
        self._refresh_host()
        self._schedule_poll()

    def _build(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=20, pady=12)
        ctk.CTkLabel(
            left,
            text=APP_TITLE,
            font=ctk.CTkFont(family="Segoe UI Semibold", size=24),
            text_color=ACCENT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            left,
            text="Power-user native joiner  ·  easiest remote path is the web portal",
            text_color=MUTED,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w")

        btns = ctk.CTkFrame(header, fg_color="transparent")
        btns.pack(side="right", padx=16)
        ctk.CTkButton(
            btns,
            text="Open web portal",
            width=150,
            fg_color=ACCENT,
            text_color="#0A1210",
            command=self._open_portal,
        ).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Re-run wizard", width=120, fg_color="#2A3544", command=self._rerun_wizard).pack(
            side="left", padx=6
        )

        # Portal banner
        portal_bar = ctk.CTkFrame(self, fg_color="#13261F", corner_radius=0)
        portal_bar.pack(fill="x")
        self.portal_entry = ctk.CTkEntry(portal_bar, height=32)
        self.portal_entry.pack(side="left", fill="x", expand=True, padx=(16, 8), pady=8)
        self.portal_entry.insert(0, be.get_portal_url(self.settings))
        ctk.CTkButton(portal_bar, text="Open", width=80, fg_color="#2A3544", command=self._open_portal).pack(
            side="right", padx=(0, 16), pady=8
        )

        # Body grid
        body = ctk.CTkFrame(self, fg_color=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        left_col = ctk.CTkFrame(body, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right_col = ctk.CTkFrame(body, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._build_identity(left_col)
        self._build_gpus(left_col)
        self._build_caps(left_col)
        self._build_actions(left_col)
        self._build_status(right_col)
        self._build_discord(right_col)

    def _card(self, parent: Any, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=10)
        card.pack(fill="x", pady=6)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT).pack(
            anchor="w", padx=14, pady=(12, 6)
        )
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=(0, 12))
        return inner

    def _build_identity(self, parent: Any) -> None:
        inner = self._card(parent, "Connection & identity")
        ctk.CTkLabel(inner, text="Scheduler URL", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.sched_entry = ctk.CTkEntry(inner, height=32)
        self.sched_entry.pack(fill="x", pady=(0, 6))
        self.sched_entry.insert(0, self.settings.scheduler_url)
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=(0, 6))
        ctk.CTkButton(row, text="Test", width=70, fg_color="#2A3544", command=self._test_scheduler).pack(side="left")
        self.test_lbl = ctk.CTkLabel(row, text="", text_color=MUTED)
        self.test_lbl.pack(side="left", padx=10)
        grid = ctk.CTkFrame(inner, fg_color="transparent")
        grid.pack(fill="x")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(grid, text="Worker name", text_color=MUTED, font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(grid, text="Discord user", text_color=MUTED, font=ctk.CTkFont(size=11)).grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        self.name_entry = ctk.CTkEntry(grid, height=32)
        self.name_entry.grid(row=1, column=0, sticky="ew", pady=2)
        self.name_entry.insert(0, self.settings.worker_name)
        self.discord_entry = ctk.CTkEntry(grid, height=32)
        self.discord_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=2)
        self.discord_entry.insert(0, self.settings.discord_user or "")

    def _build_gpus(self, parent: Any) -> None:
        inner = self._card(parent, "Detected GPUs (nvidia-smi)")
        self.gpu_box = ctk.CTkTextbox(inner, height=100, fg_color="#121A24")
        self.gpu_box.pack(fill="x")
        self.host_lbl = ctk.CTkLabel(inner, text="", text_color=MUTED, font=ctk.CTkFont(size=11))
        self.host_lbl.pack(anchor="w", pady=(6, 0))

    def _build_caps(self, parent: Any) -> None:
        inner = self._card(parent, "Dedication — VRAM · CPU · RAM · Disk")
        gpus = be.get_gpus()
        host = be.detect_host_resources()
        total_vram = max(sum(int(g.get("memory_total_mb") or 0) for g in gpus), 1024)
        total_ram = max(int(host.get("total_ram_mb") or 0), 1024)
        total_disk = max(float(host.get("total_disk_gb") or 0), 10.0)

        self.vram_var = ctk.IntVar(value=int(self.settings.max_vram_mb or 0))
        self.cpu_var = ctk.DoubleVar(value=float(self.settings.max_cpu_percent or 50))
        self.ram_var = ctk.IntVar(value=int(self.settings.max_ram_mb or 0))
        self.disk_var = ctk.DoubleVar(value=float(self.settings.max_disk_gb or 0))

        self._cap_slider(inner, "Max VRAM MiB", self.vram_var, 0, total_vram)
        self._cap_slider(inner, "Max CPU %", self.cpu_var, 5, 100)
        self._cap_slider(inner, "Max RAM MiB", self.ram_var, 0, total_ram)
        self._cap_slider(inner, "Max Disk GiB", self.disk_var, 0, total_disk)
        ctk.CTkButton(inner, text="Save caps & identity", fg_color="#2A3544", command=self._save_settings).pack(
            anchor="e", pady=(8, 0)
        )

    def _cap_slider(self, parent: Any, label: str, variable: ctk.Variable, lo: float, hi: float) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=label, font=ctk.CTkFont(size=12)).pack(side="left")
        val = ctk.CTkLabel(top, text="", text_color=ACCENT, font=ctk.CTkFont(size=12))
        val.pack(side="right")

        def upd(_v: str = "") -> None:
            v = variable.get()
            val.configure(text=f"{int(v)}" if abs(hi - lo) >= 20 else f"{float(v):.1f}")

        ctk.CTkSlider(row, from_=lo, to=hi, variable=variable, command=upd, height=16).pack(fill="x")
        upd()

    def _build_actions(self, parent: Any) -> None:
        inner = self._card(parent, "Pool control")
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")
        self.join_btn = ctk.CTkButton(
            row,
            text="Join pool",
            height=40,
            fg_color=ACCENT,
            text_color="#0A1210",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._join,
        )
        self.join_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.leave_btn = ctk.CTkButton(
            row,
            text="Leave pool",
            height=40,
            fg_color=DANGER,
            command=self._leave,
        )
        self.leave_btn.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.action_lbl = ctk.CTkLabel(inner, text="", text_color=MUTED)
        self.action_lbl.pack(anchor="w", pady=(8, 0))

    def _build_status(self, parent: Any) -> None:
        inner = self._card(parent, "Status")
        self.status_box = ctk.CTkTextbox(inner, height=220, fg_color="#121A24")
        self.status_box.pack(fill="both", expand=True)
        ctk.CTkButton(inner, text="Refresh now", fg_color="#2A3544", command=self._poll_status).pack(
            anchor="e", pady=(8, 0)
        )

    def _build_discord(self, parent: Any) -> None:
        inner = self._card(parent, "Discord helper (Glitch Factor)")
        box = ctk.CTkTextbox(inner, height=180, fg_color="#121A24")
        box.pack(fill="x")
        box.insert("1.0", be.get_discord_helper_text())
        box.configure(state="disabled")
        ctk.CTkButton(
            inner,
            text="Copy commands",
            fg_color="#2A3544",
            command=lambda: self._copy(be.get_discord_helper_text()),
        ).pack(anchor="e", pady=(8, 0))

    # --- actions ---------------------------------------------------------------

    def _collect(self) -> be.JoinerSettings:
        s = be.load_config()
        s.scheduler_url = self.sched_entry.get().strip() or s.scheduler_url
        s.worker_name = self.name_entry.get().strip() or s.worker_name
        s.discord_user = self.discord_entry.get().strip()
        s.portal_url = self.portal_entry.get().strip() or s.portal_url
        s.max_vram_mb = int(self.vram_var.get())
        s.max_cpu_percent = float(self.cpu_var.get())
        s.max_ram_mb = int(self.ram_var.get())
        s.max_disk_gb = float(self.disk_var.get())
        return s

    def _save_settings(self) -> None:
        self.settings = self._collect()
        be.save_config(self.settings)
        self.action_lbl.configure(text="Saved.", text_color=OK_GREEN)

    def _open_portal(self) -> None:
        url = self.portal_entry.get().strip()
        if url:
            s = self._collect()
            s.portal_url = url
            be.save_config(s)
        result = be.open_portal_url(url or None)
        self.action_lbl.configure(
            text=result.get("message") or "",
            text_color=OK_GREEN if result.get("ok") else WARN,
        )

    def _rerun_wizard(self) -> None:
        s = be.load_config()
        s.wizard_completed = False
        be.save_config(s)
        self.app._show_wizard()

    def _test_scheduler(self) -> None:
        url = self.sched_entry.get().strip()
        self.test_lbl.configure(text="Testing…", text_color=MUTED)

        def work() -> None:
            result = be.test_scheduler(url)
            self.after(
                0,
                lambda: self.test_lbl.configure(
                    text="Connected" if result.get("ok") else "Unreachable",
                    text_color=OK_GREEN if result.get("ok") else DANGER,
                ),
            )

        threading.Thread(target=work, daemon=True).start()

    def _join(self) -> None:
        if self.app._busy:
            return
        self.app._busy = True
        self.action_lbl.configure(text="Starting worker…", text_color=MUTED)
        settings = self._collect()
        be.save_config(settings)

        def work() -> None:
            result = be.start_worker(settings)
            self.after(0, lambda: self._join_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _join_done(self, result: dict[str, Any]) -> None:
        self.app._busy = False
        ok = bool(result.get("ok"))
        self.action_lbl.configure(
            text=result.get("message") or ("Joined" if ok else "Failed"),
            text_color=OK_GREEN if ok else DANGER,
        )
        self._poll_status()

    def _leave(self) -> None:
        if self.app._busy:
            return
        self.app._busy = True
        self.action_lbl.configure(text="Stopping worker…", text_color=MUTED)

        def work() -> None:
            result = be.stop_worker()
            self.after(0, lambda: self._leave_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _leave_done(self, result: dict[str, Any]) -> None:
        self.app._busy = False
        self.action_lbl.configure(
            text=result.get("message") or "Left pool",
            text_color=OK_GREEN if result.get("ok") else DANGER,
        )
        self._poll_status()

    def _copy(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)
        self.action_lbl.configure(text="Copied Discord helper text.", text_color=OK_GREEN)

    def _refresh_gpus(self) -> None:
        gpus = be.get_gpus()
        total = sum(int(g.get("memory_total_mb") or 0) for g in gpus)
        free = sum(int(g.get("memory_free_mb") or 0) for g in gpus)
        lines = [
            f"{len(gpus)} GPU(s)  ·  total {total} MiB  ·  free {free} MiB",
            "",
        ]
        for g in gpus:
            lines.append(
                f"[{g.get('index')}] {g.get('name')}  "
                f"{g.get('memory_free_mb')}/{g.get('memory_total_mb')} MiB free  "
                f"util {g.get('utilization_gpu_pct')}%"
            )
        if not gpus:
            lines.append("No GPUs detected — install NVIDIA drivers / check nvidia-smi.")
        self.gpu_box.delete("1.0", "end")
        self.gpu_box.insert("1.0", "\n".join(lines))

    def _refresh_host(self) -> None:
        host = be.detect_host_resources()
        self.host_lbl.configure(
            text=(
                f"Host RAM {host.get('avail_ram_mb', 0)}/{host.get('total_ram_mb', 0)} MiB avail  ·  "
                f"Disk {host.get('free_disk_gb', 0)}/{host.get('total_disk_gb', 0)} GiB free"
            )
        )

    def _poll_status(self) -> None:
        def work() -> None:
            status = be.get_status()
            self.after(0, lambda: self._render_status(status))

        threading.Thread(target=work, daemon=True).start()

    def _render_status(self, status: dict[str, Any]) -> None:
        w = status.get("worker") or {}
        sch = status.get("scheduler") or {}
        ts = status.get("tailscale_ipv4") or "n/a"
        lines = [
            f"Local worker: {'RUNNING' if w.get('running') else 'stopped'}"
            + (f"  pid={w.get('pid')}" if w.get("pid") else ""),
            f"Connected: {'yes' if w.get('connected') else 'no'}  ·  {w.get('detail') or ''}",
            f"Worker id:   {w.get('worker_id') or '—'}",
            f"Worker name: {w.get('worker_name') or '—'}",
            f"Last heartbeat: {w.get('last_heartbeat') or '—'}",
            f"GPUs advertised: {', '.join(w.get('gpus_advertised') or []) or '—'}",
            f"VRAM free/total (worker view): {w.get('free_vram_mb', 0)} / {w.get('total_vram_mb', 0)} MiB",
            "",
            f"Scheduler: {'OK' if sch.get('ok') else 'DOWN'}  {sch.get('url') or ''}",
        ]
        if sch.get("error"):
            lines.append(f"  error: {sch['error']}")
        data = sch.get("data") or {}
        if data:
            lines.append(
                f"  pool workers online: {data.get('workers_online')} / {data.get('workers_total')}  "
                f"jobs q/r/c: {((data.get('jobs') or {}).get('queued'))}/"
                f"{((data.get('jobs') or {}).get('running'))}/"
                f"{((data.get('jobs') or {}).get('completed'))}"
            )
        lines += ["", f"Tailscale IPv4: {ts}", f"Updated: {time.strftime('%H:%M:%S')}"]
        self.status_box.delete("1.0", "end")
        self.status_box.insert("1.0", "\n".join(lines))

        # Button enablement
        running = bool(w.get("running"))
        self.join_btn.configure(state="disabled" if running else "normal")
        self.leave_btn.configure(state="normal" if running else "disabled")

    def _schedule_poll(self) -> None:
        self._poll_status()

        def tick() -> None:
            self._poll_status()
            self.app._poll_after = self.after(4000, tick)

        self.app._poll_after = self.after(4000, tick)


if __name__ == "__main__":
    raise SystemExit(run_app())

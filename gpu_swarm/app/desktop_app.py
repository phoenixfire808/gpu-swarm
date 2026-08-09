"""
GPU Pool desktop joiner — customtkinter UI.

One-stop setup wizard + main Join/Leave control.
Calls only gpu_swarm.app_backend stable APIs (no mocks).
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Any, Callable

import customtkinter as ctk

from gpu_swarm import app_backend as be
from gpu_swarm.availability_schedule import PRESET_LABELS, apply_preset, config_to_settings_fields
from gpu_swarm.joiner_settings import (
    DEFAULT_LOCAL_PORTAL_URL,
    DEFAULT_LOCAL_SCHEDULER_URL,
    DEFAULT_PORTAL_URL,
    DEFAULT_SCHEDULER_URL,
    PORTAL_INVITE_CODE,
)
from gpu_swarm.use_cases import USE_CASES

APP_TITLE = "GPU Pool"
ACCENT = "#2DD4A8"
WARN = "#F0B429"
MUTED = "#9AA4B2"
BG = "#0F1419"
PANEL = "#1A2332"
DANGER = "#E85D5D"
OK_GREEN = "#3DDC97"


def _apply_availability_fields(
    settings: be.JoinerSettings,
    preset: str,
    *,
    daily_start: str = "",
    daily_end: str = "",
) -> None:
    from gpu_swarm.availability_schedule import AvailabilityConfig

    key = (preset or "always").strip().lower()
    settings.availability_preset = key
    if key == "custom":
        cfg = AvailabilityConfig(
            mode="daily",
            daily_start=daily_start or "22:00",
            daily_end=daily_end or "08:00",
        )
    else:
        cfg = apply_preset(key)
    for field, val in config_to_settings_fields(cfg).items():
        setattr(settings, field, val)


def run_app() -> int:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = GpuPoolApp()
    app.mainloop()
    return 0


class GpuPoolApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} — Network Hub")
        self.geometry("1120x820")
        self.minsize(960, 720)
        self.configure(fg_color=BG)

        self.settings = be.load_config()
        self._poll_after: str | None = None
        self._busy = False
        self._ui_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._ui_drain_after: str | None = None

        self._container = ctk.CTkFrame(self, fg_color=BG)
        self._container.pack(fill="both", expand=True)

        if not self.settings.wizard_completed:
            self._show_wizard()
        else:
            self._show_main()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._ensure_ui_drain()

    def post_ui(self, fn: Callable[[], None]) -> None:
        """Run *fn* on the Tk main thread (safe from worker threads)."""
        if threading.current_thread() is threading.main_thread():
            if not self.winfo_exists():
                return
            try:
                fn()
            except Exception:  # noqa: BLE001
                pass
            return
        self._ui_queue.put(fn)
        self._ensure_ui_drain()

    def _ensure_ui_drain(self) -> None:
        if self._ui_drain_after is not None:
            return
        try:
            if self.winfo_exists():
                self._ui_drain_after = self.after(50, self._drain_ui_queue)
        except Exception:  # noqa: BLE001
            pass

    def _drain_ui_queue(self) -> None:
        self._ui_drain_after = None
        try:
            if not self.winfo_exists():
                return
        except Exception:  # noqa: BLE001
            return
        while True:
            try:
                fn = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception:  # noqa: BLE001
                pass
        try:
            if self.winfo_exists() and not self._ui_queue.empty():
                self._ensure_ui_drain()
        except Exception:  # noqa: BLE001
            pass

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
        if self._ui_drain_after:
            try:
                self.after_cancel(self._ui_drain_after)
            except Exception:  # noqa: BLE001
                pass
            self._ui_drain_after = None
        while True:
            try:
                self._ui_queue.get_nowait()
            except queue.Empty:
                break
        if self._poll_after:
            try:
                self.after_cancel(self._poll_after)
            except Exception:  # noqa: BLE001
                pass
        self.destroy()


# =============================================================================
# Setup wizard — one-stop installer / onboarding
# =============================================================================


class WizardFrame(ctk.CTkFrame):
    STEPS = (
        "Welcome",
        "Network & Workspace",
        "Python & Deps",
        "Hardware",
        "Identity",
        "Connect",
        "Caps",
        "Join",
    )

    def __init__(self, master: Any, app: GpuPoolApp, on_done: Callable[[], None]) -> None:
        super().__init__(master, fg_color=BG)
        self.app = app
        self.on_done = on_done
        self.step = 0
        self.settings = be.load_config()
        self._gpu_info: dict[str, Any] = {}
        self._host_info: dict[str, Any] = {}
        self._no_gpu = False
        self._join_busy = False
        self._prereq_busy = False
        self._deps_busy = False
        self._cloudflare_busy = False
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
            nav, text="Next", width=160, command=self._next, fg_color=ACCENT, text_color="#0A1210"
        )
        self.next_btn.pack(side="right", padx=24, pady=14)

    def _render_step(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        name = self.STEPS[self.step]
        self.step_label.configure(text=f"Step {self.step + 1} / {len(self.STEPS)} — {name}")
        self.back_btn.configure(state="normal" if self.step > 0 else "disabled")
        last = self.step == len(self.STEPS) - 1
        self.next_btn.configure(text="Open control panel" if last else "Next")
        if last:
            # Join step owns its primary action; Next just exits wizard after save.
            self.next_btn.configure(text="Done → control panel")

        {
            0: self._step_welcome,
            1: self._step_network_tools,
            2: self._step_deps,
            3: self._step_hardware,
            4: self._step_identity,
            5: self._step_connect,
            6: self._step_caps,
            7: self._step_join,
        }[self.step]()

    def _title(self, text: str, sub: str = "") -> None:
        ctk.CTkLabel(self.body, text=text, font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w")
        if sub:
            ctk.CTkLabel(self.body, text=sub, text_color=MUTED, wraplength=860, justify="left").pack(
                anchor="w", pady=(6, 14)
            )

    def _log_box(self, height: int = 160) -> ctk.CTkTextbox:
        box = ctk.CTkTextbox(self.body, height=height, fg_color=PANEL)
        box.pack(fill="both", expand=True, pady=8)
        return box

    def _append_log(self, box: ctk.CTkTextbox, text: str) -> None:
        box.insert("end", text if text.endswith("\n") else text + "\n")
        box.see("end")

    # --- steps ----------------------------------------------------------------

    def _step_welcome(self) -> None:
        self._title(
            "Welcome to GPU Pool",
            "Follow the numbered steps. We install what you need — progress stays in this window.",
        )
        steps = ctk.CTkFrame(self.body, fg_color=PANEL, corner_radius=10)
        steps.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            steps,
            text="Just do this",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            steps,
            text=(
                "1. Click Next — we check your PC and install anything missing\n"
                "2. Enter invite glitch-factor + your Discord name\n"
                "3. Pick a big button: Share my PC · Use the pool · Invite friends\n\n"
                "What is GPU Pool?\n"
                "A private club for friends — share spare computer power, run jobs together, "
                "and invite more friends so everyone gets more speed. Not a public store."
            ),
            text_color=MUTED,
            justify="left",
            wraplength=820,
        ).pack(anchor="w", padx=16, pady=(0, 14))

        tools = ctk.CTkFrame(self.body, fg_color=PANEL, corner_radius=10)
        tools.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            tools,
            text="What we may install (plain English)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            tools,
            text=(
                "• Tailscale — a private network so friends can connect safely (optional if you have a web link)\n"
                "• Python + small helpers — runs this app and talks to the pool\n"
                "• VirtualBox + Vagrant — only if you want an optional Linux desktop (most people skip this)\n\n"
                "Already installed? We skip it. Windows may ask Yes once (normal)."
            ),
            text_color=MUTED,
            justify="left",
            wraplength=820,
        ).pack(anchor="w", padx=16, pady=(0, 14))

        uses = ctk.CTkFrame(self.body, fg_color=PANEL, corner_radius=10)
        uses.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            uses,
            text="What can you use this for?",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=16, pady=(14, 4))
        bullet = "\n".join(f"• {u['title']} — {u['body']}" for u in USE_CASES)
        ctk.CTkLabel(
            uses,
            text=bullet,
            text_color=MUTED,
            justify="left",
            wraplength=820,
        ).pack(anchor="w", padx=16, pady=(0, 14))

        hints = be.get_portal_hints()
        banner = ctk.CTkFrame(self.body, fg_color=PANEL, corner_radius=10)
        banner.pack(fill="x", pady=8)
        ctk.CTkLabel(
            banner,
            text="Easiest remote path: the browser portal",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            banner,
            text=(
                f"Live portal: {hints.get('url')}\n"
                f"Local: {hints.get('local_url')}   ·   Tailscale: {hints.get('tailscale_url')}\n"
                f"Invite code: {PORTAL_INVITE_CODE}  (pool password only if a pool admin shared it — never posted publicly)"
            ),
            text_color=MUTED,
            justify="left",
            wraplength=820,
        ).pack(anchor="w", padx=16, pady=(0, 8))
        reach = "reachable" if hints.get("reachable") else "not reachable yet — ask the host for the current public link, or start-portal.cmd on the host"
        ctk.CTkLabel(
            banner,
            text=f"Portal status: {reach}",
            text_color=OK_GREEN if hints.get("reachable") else WARN,
        ).pack(anchor="w", padx=16, pady=(0, 14))

        # Prefer live resolved URL in the entry
        portal = hints.get("url") or DEFAULT_LOCAL_PORTAL_URL
        self.settings.portal_url = portal

        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", pady=8)
        ctk.CTkButton(
            row,
            text="Open portal",
            width=140,
            fg_color=ACCENT,
            text_color="#0A1210",
            command=self._open_portal_wizard,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Use local portal",
            width=140,
            fg_color="#2A3544",
            command=lambda: self._set_portal(DEFAULT_LOCAL_PORTAL_URL),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Use Tailscale portal",
            width=160,
            fg_color="#2A3544",
            command=lambda: self._set_portal(DEFAULT_PORTAL_URL),
        ).pack(side="left")

        ctk.CTkLabel(self.body, text="Portal URL (editable)", text_color=MUTED).pack(anchor="w", pady=(8, 2))
        self.portal_entry = ctk.CTkEntry(self.body, height=36)
        self.portal_entry.pack(fill="x")
        self.portal_entry.insert(0, portal)

        py = be.check_python()
        py_frame = ctk.CTkFrame(self.body, fg_color=PANEL, corner_radius=8)
        py_frame.pack(fill="x", pady=14)
        ctk.CTkLabel(
            py_frame,
            text=f"Python: {'OK' if py.get('ok') else 'NEEDS FIX'} — {py.get('message')}",
            text_color=OK_GREEN if py.get("ok") else DANGER,
            wraplength=820,
            justify="left",
        ).pack(anchor="w", padx=14, pady=12)
        if py.get("fix"):
            ctk.CTkLabel(
                py_frame,
                text=f"Fix: {py['fix']}",
                text_color=WARN,
                wraplength=820,
                justify="left",
            ).pack(anchor="w", padx=14, pady=(0, 12))

    def _step_network_tools(self) -> None:
        self._title(
            "Step 2 — Network tools",
            "We only install what is missing. Most friends use a web link from the host and skip Tailscale.",
        )
        try:
            from gpu_swarm.diagnostics import set_wizard_step

            set_wizard_step("Network & Workspace")
        except Exception:  # noqa: BLE001
            pass

        why = ctk.CTkFrame(self.body, fg_color=PANEL, corner_radius=10)
        why.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            why,
            text=(
                "Nothing is required for the public portal path.\n"
                "• Tailscale — optional private-network fallback\n"
                "• VirtualBox + Vagrant — optional Workspace only (large install; never automatic)\n"
                "The normal friend path skips all three and opens the portal."
            ),
            text_color=MUTED,
            justify="left",
            wraplength=820,
        ).pack(anchor="w", padx=16, pady=14)

        self.prereq_status_lbl = ctk.CTkLabel(
            self.body,
            text="Click Detect to scan this PC…",
            text_color=MUTED,
            wraplength=860,
            justify="left",
        )
        self.prereq_status_lbl.pack(anchor="w", pady=(4, 2))
        self.prereq_progress = ctk.CTkProgressBar(self.body, height=14, progress_color=ACCENT)
        self.prereq_progress.pack(fill="x", pady=(0, 6))
        self.prereq_progress.set(0)
        self.prereq_log = self._log_box(200)
        self._append_log(
            self.prereq_log,
            "Ready. Detect = scan only. Install & connect = install missing tools + open Tailscale login if needed.\n"
            "Share-only shortcut: Install Tailscale only (skips VirtualBox/Vagrant).\n",
        )

        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkButton(
            row,
            text="Check my PC",
            width=170,
            fg_color="#2A3544",
            command=lambda: self._run_prereqs(detect_only=True),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Install optional Tailscale",
            width=190,
            fg_color=ACCENT,
            text_color="#0A1210",
            command=lambda: self._run_prereqs(
                detect_only=False,
                connect_tailscale=True,
                skip_virtualbox=True,
                skip_vagrant=True,
            ),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Workspace tools (optional)",
            width=210,
            fg_color="#2A3544",
            command=lambda: self._run_prereqs(
                detect_only=False,
                workspace_tools=True,
                skip_tailscale=True,
            ),
        ).pack(side="left")

        self.after(200, lambda: self._run_prereqs(detect_only=True))

        cloud = ctk.CTkFrame(self.body, fg_color="#13261F", corner_radius=10)
        cloud.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(
            cloud,
            text="Public access with Cloudflare (optional)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=16, pady=(12, 4))
        ctk.CTkLabel(
            cloud,
            text=(
                "Make this PC's GPU Pool portal available over HTTPS. Quick link = one click, no account, "
                "temporary URL. Stable hostname = your Cloudflare account/domain. Credentials stay on this PC. "
                "Only the portal is published; scheduler access remains behind /pool-api."
            ),
            text_color=MUTED,
            wraplength=820,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 8))
        self.cloudflare_status_lbl = ctk.CTkLabel(cloud, text="Checking Cloudflare helper…", text_color=MUTED, wraplength=820, justify="left")
        self.cloudflare_status_lbl.pack(anchor="w", padx=16, pady=(0, 4))
        named_fields = ctk.CTkFrame(cloud, fg_color="transparent")
        named_fields.pack(fill="x", padx=16, pady=(0, 8))
        self.cloudflare_hostname_entry = ctk.CTkEntry(named_fields, placeholder_text="Stable hostname, e.g. gpu-pool.example.com")
        self.cloudflare_hostname_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.cloudflare_tunnel_name_entry = ctk.CTkEntry(named_fields, width=170, placeholder_text="Tunnel name")
        self.cloudflare_tunnel_name_entry.pack(side="left")
        self.cloudflare_tunnel_name_entry.insert(0, "gpu-pool")
        self.cloudflare_log = ctk.CTkTextbox(cloud, height=118, fg_color=PANEL)
        self.cloudflare_log.pack(fill="x", padx=16, pady=(0, 8))
        self._append_log(self.cloudflare_log, "Cloudflare is optional. Install the helper, then publish a temporary link when the local portal is ready.\n")
        cloud_row = ctk.CTkFrame(cloud, fg_color="transparent")
        cloud_row.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkButton(
            cloud_row,
            text="Install Cloudflare helper",
            width=190,
            fg_color="#2A3544",
            command=lambda: self._run_cloudflare("install"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            cloud_row,
            text="Publish temporary HTTPS link",
            width=215,
            fg_color=ACCENT,
            text_color="#0A1210",
            command=lambda: self._run_cloudflare("quick"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            cloud_row,
            text="Stable hostname guide",
            width=170,
            fg_color="#2A3544",
            command=self._open_cloudflare_guide,
        ).pack(side="left")
        named_row = ctk.CTkFrame(cloud, fg_color="transparent")
        named_row.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkButton(
            named_row,
            text="Create & launch named tunnel",
            width=250,
            fg_color=ACCENT,
            text_color="#0A1210",
            command=lambda: self._run_cloudflare("named_setup"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            named_row,
            text="Refresh Cloudflare status",
            width=190,
            fg_color="#2A3544",
            command=self._refresh_cloudflare_status,
        ).pack(side="left")
        self.after(250, self._refresh_cloudflare_status)

    def _run_prereqs(
        self,
        *,
        detect_only: bool,
        connect_tailscale: bool = False,
        skip_virtualbox: bool = False,
        skip_vagrant: bool = False,
        workspace_tools: bool = False,
    ) -> None:
        if self._prereq_busy:
            return
        if not hasattr(self, "prereq_log"):
            return
        self._prereq_busy = True
        self.prereq_log.delete("1.0", "end")
        if hasattr(self, "prereq_progress"):
            self.prereq_progress.set(0.05)
        mode = "Detecting" if detect_only else "Installing / connecting"
        self._append_log(self.prereq_log, f"{mode}… (already-installed tools are skipped)\n\n")
        if hasattr(self, "prereq_status_lbl"):
            self.prereq_status_lbl.configure(text=f"{mode}…", text_color=ACCENT)

        def work() -> None:
            try:
                result = be.install_prereqs(
                    detect_only=detect_only,
                    connect_tailscale=connect_tailscale,
                    skip_virtualbox=skip_virtualbox,
                    skip_vagrant=skip_vagrant,
                    workspace_tools=workspace_tools,
                )
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "message": f"Prerequisite check error: {exc}", "warnings": ["Use the public portal path and skip optional tools."]}
            self.app.post_ui(lambda: self._prereqs_done(result, detect_only=detect_only))

        threading.Thread(target=work, daemon=True).start()

    def _prereqs_done(self, result: dict[str, Any], *, detect_only: bool) -> None:
        self._prereq_busy = False
        if hasattr(self, "prereq_progress"):
            self.prereq_progress.set(1.0 if result.get("ok") else 0.4)
        log_text = result.get("log_text") or ""
        if log_text:
            self._append_log(self.prereq_log, log_text + "\n")
        for key in ("tailscale", "virtualbox", "vagrant"):
            block = result.get(key) or {}
            if isinstance(block, dict) and block.get("message"):
                self._append_log(self.prereq_log, f"{key}: {block.get('message')}\n")
        warns = result.get("warnings") or []
        for w in warns:
            self._append_log(self.prereq_log, f"WARN: {w}\n")
        next_steps = result.get("next_steps") or []
        if next_steps:
            self._append_log(self.prereq_log, "\nNext:\n")
            for s in next_steps:
                self._append_log(self.prereq_log, f"  • {s}\n")
        ts = result.get("tailscale") or {}
        ws_ok = bool(result.get("workspace_tools_ready"))
        parts = []
        if ts.get("logged_in"):
            parts.append(f"Tailscale on ({ts.get('ipv4') or 'ok'})")
        elif ts.get("installed"):
            parts.append("Tailscale installed — finish browser login if prompted")
        elif ts.get("skipped"):
            parts.append("Tailscale skipped")
        else:
            parts.append("Tailscale missing — use public portal or Install")
        parts.append("Workspace tools OK" if ws_ok else "Workspace optional / incomplete")
        summary = " · ".join(parts)
        if hasattr(self, "prereq_status_lbl"):
            self.prereq_status_lbl.configure(
                text=summary,
                text_color=OK_GREEN if (ts.get("logged_in") or detect_only) else WARN,
            )
        self._append_log(self.prereq_log, f"\n{summary}\n")

    def _cloudflare_done(self, result: dict[str, Any], action: str) -> None:
        self._cloudflare_busy = False
        log_text = result.get("log_text") or ""
        if log_text:
            self._append_log(self.cloudflare_log, str(log_text)[-4000:] + "\n")
        if result.get("ok"):
            if result.get("setup_started"):
                self._append_log(self.cloudflare_log, f"SETUP — {result.get('message') or 'Cloudflare setup window opened.'}\n")
                if hasattr(self, "cloudflare_status_lbl"):
                    self.cloudflare_status_lbl.configure(
                        text="Cloudflare setup window opened — finish login/setup there, then refresh status.",
                        text_color=ACCENT,
                    )
                self.after(3000, self._refresh_cloudflare_status)
                return
            portal = result.get("portal_path") or ""
            self._append_log(self.cloudflare_log, f"OK — {result.get('message') or 'Cloudflare ready'}\n")
            if portal:
                self.settings.portal_url = str(portal)
                be.save_config(self.settings)
                self._append_log(self.cloudflare_log, f"Portal: {portal}\n")
            if hasattr(self, "cloudflare_status_lbl"):
                self.cloudflare_status_lbl.configure(
                    text=f"Cloudflare ON — {portal or result.get('path') or 'helper ready'}",
                    text_color=OK_GREEN,
                )
        else:
            self._append_log(self.cloudflare_log, f"FAILED — {result.get('message') or result.get('error') or 'Cloudflare action failed'}\n")
            if hasattr(self, "cloudflare_status_lbl"):
                self.cloudflare_status_lbl.configure(text="Cloudflare action needs attention — see the log.", text_color=WARN)
        self._refresh_cloudflare_status()

    def _run_cloudflare(self, action: str) -> None:
        if self._cloudflare_busy or not hasattr(self, "cloudflare_log"):
            return
        hostname = ""
        tunnel_name = "gpu-pool"
        if action == "named_setup":
            hostname = self.cloudflare_hostname_entry.get().strip() if hasattr(self, "cloudflare_hostname_entry") else ""
            tunnel_name = self.cloudflare_tunnel_name_entry.get().strip() if hasattr(self, "cloudflare_tunnel_name_entry") else "gpu-pool"
            if not hostname:
                self.cloudflare_status_lbl.configure(text="Enter a Cloudflare-managed hostname before setup.", text_color=WARN)
                self._append_log(self.cloudflare_log, "Named setup blocked: enter a hostname such as gpu-pool.example.com.\n")
                return
        self._cloudflare_busy = True
        self.cloudflare_log.delete("1.0", "end")
        if action == "install":
            label = "Installing Cloudflare helper"
        elif action == "named_setup":
            label = "Opening named Cloudflare tunnel setup"
        else:
            label = "Starting temporary HTTPS link"
        self._append_log(self.cloudflare_log, f"{label}…\n\n")
        if hasattr(self, "cloudflare_status_lbl"):
            self.cloudflare_status_lbl.configure(text=f"{label}…", text_color=ACCENT)

        def work() -> None:
            try:
                if action == "install":
                    result = be.install_cloudflared()
                elif action == "named_setup":
                    result = be.launch_cloudflare_named_setup(
                        hostname=hostname,
                        tunnel_name=tunnel_name,
                        launch=True,
                    )
                else:
                    result = be.publish_cloudflare(mode="quick", open_browser=True)
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "message": f"Cloudflare action error: {exc}"}
            self.app.post_ui(lambda: self._cloudflare_done(result, action))

        threading.Thread(target=work, daemon=True).start()

    def _refresh_cloudflare_status(self) -> None:
        if not hasattr(self, "cloudflare_status_lbl") or self._cloudflare_busy:
            return
        try:
            status = be.cloudflare_status()
            if status.get("public_active"):
                text = f"Cloudflare ON ({status.get('mode')}) — {status.get('portal_path')}"
                color = OK_GREEN
            elif status.get("named_config_present"):
                text = "Named tunnel config found — enter the hostname above and create/launch it."
                color = OK_GREEN
            elif status.get("tool_installed"):
                text = "Cloudflare helper installed — publish a temporary link or create a named tunnel above."
                color = OK_GREEN
            else:
                text = "Cloudflare helper not installed yet — optional; public access needs a running local portal."
                color = MUTED
            self.cloudflare_status_lbl.configure(text=text, text_color=color)
        except Exception as exc:  # noqa: BLE001
            self.cloudflare_status_lbl.configure(text=f"Cloudflare status unavailable: {exc}", text_color=WARN)

    def _open_cloudflare_guide(self) -> None:
        result = be.open_cloudflare_guide()
        if hasattr(self, "cloudflare_log"):
            if result.get("ok"):
                self._append_log(self.cloudflare_log, f"Opened stable hostname guide: {result.get('path')}\n")
            else:
                self._append_log(self.cloudflare_log, f"Guide: {result.get('message') or result.get('path')}\n")

    def _set_portal(self, url: str) -> None:
        if hasattr(self, "portal_entry"):
            self.portal_entry.delete(0, "end")
            self.portal_entry.insert(0, url)

    def _open_portal_wizard(self) -> None:
        url = self.portal_entry.get().strip() if hasattr(self, "portal_entry") else ""
        if not url:
            url = be.resolve_portal_url().get("url") or DEFAULT_LOCAL_PORTAL_URL
        result = be.open_portal_url(url)
        # Surface result in a transient label if present
        msg = result.get("message") or ""
        if hasattr(self, "portal_entry"):
            # keep entry synced to what we opened
            opened = result.get("url") or url
            self.portal_entry.delete(0, "end")
            self.portal_entry.insert(0, opened)
        self.settings.portal_url = (result.get("url") or url).strip()
        be.save_config(self.settings)

    def _step_deps(self) -> None:
        self._title(
            "Python & dependencies",
            "We install a private Python under %LOCALAPPDATA%\\GPUPool\\ (not your system Python). "
            "Watch the log below for steps like “Downloading Python runtime…” and package names. "
            "CUDA PyTorch is optional — only if you want GPU compute jobs on this PC.",
        )
        try:
            from gpu_swarm.diagnostics import set_wizard_step

            set_wizard_step("Python & Deps")
        except Exception:  # noqa: BLE001
            pass
        py = be.check_python()
        ctk.CTkLabel(
            self.body,
            text=py.get("message") or "",
            text_color=OK_GREEN if py.get("ok") else DANGER,
            wraplength=860,
            justify="left",
        ).pack(anchor="w")
        if py.get("conflict_hint"):
            ctk.CTkLabel(
                self.body,
                text=py["conflict_hint"],
                text_color=WARN,
                wraplength=860,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))
        if py.get("fix") and not py.get("ok"):
            ctk.CTkLabel(
                self.body,
                text=f"Fix: {py['fix']}",
                text_color=WARN,
                wraplength=860,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))

        status = be.check_python_deps()
        msg = (
            "All required packages present."
            if status.get("ok")
            else f"Missing: {', '.join(status.get('missing') or [])}"
        )
        if status.get("isolated_venv"):
            msg += " (isolated venv)"
        self.deps_status_lbl = ctk.CTkLabel(
            self.body,
            text=msg,
            text_color=OK_GREEN if status.get("ok") else WARN,
            font=ctk.CTkFont(size=14),
        )
        self.deps_status_lbl.pack(anchor="w", pady=8)

        torch = be.check_torch_cuda()
        self.torch_lbl = ctk.CTkLabel(
            self.body,
            text=f"PyTorch (optional): {torch.get('message')}",
            text_color=OK_GREEN if torch.get("cuda") else MUTED,
            wraplength=860,
            justify="left",
        )
        self.torch_lbl.pack(anchor="w", pady=(0, 6))

        self.deps_step_lbl = ctk.CTkLabel(
            self.body,
            text="Ready — progress appears here when you Bootstrap or Install.",
            text_color=MUTED,
            wraplength=860,
            justify="left",
        )
        self.deps_step_lbl.pack(anchor="w", pady=(4, 2))
        self.deps_progress = ctk.CTkProgressBar(self.body, height=14, progress_color=ACCENT)
        self.deps_progress.pack(fill="x", pady=(0, 6))
        self.deps_progress.set(0)

        self.deps_log = self._log_box(180)
        self._append_log(
            self.deps_log,
            "Ready. Recommended: Bootstrap portable Python first (shows download %), then Install.\n"
            "Logs stay visible — if something fails, scroll up and use Copy log / Submit diagnostics.\n",
        )
        if status.get("fix"):
            self._append_log(self.deps_log, f"Fix if install fails:\n{status['fix']}\n")

        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkButton(
            row,
            text="Bootstrap portable Python",
            command=self._bootstrap_python,
            fg_color=ACCENT,
            text_color="#0A1210",
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Install / repair requirements",
            command=self._install_deps,
            fg_color="#2A3544",
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Install CUDA PyTorch (large)",
            command=self._install_torch,
            fg_color="#2A3544",
        ).pack(side="left")
        diag_row = ctk.CTkFrame(self.body, fg_color="transparent")
        diag_row.pack(fill="x", pady=(4, 0))
        ctk.CTkButton(
            diag_row,
            text="Copy log",
            width=110,
            fg_color="#2A3544",
            command=lambda: self._diag_copy("Python & Deps"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            diag_row,
            text="Submit diagnostics",
            width=150,
            fg_color="#2A3544",
            command=lambda: self._diag_submit("Python & Deps"),
        ).pack(side="left")
        self.deps_diag_lbl = ctk.CTkLabel(self.body, text="", text_color=MUTED)
        self.deps_diag_lbl.pack(anchor="w", pady=(2, 0))

    def _on_install_progress(self, label: str, detail: dict[str, Any]) -> None:
        """UI thread: update progress bar + keep log visible during download/install."""

        def apply() -> None:
            if not hasattr(self, "deps_log"):
                return
            pct = detail.get("percent")
            pkg = detail.get("package") or detail.get("current") or ""
            line = label
            if pkg:
                line = f"{label} — {pkg}"
            if pct is not None:
                try:
                    p = max(0.0, min(1.0, float(pct) / 100.0))
                    if hasattr(self, "deps_progress"):
                        self.deps_progress.set(p)
                    line = f"{line}  ({int(pct)}%)"
                except (TypeError, ValueError):
                    pass
            if hasattr(self, "deps_step_lbl"):
                self.deps_step_lbl.configure(text=line, text_color=ACCENT)
            # Avoid flooding the log with every percent tick — log label changes + package lines.
            raw_line = detail.get("line")
            if raw_line:
                self._append_log(self.deps_log, str(raw_line))
            elif pct is None or int(pct or 0) in (0, 100) or pkg:
                self._append_log(self.deps_log, line)

        self.app.post_ui(apply)

    def _bootstrap_python(self) -> None:
        if self._deps_busy:
            return
        self._deps_busy = True
        self.deps_log.delete("1.0", "end")
        if hasattr(self, "deps_progress"):
            self.deps_progress.set(0)
        self._append_log(
            self.deps_log,
            "Starting setup…\n"
            "You should see: Creating GPUPool folder → Downloading Python runtime → "
            "Creating environment → Installing dependencies.\n"
            "(Skips download if a healthy Python/venv already exists.)\n\n",
        )

        def work() -> None:
            try:
                result = be.bootstrap_portable_python(
                    dry_run=False,
                    with_requirements=True,
                    on_progress=self._on_install_progress,
                )
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "message": f"Bootstrap error: {exc}", "fix": "Use Copy log and retry."}
            self.app.post_ui(lambda: self._bootstrap_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _bootstrap_done(self, result: dict[str, Any]) -> None:
        self._deps_busy = False
        if hasattr(self, "deps_progress") and result.get("ok"):
            self.deps_progress.set(1.0)
        self._append_log(self.deps_log, result.get("message") or str(result))
        if result.get("actions"):
            self._append_log(self.deps_log, f"actions: {', '.join(result['actions'])}\n")
        if result.get("executable"):
            self._append_log(self.deps_log, f"python: {result['executable']}\n")
        if result.get("fix") and not result.get("ok"):
            self._append_log(self.deps_log, f"\nFIX:\n{result['fix']}\n")
            self._on_install_failure("Python & Deps", result)
        py = be.check_python()
        if hasattr(self, "deps_status_lbl"):
            status = be.check_python_deps()
            self.deps_status_lbl.configure(
                text=(
                    "All required packages present."
                    if status.get("ok")
                    else f"Missing: {', '.join(status.get('missing') or [])}"
                ),
                text_color=OK_GREEN if status.get("ok") else DANGER,
            )
        if hasattr(self, "deps_step_lbl"):
            self.deps_step_lbl.configure(
                text="Bootstrap OK." if result.get("ok") else "Bootstrap FAILED — see log.",
                text_color=OK_GREEN if result.get("ok") else DANGER,
            )
        self._append_log(
            self.deps_log,
            f"\nPython check: {py.get('message')}\n" + ("Bootstrap OK.\n" if result.get("ok") else "Bootstrap FAILED.\n"),
        )

    def _install_deps(self) -> None:
        if self._deps_busy:
            return
        self._deps_busy = True
        self.deps_log.delete("1.0", "end")
        if hasattr(self, "deps_progress"):
            self.deps_progress.set(0)
        self._append_log(self.deps_log, "Checking deps / installing missing packages…\n")

        def work() -> None:
            try:
                result = be.install_requirements(on_progress=self._on_install_progress)
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "message": f"Dependency install error: {exc}", "fix": "Use Copy log and retry."}
            self.app.post_ui(lambda: self._deps_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _deps_done(self, result: dict[str, Any]) -> None:
        self._deps_busy = False
        if hasattr(self, "deps_progress") and result.get("ok"):
            self.deps_progress.set(1.0)
        self._append_log(self.deps_log, result.get("message") or str(result))
        if result.get("fix"):
            self._append_log(self.deps_log, f"\nFIX:\n{result['fix']}\n")
        status = be.check_python_deps()
        self.deps_status_lbl.configure(
            text=(
                "All required packages present."
                if status.get("ok")
                else f"Missing: {', '.join(status.get('missing') or [])}"
            ),
            text_color=OK_GREEN if status.get("ok") else DANGER,
        )
        if hasattr(self, "deps_step_lbl"):
            self.deps_step_lbl.configure(
                text="Dependencies OK." if result.get("ok") else "Install FAILED — see log.",
                text_color=OK_GREEN if result.get("ok") else DANGER,
            )
        if result.get("ok"):
            self._append_log(self.deps_log, "\nDeps OK.\n")
        else:
            self._append_log(self.deps_log, "\nDeps FAILED — see FIX above. Use Copy log / Submit diagnostics.\n")
            self._on_install_failure("Python & Deps", result)

    def _diag_copy(self, step: str) -> None:
        result = be.copy_diagnostics_text(
            wizard_step=step,
            scheduler_url=self.settings.scheduler_url,
            portal_url=self.settings.portal_url,
            write_file=True,
        )
        text = result.get("text") or ""
        self.clipboard_clear()
        self.clipboard_append(text)
        path = result.get("path") or ""
        msg = f"Copied diagnostic log" + (f" · saved {path}" if path else "")
        if hasattr(self, "deps_diag_lbl"):
            self.deps_diag_lbl.configure(text=msg, text_color=OK_GREEN)
        if hasattr(self, "join_status"):
            self.join_status.configure(text=msg, text_color=OK_GREEN)
        if hasattr(self, "deps_log"):
            self._append_log(self.deps_log, f"\n{msg}\n")

    def _diag_submit(self, step: str) -> None:
        written = be.write_error_log(
            wizard_step=step,
            scheduler_url=self.settings.scheduler_url,
            portal_url=self.settings.portal_url,
            reason="submit",
        )

        def work() -> None:
            result = be.submit_diagnostics(
                portal_url=self.settings.portal_url,
                log_path=written.get("path") or "",
                text=written.get("text") or "",
                display_name=self.settings.discord_user or self.settings.worker_name,
                invite_code=PORTAL_INVITE_CODE,
            )
            self.app.post_ui(lambda: self._diag_submit_done(result, written))

        if hasattr(self, "deps_diag_lbl"):
            self.deps_diag_lbl.configure(text="Submitting diagnostics…", text_color=MUTED)
        if hasattr(self, "join_status"):
            self.join_status.configure(text="Submitting diagnostics…", text_color=MUTED)
        threading.Thread(target=work, daemon=True).start()

    def _diag_submit_done(self, result: dict[str, Any], written: dict[str, Any]) -> None:
        if result.get("ok"):
            msg = result.get("message") or "Submitted"
            color = OK_GREEN
        else:
            # Fallback: copy to clipboard so friend can paste to a pool admin
            clip = result.get("clipboard") or written.get("text") or ""
            if clip:
                self.clipboard_clear()
                self.clipboard_append(clip)
            msg = (
                (result.get("message") or "Submit failed")
                + " — log copied to clipboard. Paste to a pool admin in Discord."
            )
            if written.get("path"):
                msg += f" File: {written['path']}"
            color = WARN
        if hasattr(self, "deps_diag_lbl"):
            self.deps_diag_lbl.configure(text=msg, text_color=color)
        if hasattr(self, "join_status"):
            self.join_status.configure(text=msg, text_color=color)
        if hasattr(self, "deps_log"):
            self._append_log(self.deps_log, f"\n{msg}\n")
        if hasattr(self, "join_log"):
            self._append_log(self.join_log, f"\n{msg}\n")

    def _on_install_failure(self, step: str, result: dict[str, Any]) -> None:
        try:
            written = be.write_error_log(
                wizard_step=step,
                scheduler_url=self.settings.scheduler_url,
                portal_url=self.settings.portal_url,
                extra={"message": result.get("message"), "fix": result.get("fix")},
                include_traceback=str(result.get("message") or ""),
                reason="install-fail",
            )
            if hasattr(self, "deps_log") and written.get("path"):
                self._append_log(
                    self.deps_log,
                    f"\nDiagnostic log saved: {written['path']}\n"
                    "Use Copy log or Submit diagnostics so the host can debug.\n",
                )
        except Exception:  # noqa: BLE001
            pass

    def _install_torch(self) -> None:
        if self._deps_busy:
            return
        self._deps_busy = True
        if hasattr(self, "deps_progress"):
            self.deps_progress.set(0)
        self._append_log(
            self.deps_log,
            "\n--- CUDA PyTorch (optional, large download — several GB) — starting… ---\n"
            "Keep this window open. Progress lines appear below.\n",
        )

        def work() -> None:
            try:
                result = be.install_torch_cuda(on_progress=self._on_install_progress)
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "message": f"CUDA install error: {exc}", "fix": "Use Copy log and retry."}
            self.app.post_ui(lambda: self._torch_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _torch_done(self, result: dict[str, Any]) -> None:
        self._deps_busy = False
        if hasattr(self, "deps_progress") and result.get("ok"):
            self.deps_progress.set(1.0)
        self._append_log(self.deps_log, result.get("message") or str(result))
        if result.get("fix"):
            self._append_log(self.deps_log, f"\nFIX:\n{result['fix']}\n")
        torch = be.check_torch_cuda()
        self.torch_lbl.configure(
            text=f"PyTorch (optional): {torch.get('message')}",
            text_color=OK_GREEN if torch.get("cuda") else MUTED,
        )

    def _step_hardware(self) -> None:
        self._title(
            "Checking GPU & PC resources",
            "Live nvidia-smi + CPU/RAM/disk (real numbers, no mock data). "
            "No NVIDIA? Totally fine — use Utilize (jobs run on friends who have GPUs), "
            "or Contribute with VRAM=0 for CPU-only help.",
        )
        self.hw_box = self._log_box(280)
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
        self._no_gpu = not bool(gpus)
        lines = [
            f"NVIDIA: {'OK' if nv.get('ok') else 'NONE (optional)'} — {nv.get('message')}",
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
        if self._no_gpu:
            lines += [
                "",
                "No NVIDIA? You can still Utilize the pool or contribute CPU.",
                "Next: Connect → (optional Caps for CPU) → Finish → Utilize.",
                "Jobs run on online GPU workers on the host network. CUDA needs a GPU worker online.",
            ]
        lines += [
            "",
            f"Host RAM total/avail: {self._host_info.get('total_ram_mb', 0)} / "
            f"{self._host_info.get('avail_ram_mb', 0)} MiB",
            f"Host Disk total/free: {self._host_info.get('total_disk_gb', 0)} / "
            f"{self._host_info.get('free_disk_gb', 0)} GiB",
        ]
        if self._host_info.get("error"):
            lines.append(f"Host note: {self._host_info['error']}")
        self.hw_box.delete("1.0", "end")
        self.hw_box.insert("1.0", "\n".join(lines))

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
        self._title(
            "Scheduler connection",
            "Auto-detects public tunnel → Tailscale → localhost. You usually do NOT hand-edit GPU_SWARM_SCHEDULER_URL.",
        )
        ts = be.get_tailscale_ipv4()
        pub = be.get_public_access_info()
        ctk.CTkLabel(
            self.body,
            text=(
                f"Tailscale IPv4: {ts or 'not found'}  ·  "
                f"Public tunnel: {'ON' if pub.get('active') else 'off'}  ·  invite {PORTAL_INVITE_CODE}"
            ),
            text_color=MUTED,
        ).pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(self.body, text="Scheduler URL (auto-filled)", text_color=MUTED).pack(anchor="w")
        self.sched_entry = ctk.CTkEntry(self.body, height=36)
        self.sched_entry.pack(fill="x", pady=(0, 8))
        default = self.settings.scheduler_url or be.get_default_scheduler_url()
        self.sched_entry.insert(0, default)
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkButton(
            row, text="Auto-detect best", fg_color=ACCENT, text_color="#0A1210", command=self._auto_detect_sched
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="Tailscale", fg_color="#2A3544", command=self._use_ts).pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="Localhost", fg_color="#2A3544", command=self._use_local).pack(side="left")
        ctk.CTkButton(row, text="Test /status", fg_color="#2A3544", command=self._test_sched).pack(side="right")
        self.connect_log = self._log_box(180)
        # Kick auto-detect on first show so friends don't hand-edit env
        self.after(100, self._auto_detect_sched)

    def _auto_detect_sched(self) -> None:
        if not hasattr(self, "connect_log") or self.connect_log is None:
            return
        self.connect_log.delete("1.0", "end")
        self._append_log(self.connect_log, "Auto-detecting scheduler (public → Tailscale → localhost)…\n")

        def work() -> None:
            result = be.auto_detect_scheduler_url(probe=True, timeout=2.5)
            self.app.post_ui(lambda: self._auto_detect_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _auto_detect_done(self, result: dict[str, Any]) -> None:
        url = str(result.get("url") or "")
        if url and hasattr(self, "sched_entry") and self.sched_entry is not None:
            self.sched_entry.delete(0, "end")
            self.sched_entry.insert(0, url)
            self.settings.scheduler_url = url
            be.save_config(self.settings)
        ok = bool(result.get("ok"))
        self._append_log(
            self.connect_log,
            f"{'OK' if ok else 'WARN'} — {result.get('message') or url}\n"
            f"source={result.get('source')}  (env hand-edit not required)\n",
        )
        if result.get("hint") and not ok:
            self._append_log(self.connect_log, f"\n{result['hint']}\n")

    def _use_ts(self) -> None:
        self.sched_entry.delete(0, "end")
        self.sched_entry.insert(0, DEFAULT_SCHEDULER_URL)

    def _use_local(self) -> None:
        self.sched_entry.delete(0, "end")
        self.sched_entry.insert(0, DEFAULT_LOCAL_SCHEDULER_URL)

    def _test_sched(self) -> None:
        url = self.sched_entry.get().strip()
        self.connect_log.delete("1.0", "end")
        self._append_log(self.connect_log, f"Testing {url} …\n")

        def work() -> None:
            result = be.test_scheduler(url)
            self.app.post_ui(lambda: self._test_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _test_done(self, result: dict[str, Any]) -> None:
        if result.get("ok"):
            data = result.get("data") or {}
            self._append_log(
                self.connect_log,
                f"OK — {result.get('url')}\n"
                f"Workers online: {data.get('workers_online')}  "
                f"Free VRAM: {data.get('free_vram_mb')} MiB\n"
                f"CPU cores: {data.get('cpu_cores')}  "
                f"RAM avail: {data.get('ram_available_mb')} MiB  "
                f"Disk free: {data.get('disk_free_mb')} MiB\n",
            )
            # Prefer the URL that actually worked
            worked = result.get("url") or ""
            if worked and hasattr(self, "sched_entry"):
                self.sched_entry.delete(0, "end")
                self.sched_entry.insert(0, worked)
        else:
            self._append_log(self.connect_log, f"FAILED — {result.get('error')}\n")
            for a in result.get("attempts") or []:
                self._append_log(
                    self.connect_log,
                    f"  tried {a.get('url')}: {'ok' if a.get('ok') else a.get('error')}\n",
                )
            hint = result.get("hint") or be.scheduler_reachability_hint(
                ok=False,
                url=str(result.get("url") or url),
                error=str(result.get("error") or ""),
                tailscale_ipv4=result.get("tailscale_ipv4"),
            )
            self._append_log(self.connect_log, f"\n{hint}\n")

    def _step_caps(self) -> None:
        self._title(
            "Resource dedication",
            "Only you control how much of your PC is offered. Change anytime on your machine or in "
            "your Contribute settings. Sliders save locally (joiner_settings.json / LOCALAPPDATA) and "
            "apply to your worker only — nobody else can remotely raise your caps. "
            "0 VRAM/RAM/Disk = no extra soft cap (advertise detected free). "
            "Host GPU safety stays ON by default so the pool cannot freeze your desktop.",
        )
        gpus = be.get_gpus()
        host = be.detect_host_resources()
        total_vram = max(sum(int(g.get("memory_total_mb") or 0) for g in gpus), 1024)
        total_ram = max(int(host.get("total_ram_mb") or 0), 1024)
        total_disk = max(float(host.get("total_disk_gb") or 0), 10.0)

        live = ctk.CTkFrame(self.body, fg_color=PANEL, corner_radius=8)
        live.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            live,
            text=(
                f"Live host: {host.get('avail_ram_mb', 0)}/{host.get('total_ram_mb', 0)} MiB RAM avail  ·  "
                f"{host.get('free_disk_gb', 0)}/{host.get('total_disk_gb', 0)} GiB disk free  ·  "
                f"{len(gpus)} GPU(s), {sum(int(g.get('memory_free_mb') or 0) for g in gpus)} MiB VRAM free"
            ),
            text_color=MUTED,
            wraplength=860,
            justify="left",
        ).pack(anchor="w", padx=12, pady=10)

        self.vram_var = ctk.IntVar(value=int(self.settings.max_vram_mb or 0))
        self.cpu_var = ctk.DoubleVar(value=float(self.settings.max_cpu_percent or 50))
        self.ram_var = ctk.IntVar(value=int(self.settings.max_ram_mb or 0))
        self.disk_var = ctk.DoubleVar(value=float(self.settings.max_disk_gb or 0))

        self._slider_row(self.body, "Max VRAM (MiB)", self.vram_var, 0, total_vram, f"Detected total {total_vram} MiB")
        self._slider_row(self.body, "Max CPU (%)", self.cpu_var, 5, 100, "Soft advertise cap → dedicated_cpu_cores")
        self._slider_row(self.body, "Max RAM (MiB)", self.ram_var, 0, total_ram, f"Host total {total_ram} MiB")
        self._slider_row(self.body, "Max Disk (GiB)", self.disk_var, 0, total_disk, f"Host total {total_disk} GiB")

        self.host_protect_var = ctk.BooleanVar(value=bool(getattr(self.settings, "host_protect", True)))
        ctk.CTkCheckBox(
            self.body,
            text=(
                "Host GPU safety (recommended) — leave ~45% VRAM headroom, pause jobs when "
                "GPU util ≥65% or free VRAM is low so Windows stays responsive"
            ),
            variable=self.host_protect_var,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", pady=(12, 0))
        self._build_availability_controls(self.body, wizard=True)

    def _build_availability_controls(self, parent: Any, *, wizard: bool = False) -> None:
        frame = ctk.CTkFrame(parent, fg_color=PANEL if wizard else "transparent", corner_radius=8)
        frame.pack(fill="x", pady=(12, 0))
        pad = 12 if wizard else 0
        ctk.CTkLabel(
            frame,
            text="When should we use your PC?",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=pad, pady=(pad, 4))
        ctk.CTkLabel(
            frame,
            text=(
                "Pick when friends may run jobs. Outside the window the worker still checks in "
                "but pauses new jobs — same idea as host GPU safety."
            ),
            text_color=MUTED,
            wraplength=860,
            justify="left",
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=pad, pady=(0, 6))
        preset = str(getattr(self.settings, "availability_preset", "always") or "always")
        self.availability_preset_var = ctk.StringVar(value=preset)
        menu = ctk.CTkOptionMenu(
            frame,
            variable=self.availability_preset_var,
            values=list(PRESET_LABELS.keys()),
            command=lambda _v: self._update_availability_status_lbl(),
        )
        menu.pack(anchor="w", padx=pad, pady=(0, 6))
        custom_row = ctk.CTkFrame(frame, fg_color="transparent")
        custom_row.pack(fill="x", padx=pad, pady=(0, 6))
        ctk.CTkLabel(custom_row, text="Custom start (HH:MM)", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(
            side="left", padx=(0, 8)
        )
        self.avail_start_entry = ctk.CTkEntry(custom_row, width=80, height=28)
        self.avail_start_entry.pack(side="left", padx=(0, 12))
        self.avail_start_entry.insert(0, getattr(self.settings, "availability_daily_start", "22:00") or "22:00")
        ctk.CTkLabel(custom_row, text="Custom end (HH:MM)", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(
            side="left", padx=(0, 8)
        )
        self.avail_end_entry = ctk.CTkEntry(custom_row, width=80, height=28)
        self.avail_end_entry.pack(side="left")
        self.avail_end_entry.insert(0, getattr(self.settings, "availability_daily_end", "08:00") or "08:00")
        self.availability_status_lbl = ctk.CTkLabel(
            frame, text="", text_color=OK_GREEN, wraplength=860, justify="left"
        )
        self.availability_status_lbl.pack(anchor="w", padx=pad, pady=(0, pad))
        self._update_availability_status_lbl()

    def _update_availability_status_lbl(self) -> None:
        if not hasattr(self, "availability_status_lbl"):
            return
        try:
            s = be.load_config()
            _apply_availability_fields(
                s,
                self.availability_preset_var.get(),
                daily_start=self.avail_start_entry.get() if hasattr(self, "avail_start_entry") else "",
                daily_end=self.avail_end_entry.get() if hasattr(self, "avail_end_entry") else "",
            )
            self.availability_status_lbl.configure(text=be.get_availability_status(s).get("label") or "")
        except Exception as exc:  # noqa: BLE001
            self.availability_status_lbl.configure(text=f"Schedule: {exc}", text_color=WARN)

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

    def _step_join(self) -> None:
        no_gpu = bool(getattr(self, "_no_gpu", False)) or not be.get_gpus()
        self._title(
            "Utilize-first (no GPU)" if no_gpu else "Save & Join pool",
            (
                "No NVIDIA detected — finish setup and open Utilize. Jobs run on pool GPUs. "
                "Optional: also Contribute CPU (gpu_available=false)."
                if no_gpu
                else "Persists caps/identity, starts the worker, and shows success or the exact fix. "
                "On failure: Copy log / Submit diagnostics so the host can debug."
            ),
        )
        try:
            from gpu_swarm.diagnostics import set_wizard_step

            set_wizard_step("Join")
        except Exception:  # noqa: BLE001
            pass
        summary = ctk.CTkFrame(self.body, fg_color=PANEL, corner_radius=8)
        summary.pack(fill="x", pady=6)
        lines = [
            f"Worker: {self.settings.worker_name}",
            f"Discord: {self.settings.discord_user or '(none)'}",
            f"Scheduler: {self.settings.scheduler_url}",
            f"Portal: {self.settings.portal_url}  ·  invite {PORTAL_INVITE_CODE}",
            (
                f"Caps: VRAM {self.settings.max_vram_mb} MiB · CPU {self.settings.max_cpu_percent}% · "
                f"RAM {self.settings.max_ram_mb} MiB · Disk {self.settings.max_disk_gb} GiB"
            ),
            (
                "Host GPU safety: ON (desktop headroom)"
                if getattr(self.settings, "host_protect", True)
                else "Host GPU safety: OFF (desktop freeze risk)"
            ),
            "Mode: Utilize-first (no NVIDIA on this machine)" if no_gpu else "Mode: Contribute GPU/CPU",
        ]
        ctk.CTkLabel(
            summary,
            text="\n".join(lines),
            justify="left",
            text_color=MUTED,
            wraplength=860,
        ).pack(anchor="w", padx=14, pady=12)

        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", pady=8)
        if no_gpu:
            self.join_now_btn = ctk.CTkButton(
                row,
                text="Done → Utilize the pool",
                height=40,
                fg_color=ACCENT,
                text_color="#0A1210",
                font=ctk.CTkFont(size=15, weight="bold"),
                command=self._finish_utilize_first,
            )
            self.join_now_btn.pack(side="left", padx=(0, 8))
            ctk.CTkButton(
                row,
                text="Also contribute CPU",
                height=40,
                fg_color="#2A3544",
                command=self._join_now,
            ).pack(side="left", padx=(0, 8))
        else:
            self.join_now_btn = ctk.CTkButton(
                row,
                text="Save + Join pool",
                height=40,
                fg_color=ACCENT,
                text_color="#0A1210",
                font=ctk.CTkFont(size=15, weight="bold"),
                command=self._join_now,
            )
            self.join_now_btn.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Open portal",
            height=40,
            fg_color="#2A3544",
            command=lambda: be.open_portal_url(self.settings.portal_url),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Copy log",
            height=40,
            fg_color="#2A3544",
            command=lambda: self._diag_copy("Join"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Submit diagnostics",
            height=40,
            fg_color="#2A3544",
            command=lambda: self._diag_submit("Join"),
        ).pack(side="left")
        self.join_status = ctk.CTkLabel(self.body, text="", text_color=MUTED)
        self.join_status.pack(anchor="w", pady=(4, 0))
        self.join_log = self._log_box(220)
        if no_gpu:
            self.join_status.configure(
                text="Success path: Finish → Utilize → Run Probe (uses online pool GPUs).",
                text_color=OK_GREEN,
            )

    def _finish_utilize_first(self) -> None:
        """No-GPU laptop path: save settings and open main panel on Utilize (no worker required)."""
        self._persist_partial()
        self.settings.wizard_completed = True
        be.save_config(self.settings)
        # Stash preferred mode for MainFrame
        try:
            from gpu_swarm.paths import ROOT as _ROOT

            hint = _ROOT / "data" / "prefer_mode.txt"
            hint.parent.mkdir(parents=True, exist_ok=True)
            hint.write_text("utilize\n", encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        if hasattr(self, "join_status"):
            self.join_status.configure(
                text="Saved — opening Utilize. No GPU needed on your laptop.",
                text_color=OK_GREEN,
            )
        self.on_done()

    def _join_now(self) -> None:
        if self._join_busy:
            return
        self._join_busy = True
        self._persist_partial()
        self.settings.wizard_completed = True
        be.save_config(self.settings)
        self.join_now_btn.configure(state="disabled")
        self.join_status.configure(text="Starting worker…", text_color=MUTED)
        self.join_log.delete("1.0", "end")
        self._append_log(self.join_log, "Saving config and starting worker…\n")

        settings = be.load_config()

        def work() -> None:
            result = be.start_worker(settings, wait_online_sec=10.0)
            self.app.post_ui(lambda: self._join_now_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _join_now_done(self, result: dict[str, Any]) -> None:
        self._join_busy = False
        self.join_now_btn.configure(state="normal")
        ok = bool(result.get("ok"))
        msg = result.get("message") or ("Joined" if ok else "Failed")
        self.join_status.configure(text=msg, text_color=OK_GREEN if ok else DANGER)
        self._append_log(self.join_log, msg + "\n")
        if result.get("pid"):
            self._append_log(self.join_log, f"pid={result['pid']}\n")
        if result.get("warning"):
            self._append_log(self.join_log, f"Note: {result['warning']}\n")
        if result.get("log_tail"):
            self._append_log(self.join_log, f"\n--- log ---\n{result['log_tail']}\n")
        if result.get("fix"):
            self._append_log(self.join_log, f"\nFIX:\n{result['fix']}\n")
        diag = result.get("diagnostics") or {}
        if not ok:
            path = diag.get("path") or ""
            self._append_log(
                self.join_log,
                "\nJoin failed — use Copy log or Submit diagnostics so the host can debug.\n"
                + (f"Diagnostic file: {path}\n" if path else ""),
            )
        runtime = result.get("runtime") or {}
        if runtime:
            self._append_log(
                self.join_log,
                "\nLive advertised:\n"
                f"  connected={runtime.get('connected')}  status={runtime.get('detail')}\n"
                f"  cpu_cores={runtime.get('cpu_cores')}  "
                f"ram_available_mb={runtime.get('ram_available_mb')}  "
                f"disk_free_mb={runtime.get('disk_free_mb')}\n"
                f"  free_vram_mb={runtime.get('free_vram_mb')} / "
                f"total_vram_mb={runtime.get('total_vram_mb')}\n"
                f"  gpus={', '.join(runtime.get('gpus_advertised') or [])}\n",
            )

    def _alive(self, name: str) -> Any | None:
        """Return widget if attribute exists and Tk widget is still alive."""
        widget = getattr(self, name, None)
        if widget is None:
            return None
        try:
            if bool(widget.winfo_exists()):
                return widget
        except Exception:  # noqa: BLE001
            pass
        setattr(self, name, None)
        return None

    def _entry_text(self, name: str) -> str | None:
        widget = self._alive(name)
        if widget is None:
            return None
        try:
            return widget.get().strip()
        except Exception:  # noqa: BLE001
            setattr(self, name, None)
            return None

    def _persist_partial(self) -> None:
        portal = self._entry_text("portal_entry")
        if portal:
            self.settings.portal_url = portal
        name = self._entry_text("name_entry")
        if name:
            self.settings.worker_name = name
        discord = self._entry_text("discord_entry")
        if discord is not None:
            self.settings.discord_user = discord
        sched = self._entry_text("sched_entry")
        if sched:
            self.settings.scheduler_url = sched
        # Vars survive step rebuild; only read if present
        if getattr(self, "vram_var", None) is not None:
            try:
                self.settings.max_vram_mb = int(self.vram_var.get())
                self.settings.max_cpu_percent = float(self.cpu_var.get())
                self.settings.max_ram_mb = int(self.ram_var.get())
                self.settings.max_disk_gb = float(self.disk_var.get())
            except Exception:  # noqa: BLE001
                pass
        if getattr(self, "host_protect_var", None) is not None:
            try:
                self.settings.host_protect = bool(self.host_protect_var.get())
            except Exception:  # noqa: BLE001
                pass
        be.save_config(self.settings)

    def _clear_step_widgets(self) -> None:
        for name in ("portal_entry", "name_entry", "discord_entry", "sched_entry", "hw_box", "deps_log", "connect_log"):
            setattr(self, name, None)

    def _back(self) -> None:
        self._persist_partial()
        if self.step > 0:
            self.step -= 1
            self._clear_step_widgets()
            self._render_step()

    def _next(self) -> None:
        self._persist_partial()
        if self.step < len(self.STEPS) - 1:
            self.step += 1
            self._clear_step_widgets()
            self._render_step()
            return
        # Finish → main control panel (Join may already have run)
        self.settings.wizard_completed = True
        be.save_config(self.settings)
        self.on_done()


# =============================================================================
# Main control panel — Contribute | Utilize | Connect from code
# =============================================================================


class MainFrame(ctk.CTkFrame):
    def __init__(self, master: Any, app: GpuPoolApp) -> None:
        super().__init__(master, fg_color=BG)
        self.app = app
        self.settings = be.load_config()
        self._mode = "home"
        self._last_job_id = ""
        # Prefer a live portal URL (public / Tailscale :8767 when available)
        resolved = be.resolve_portal_url()
        if resolved.get("ok") and resolved.get("url"):
            self.settings.portal_url = resolved["url"]
            be.save_config(self.settings)
        # Laptop / no-GPU wizard finish → open Utilize
        try:
            from gpu_swarm.paths import ROOT as _ROOT

            prefer = (_ROOT / "data" / "prefer_mode.txt").read_text(encoding="utf-8").strip()
            if prefer in ("utilize", "contribute", "connect", "home"):
                self._mode = prefer
        except Exception:  # noqa: BLE001
            if not be.get_gpus():
                self._mode = "utilize"
        self._build()
        self._refresh_gpus()
        self._refresh_host()
        self._refresh_pool_utilize()
        self._refresh_connect_snippets()
        self._refresh_home_pool()
        self._schedule_poll()

    def _build(self) -> None:
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
            text=f"Join · Share · Use pool · Invite · invite: {PORTAL_INVITE_CODE}",
            text_color=MUTED,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w")

        btns = ctk.CTkFrame(header, fg_color="transparent")
        btns.pack(side="right", padx=16)
        ctk.CTkButton(
            btns,
            text="Home",
            width=90,
            fg_color="#2A3544",
            command=lambda: self._set_mode("home"),
        ).pack(side="left", padx=6)
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

        portal_bar = ctk.CTkFrame(self, fg_color="#13261F", corner_radius=0)
        portal_bar.pack(fill="x")
        self.portal_entry = ctk.CTkEntry(portal_bar, height=32)
        self.portal_entry.pack(side="left", fill="x", expand=True, padx=(16, 8), pady=8)
        self.portal_entry.insert(0, be.get_portal_url(self.settings) or DEFAULT_PORTAL_URL)
        ctk.CTkLabel(
            portal_bar,
            text=f"invite: {PORTAL_INVITE_CODE}",
            text_color=ACCENT,
            font=ctk.CTkFont(size=12),
        ).pack(side="right", padx=(0, 8))
        ctk.CTkButton(portal_bar, text="Open", width=80, fg_color="#2A3544", command=self._open_portal).pack(
            side="right", padx=(0, 16), pady=8
        )

        mode_bar = ctk.CTkFrame(self, fg_color="#0C1218", corner_radius=0)
        mode_bar.pack(fill="x")
        self._mode_btns: dict[str, ctk.CTkButton] = {}
        for key, label in (
            ("home", "Home"),
            ("contribute", "1 · Share my PC"),
            ("utilize", "2 · Use the pool"),
            ("connect", "3 · Connect"),
            ("share", "4 · Invite others"),
        ):
            btn = ctk.CTkButton(
                mode_bar,
                text=label,
                height=40,
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color=ACCENT if key == "home" else "#2A3544",
                text_color="#0A1210" if key == "home" else "#E8EEF4",
                command=lambda k=key: self._set_mode(k),
            )
            btn.pack(side="left", padx=(12 if key == "home" else 8, 0), pady=10, fill="x", expand=True)
            self._mode_btns[key] = btn

        self._mode_host = ctk.CTkFrame(self, fg_color=BG)
        self._mode_host.pack(fill="both", expand=True, padx=16, pady=12)

        self._home = ctk.CTkFrame(self._mode_host, fg_color=BG)
        self._contribute = ctk.CTkFrame(self._mode_host, fg_color=BG)
        self._utilize = ctk.CTkFrame(self._mode_host, fg_color=BG)
        self._connect = ctk.CTkFrame(self._mode_host, fg_color=BG)
        self._share = ctk.CTkFrame(self._mode_host, fg_color=BG)
        self._build_home(self._home)
        self._build_contribute(self._contribute)
        self._build_utilize(self._utilize)
        self._build_connect(self._connect)
        self._build_share(self._share)
        self._set_mode(self._mode or "home")

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        for frame in (self._home, self._contribute, self._utilize, self._connect, self._share):
            frame.pack_forget()
        {
            "home": self._home,
            "contribute": self._contribute,
            "utilize": self._utilize,
            "connect": self._connect,
            "share": self._share,
            "workspace": self._connect,
        }[mode].pack(fill="both", expand=True)
        for key, btn in self._mode_btns.items():
            on = key == mode
            btn.configure(fg_color=ACCENT if on else "#2A3544", text_color="#0A1210" if on else "#E8EEF4")
        if mode == "home":
            self._refresh_home_pool()
        elif mode == "utilize":
            if hasattr(self, "utilize_sched") and hasattr(self, "sched_entry"):
                cur = self.utilize_sched.get().strip()
                contrib = self.sched_entry.get().strip()
                if not cur and contrib:
                    self._set_entry(self.utilize_sched, contrib)
            self._refresh_pool_utilize()
            self._test_utilize_scheduler()
        elif mode == "connect":
            self._refresh_connect_snippets()
            self._test_connect_scheduler()
            self._refresh_workspace()
        elif mode == "share":
            self._refresh_share_pack()

    def _build_home(self, parent: Any) -> None:
        ctk.CTkLabel(
            parent,
            text="What do you want to do?",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=26),
        ).pack(anchor="w", pady=(4, 4))
        ctk.CTkLabel(
            parent,
            text=(
                "Pick one in under 30 seconds. Chat + Suggest live on the web hub. "
                "Workspace = optional Linux VM (CPU/RAM only — no NVIDIA passthrough)."
            ),
            text_color=MUTED,
            wraplength=980,
            justify="left",
        ).pack(anchor="w", pady=(0, 14))

        uses = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=10)
        uses.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            uses,
            text="What can you use this for?",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=16, pady=(14, 4))
        bullet = "\n".join(f"• {u['title']} — {u['body']}" for u in USE_CASES[:5])
        ctk.CTkLabel(
            uses,
            text=bullet + "\n• Invite friends — every PC that joins gives everyone more power.",
            text_color=MUTED,
            justify="left",
            wraplength=960,
        ).pack(anchor="w", padx=16, pady=(0, 14))

        cards = ctk.CTkFrame(parent, fg_color="transparent")
        cards.pack(fill="both", expand=True)
        cards.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="modes")
        cards.grid_rowconfigure(0, weight=1)

        specs = (
            (
                "contribute",
                "1 · Share my PC",
                "Contribute spare GPU/CPU",
                "Join as a worker with your caps. Host GPU safety ON by default so Windows stays usable.",
                "Share my PC →",
                False,
            ),
            (
                "utilize",
                "2 · Use the pool",
                "Run jobs on whoever is online",
                "No NVIDIA needed here. Probe / CUDA jobs run on online contributors.",
                "Use the pool →",
                False,
            ),
            (
                "share",
                "3 · Invite others",
                "Grow the network",
                "Copy a friend message, portal URL, invite code, and GitHub download link.",
                "Invite others →",
                False,
            ),
            (
                "connect",
                "4 · Connect / Workspace",
                "Tools + optional Linux desktop",
                "URLs, local model endpoint, Hermes Workspace (CPU/RAM only — no GPU passthrough).",
                "Open Connect →",
                True,
            ),
        )
        for col, (key, title, subtitle, body, cta, is_workspace) in enumerate(specs):
            card = ctk.CTkFrame(cards, fg_color=PANEL, corner_radius=14, border_width=1, border_color="#2A3544")
            card.grid(row=0, column=col, sticky="nsew", padx=8, pady=4)
            ctk.CTkLabel(
                card,
                text=title,
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=ACCENT,
            ).pack(anchor="w", padx=18, pady=(20, 4))
            ctk.CTkLabel(
                card,
                text=subtitle,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(anchor="w", padx=18)
            ctk.CTkLabel(
                card,
                text=body,
                text_color=MUTED,
                wraplength=220,
                justify="left",
            ).pack(anchor="w", padx=18, pady=(10, 16))
            if is_workspace:
                ctk.CTkButton(
                    card,
                    text=cta,
                    height=44,
                    fg_color="#2A3544",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    command=self._home_workspace_slot,
                ).pack(fill="x", padx=18, pady=(0, 20))
            else:
                ctk.CTkButton(
                    card,
                    text=cta,
                    height=44,
                    fg_color=ACCENT,
                    text_color="#0A1210",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    command=lambda k=key: self._set_mode(k),
                ).pack(fill="x", padx=18, pady=(0, 20))

        live = self._card(parent, "Live pool snapshot (hub)")
        self.home_pool_lbl = ctk.CTkLabel(live, text="Checking scheduler…", text_color=MUTED, wraplength=960, justify="left")
        self.home_pool_lbl.pack(anchor="w")
        self.home_workspace_lbl = ctk.CTkLabel(
            live, text="Workspace slot: …", text_color=MUTED, wraplength=960, justify="left"
        )
        self.home_workspace_lbl.pack(anchor="w", pady=(6, 0))
        row = ctk.CTkFrame(live, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        ctk.CTkButton(row, text="Refresh", fg_color="#2A3544", command=self._refresh_home_pool).pack(side="left")
        ctk.CTkButton(
            row,
            text="Run Probe now →",
            fg_color=ACCENT,
            text_color="#0A1210",
            command=lambda: (self._set_mode("utilize"), self._submit_utilize("probe")),
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            row,
            text="Web hub (chat / suggest)",
            fg_color="#2A3544",
            command=self._open_portal,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            row,
            text="How to Connect →",
            fg_color="#2A3544",
            command=lambda: self._set_mode("connect"),
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            row,
            text="Invite others →",
            fg_color=ACCENT,
            text_color="#0A1210",
            command=lambda: self._set_mode("share"),
        ).pack(side="left")

    def _build_share(self, parent: Any) -> None:
        ctk.CTkLabel(
            parent,
            text="Invite others",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=26),
        ).pack(anchor="w", pady=(4, 4))
        ctk.CTkLabel(
            parent,
            text=(
                "Grow the pool: copy a short friend message, portal URL, invite code, "
                "or GitHub download link. No passwords or tokens."
            ),
            text_color=MUTED,
            wraplength=980,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        card = self._card(parent, "Send this to a friend")
        self.share_msg_box = ctk.CTkTextbox(card, height=140, fg_color="#0C1218")
        self.share_msg_box.pack(fill="x", pady=(0, 8))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkButton(
            row,
            text="Copy friend message",
            fg_color=ACCENT,
            text_color="#0A1210",
            command=lambda: self._copy_share_field("send_to_friend", "Friend message copied."),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Copy full blurb",
            fg_color="#2A3544",
            command=lambda: self._copy_share_field("invite_blurb", "Full blurb copied."),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Copy portal URL",
            fg_color="#2A3544",
            command=lambda: self._copy_share_field("portal_best", "Portal URL copied."),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Copy invite code",
            fg_color="#2A3544",
            command=lambda: self._copy_share_field("invite_code", "Invite code copied."),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row,
            text="Copy download link",
            fg_color="#2A3544",
            command=lambda: self._copy_share_field("github_download", "Download link copied."),
        ).pack(side="left")

        meta = self._card(parent, "Links (live when known)")
        self.share_meta_lbl = ctk.CTkLabel(
            meta, text="Loading…", text_color=MUTED, wraplength=960, justify="left"
        )
        self.share_meta_lbl.pack(anchor="w")
        self._share_pack: dict[str, Any] = {}
        self._refresh_share_pack()

    def _refresh_share_pack(self) -> None:
        try:
            pack = be.get_share_pack()
        except Exception as exc:  # noqa: BLE001
            pack = {"send_to_friend": f"(share pack unavailable: {exc})", "invite_code": PORTAL_INVITE_CODE}
        self._share_pack = pack
        if hasattr(self, "share_msg_box"):
            self.share_msg_box.delete("1.0", "end")
            self.share_msg_box.insert("1.0", pack.get("send_to_friend") or pack.get("short_message") or "")
        if hasattr(self, "share_meta_lbl"):
            self.share_meta_lbl.configure(
                text=(
                    f"Portal: {pack.get('portal_best') or '—'}\n"
                    f"Invite: {pack.get('invite_code') or PORTAL_INVITE_CODE}\n"
                    f"Download: {pack.get('github_download') or '—'}\n"
                    f"Repo: {pack.get('github_repo') or '—'}\n"
                    f"{pack.get('invite_note') or ''}"
                )
            )

    def _copy_share_field(self, key: str, msg: str) -> None:
        pack = getattr(self, "_share_pack", None) or {}
        if not pack:
            try:
                pack = be.get_share_pack()
            except Exception:  # noqa: BLE001
                pack = {}
        value = str(pack.get(key) or "").strip()
        if not value and key == "invite_code":
            value = PORTAL_INVITE_CODE
        self._copy(value, msg)

    def _home_workspace_slot(self) -> None:
        """Jump to Connect workspace controls; web hub also has a Workspace slot."""
        info = be.get_agent_vms_info()
        ready = bool(info.get("ready"))
        path = info.get("path") or "(default)"
        msg = (
            f"Workspace: agent-vms {'ready' if ready else 'slot'} · {path} "
            "(Hermes owns VMs — not GPU passthrough). Chat/suggestions: Open web hub."
        )
        if hasattr(self, "home_workspace_lbl"):
            self.home_workspace_lbl.configure(text=msg, text_color=OK_GREEN if ready else MUTED)
        self._set_mode("connect")
        if hasattr(self, "_refresh_workspace"):
            self._refresh_workspace()

    def _refresh_home_pool(self) -> None:
        def work() -> None:
            url = self._scheduler_url_for_jobs()
            st = be.pool_status(url)
            info = be.get_agent_vms_info()
            self.app.post_ui(lambda: self._render_home_pool(st, info))

        threading.Thread(target=work, daemon=True).start()

    def _render_home_pool(self, st: dict[str, Any], workspace: dict[str, Any] | None = None) -> None:
        if not hasattr(self, "home_pool_lbl"):
            return
        if workspace is not None and hasattr(self, "home_workspace_lbl"):
            ready = bool(workspace.get("ready"))
            self.home_workspace_lbl.configure(
                text=(
                    f"Workspace: agent-vms {'ready' if ready else 'slot'} · {workspace.get('path') or ''}"
                ),
                text_color=OK_GREEN if ready else MUTED,
            )
        if st.get("ok"):
            gpus = ", ".join(st.get("gpus") or []) or "(none listed)"
            text = (
                f"Scheduler OK · {st.get('url')}  ·  "
                f"workers online {st.get('workers_online', 0)}/{st.get('workers_total', 0)}  ·  "
                f"VRAM free {st.get('free_vram_mb', 0)} MiB  ·  GPUs: {gpus}"
            )
            self.home_pool_lbl.configure(text=text, text_color=OK_GREEN)
        else:
            hint = (st.get("hint") or "").splitlines()
            short = hint[0] if hint else "Cannot reach Tailscale/LAN scheduler yet."
            self.home_pool_lbl.configure(
                text=(
                    f"{short} Tried {st.get('url') or 'n/a'}. "
                    "Install/login Tailscale, join the private pool network, then retry — "
                    f"or on the host PC use {DEFAULT_LOCAL_SCHEDULER_URL}."
                ),
                text_color=DANGER,
            )

    def _scheduler_url_for_jobs(self) -> str:
        """Prefer Utilize field, then Contribute field, then saved/default."""
        for name in ("utilize_sched", "sched_entry", "connect_sched"):
            widget = getattr(self, name, None)
            if widget is None:
                continue
            try:
                url = widget.get().strip()
                if url:
                    return url
            except Exception:  # noqa: BLE001
                continue
        return (self.settings.scheduler_url or DEFAULT_LOCAL_SCHEDULER_URL).rstrip("/")

    def _build_contribute(self, parent: Any) -> None:
        parent.grid_columnconfigure(0, weight=3)
        parent.grid_columnconfigure(1, weight=2)
        parent.grid_rowconfigure(0, weight=1)
        left_col = ctk.CTkFrame(parent, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right_col = ctk.CTkFrame(parent, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._build_identity(left_col)
        self._build_gpus(left_col)
        self._build_caps(left_col)
        self._build_actions(left_col)
        self._build_status(right_col)
        self._build_discord(right_col)

    def _build_utilize(self, parent: Any) -> None:
        parent.grid_columnconfigure(0, weight=3)
        parent.grid_columnconfigure(1, weight=2)
        parent.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(parent, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        intro = self._card(left, "Utilize — use the pool NOW")
        ctk.CTkLabel(
            intro,
            text=(
                f"{be.PRIVATE_NETWORK_BLURB} "
                "Submit allowlisted jobs to live workers. No arbitrary shell."
            ),
            text_color=MUTED,
            wraplength=560,
            justify="left",
        ).pack(anchor="w")
        srow = ctk.CTkFrame(intro, fg_color="transparent")
        srow.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(srow, text="Scheduler URL", text_color=MUTED).pack(side="left")
        self.utilize_sched = ctk.CTkEntry(srow, height=34)
        self.utilize_sched.pack(side="left", fill="x", expand=True, padx=8)
        self.utilize_sched.insert(0, self.settings.scheduler_url or DEFAULT_LOCAL_SCHEDULER_URL)
        ctk.CTkButton(
            srow, text="Local", width=70, fg_color="#2A3544",
            command=lambda: self._set_entry(self.utilize_sched, DEFAULT_LOCAL_SCHEDULER_URL),
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            srow, text="Tailscale", width=90, fg_color="#2A3544",
            command=lambda: self._set_entry(self.utilize_sched, DEFAULT_SCHEDULER_URL),
        ).pack(side="left")
        crow = ctk.CTkFrame(intro, fg_color="transparent")
        crow.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(
            crow,
            text="Test Tailscale connection",
            width=190,
            fg_color=ACCENT,
            text_color="#0A1210",
            command=self._test_utilize_scheduler,
        ).pack(side="left")
        self.utilize_conn_lbl = ctk.CTkLabel(
            crow, text="Connection: not tested yet", text_color=MUTED, wraplength=360, justify="left"
        )
        self.utilize_conn_lbl.pack(side="left", padx=10)

        pool = self._card(left, "Pool status (live)")
        self.pool_box = ctk.CTkTextbox(pool, height=160, fg_color="#121A24")
        self.pool_box.pack(fill="x")
        prow = ctk.CTkFrame(pool, fg_color="transparent")
        prow.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(prow, text="Refresh pool", fg_color="#2A3544", command=self._refresh_pool_utilize).pack(
            side="left"
        )
        self.pool_lbl = ctk.CTkLabel(prow, text="", text_color=MUTED)
        self.pool_lbl.pack(side="left", padx=10)

        jobs = self._card(left, "Run a job")
        ctk.CTkLabel(
            jobs,
            text="Big actions below hit the live scheduler and wait for completion.",
            text_color=MUTED,
            wraplength=520,
            justify="left",
        ).pack(anchor="w")
        brow = ctk.CTkFrame(jobs, fg_color="transparent")
        brow.pack(fill="x", pady=(12, 0))
        ctk.CTkButton(
            brow,
            text="Run Probe",
            height=48,
            width=160,
            fg_color=ACCENT,
            text_color="#0A1210",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=lambda: self._submit_utilize("probe"),
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            brow,
            text="Run CUDA Job",
            height=48,
            width=180,
            fg_color=ACCENT,
            text_color="#0A1210",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=lambda: self._submit_utilize("pytorch_cuda_probe"),
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(brow, text="Poll last job", height=48, fg_color="#2A3544", command=self._poll_last_job).pack(
            side="left"
        )
        self.utilize_lbl = ctk.CTkLabel(jobs, text="Job status: idle", text_color=MUTED)
        self.utilize_lbl.pack(anchor="w", pady=(10, 0))

        result = self._card(left, "Job status + result")
        self.job_box = ctk.CTkTextbox(result, height=210, fg_color="#121A24")
        self.job_box.pack(fill="both", expand=True)
        self.job_box.insert("1.0", "Submit a job to see status and JSON result here.\n")

        help_card = self._card(right, "What can I run?")
        self.utilize_help = ctk.CTkTextbox(help_card, height=220, fg_color="#121A24")
        self.utilize_help.pack(fill="x")
        self.utilize_help.insert("1.0", be.get_utilize_helper_text())
        self.utilize_help.configure(state="disabled")
        ctk.CTkButton(
            help_card,
            text="Copy Discord equivalents",
            fg_color="#2A3544",
            command=lambda: self._copy(be.get_discord_helper_text(), "Copied Discord slash helpers."),
        ).pack(anchor="e", pady=(8, 0))

        disc = self._card(right, "Discord tips (utilize)")
        box = ctk.CTkTextbox(disc, height=160, fg_color="#121A24")
        box.pack(fill="x")
        box.insert(
            "1.0",
            "Glitch Factor — GPU Pool bot\n"
            "\n"
            "/pool           pool overview\n"
            "/workers        list workers\n"
            "/submit_probe   same as Run Probe\n"
            "/submit_compute same as Run CUDA Job\n"
            "/job_status id  poll a job\n",
        )
        box.configure(state="disabled")

    def _set_entry(self, entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)
        if entry is getattr(self, "utilize_sched", None):
            self._refresh_pool_utilize()

    def _build_connect(self, parent: Any) -> None:
        scroll = ctk.CTkScrollableFrame(parent, fg_color=BG)
        scroll.pack(fill="both", expand=True)

        ws = self._card(scroll, "Workspace — agent Ubuntu VM (Hermes / VirtualBox)")
        ctk.CTkLabel(
            ws,
            text=(
                "One-product path: open a capped Linux desktop workspace from GPU Pool. "
                "CPU/RAM come from your Contribute share (+ host_protect ceiling). "
                "Shared GPU/VRAM is NOT passed into the VM — pool jobs still use the host worker."
            ),
            text_color=MUTED,
            wraplength=900,
            justify="left",
        ).pack(anchor="w")
        self.workspace_plan_lbl = ctk.CTkLabel(
            ws,
            text="Resource plan: checking…",
            text_color=ACCENT,
            wraplength=900,
            justify="left",
        )
        self.workspace_plan_lbl.pack(anchor="w", pady=(8, 4))
        ws_row = ctk.CTkFrame(ws, fg_color="transparent")
        ws_row.pack(fill="x", pady=(8, 4))
        self.workspace_open_btn = ctk.CTkButton(
            ws_row,
            text="Start / Open workspace",
            width=200,
            fg_color=ACCENT,
            text_color="#0A1210",
            command=self._open_workspace,
        )
        self.workspace_open_btn.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            ws_row,
            text="Open RDP only",
            width=130,
            fg_color="#2A3544",
            command=self._open_workspace_rdp,
        ).pack(side="left", padx=(0, 8))
        self.workspace_halt_btn = ctk.CTkButton(
            ws_row,
            text="Halt VM",
            width=100,
            fg_color=DANGER,
            command=self._halt_workspace,
        )
        self.workspace_halt_btn.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            ws_row,
            text="Refresh",
            width=90,
            fg_color="#2A3544",
            command=self._refresh_workspace,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            ws_row,
            text="ADVANCED_VM.md",
            width=140,
            fg_color="#2A3544",
            command=lambda: self._open_doc(be.ADVANCED_VM_DOC),
        ).pack(side="left")
        self.workspace_status_lbl = ctk.CTkLabel(
            ws,
            text="Workspace: checking…",
            text_color=MUTED,
            wraplength=900,
            justify="left",
        )
        self.workspace_status_lbl.pack(anchor="w", pady=(6, 0))
        self._refresh_workspace()

        friends = self._card(scroll, "How friends connect")
        friends_box = ctk.CTkTextbox(friends, height=150, fg_color="#121A24")
        friends_box.pack(fill="x")
        friends_box.insert("1.0", be.get_friends_connect_text())
        friends_box.configure(state="disabled")

        pub = be.get_public_access_info()
        if pub.get("active"):
            pub_card = self._card(scroll, "Public access — no Tailscale needed")
            ctk.CTkLabel(
                pub_card,
                text=(
                    f"{pub.get('message')}\n"
                    f"Portal:  {pub.get('portal_path')}\n"
                    f"Pool API: {pub.get('pool_api_public_url')}\n"
                    f"Invite:  {PORTAL_INVITE_CODE}"
                ),
                text_color=ACCENT,
                wraplength=900,
                justify="left",
            ).pack(anchor="w")
            prow_pub = ctk.CTkFrame(pub_card, fg_color="transparent")
            prow_pub.pack(fill="x", pady=(8, 0))
            ctk.CTkButton(
                prow_pub,
                text="Open public portal",
                width=160,
                fg_color=ACCENT,
                text_color="#0A1210",
                command=lambda u=pub.get("portal_path"): be.open_portal_url(u),
            ).pack(side="left", padx=(0, 8))
            ctk.CTkButton(
                prow_pub,
                text="Copy public portal",
                width=150,
                fg_color="#2A3544",
                command=lambda u=pub.get("portal_path") or "": self._copy(
                    u, "Copied public portal URL (no Tailscale)."
                ),
            ).pack(side="left")

        local_ep = self._card(scroll, "Local model endpoint — pool as a local AI API")
        ctk.CTkLabel(
            local_ep,
            text=(
                "Start a localhost OpenAI-compatible API that apps can point at "
                "(Open WebUI / LM Studio / Continue / Cursor). "
                "This appears as a local AI API for apps — not a physical GPU device."
            ),
            text_color=MUTED,
            wraplength=900,
            justify="left",
        ).pack(anchor="w")
        lep_row = ctk.CTkFrame(local_ep, fg_color="transparent")
        lep_row.pack(fill="x", pady=(10, 4))
        self.local_ep_start_btn = ctk.CTkButton(
            lep_row,
            text="Start local endpoint",
            width=180,
            fg_color=ACCENT,
            text_color="#0A1210",
            command=self._start_local_endpoint,
        )
        self.local_ep_start_btn.pack(side="left", padx=(0, 8))
        self.local_ep_stop_btn = ctk.CTkButton(
            lep_row,
            text="Stop",
            width=90,
            fg_color=DANGER,
            command=self._stop_local_endpoint,
        )
        self.local_ep_stop_btn.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            lep_row,
            text="Refresh",
            width=90,
            fg_color="#2A3544",
            command=self._refresh_local_endpoint,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            lep_row,
            text="Copy OpenAI base URL",
            width=180,
            fg_color="#2A3544",
            command=self._copy_local_endpoint_url,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            lep_row,
            text="Open LOCAL_MODEL.md",
            width=170,
            fg_color="#2A3544",
            command=lambda: self._open_doc(be.LOCAL_MODEL_DOC),
        ).pack(side="left")
        self.local_ep_url = ctk.CTkEntry(local_ep, height=36)
        self.local_ep_url.pack(fill="x", pady=(8, 4))
        self.local_ep_status_lbl = ctk.CTkLabel(
            local_ep,
            text="Local endpoint: checking…",
            text_color=MUTED,
            wraplength=900,
            justify="left",
        )
        self.local_ep_status_lbl.pack(anchor="w", pady=(2, 0))
        self._refresh_local_endpoint()

        llm = self._card(scroll, "LLM routing — mounted shared models")
        ctk.CTkLabel(
            llm,
            text=(
                "Online workers advertise the models they have mounted. Choose one here for local tooling; "
                "contributors can run Ollama, LM Studio, vLLM, llama.cpp, or another OpenAI-compatible server. "
                "API keys never belong in this field or in Discord."
            ),
            text_color=MUTED,
            wraplength=900,
            justify="left",
        ).pack(anchor="w")
        llm_endpoint_row = ctk.CTkFrame(llm, fg_color="transparent")
        llm_endpoint_row.pack(fill="x", pady=(10, 4))
        ctk.CTkLabel(llm_endpoint_row, text="Your provider base URL", text_color=MUTED).pack(side="left")
        self.llm_provider_entry = ctk.CTkEntry(
            llm_endpoint_row,
            height=34,
            placeholder_text="http://127.0.0.1:11434 or http://127.0.0.1:1234/v1",
        )
        self.llm_provider_entry.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(
            llm_endpoint_row,
            text="Save provider",
            width=125,
            fg_color=ACCENT,
            text_color="#0A1210",
            command=self._save_llm_provider,
        ).pack(side="left")
        llm_model_row = ctk.CTkFrame(llm, fg_color="transparent")
        llm_model_row.pack(fill="x", pady=(8, 4))
        ctk.CTkLabel(llm_model_row, text="Mounted model", text_color=MUTED).pack(side="left")
        self.llm_model_menu = ctk.CTkOptionMenu(
            llm_model_row,
            values=["No online mounted models"],
            width=460,
            command=self._select_llm_model,
        )
        self.llm_model_menu.pack(side="left", padx=10)
        ctk.CTkButton(
            llm_model_row,
            text="Refresh catalog",
            width=130,
            fg_color="#2A3544",
            command=self._refresh_llm_catalog,
        ).pack(side="left")
        self.llm_model_status_lbl = ctk.CTkLabel(
            llm,
            text="Mounted model catalog: checking…",
            text_color=MUTED,
            wraplength=900,
            justify="left",
        )
        self.llm_model_status_lbl.pack(anchor="w", pady=(4, 0))
        self._llm_catalog_entries: list[dict[str, Any]] = []
        self._llm_selected_model = ""
        self._refresh_llm_catalog()

        cloud = self._card(scroll, "Cloudflare public access")
        ctk.CTkLabel(
            cloud,
            text="Optional HTTPS access for the portal. Quick Tunnel is temporary; named Tunnel uses your Cloudflare-managed hostname.",
            text_color=MUTED,
            wraplength=900,
            justify="left",
        ).pack(anchor="w")
        self.main_cloudflare_status_lbl = ctk.CTkLabel(cloud, text="Checking Cloudflare status…", text_color=MUTED, wraplength=900, justify="left")
        self.main_cloudflare_status_lbl.pack(anchor="w", pady=(6, 4))
        cf_fields = ctk.CTkFrame(cloud, fg_color="transparent")
        cf_fields.pack(fill="x", pady=(0, 6))
        self.main_cloudflare_hostname = ctk.CTkEntry(cf_fields, height=32, placeholder_text="Stable hostname, e.g. gpu-pool.example.com")
        self.main_cloudflare_hostname.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.main_cloudflare_tunnel_name = ctk.CTkEntry(cf_fields, width=150, height=32, placeholder_text="Tunnel name")
        self.main_cloudflare_tunnel_name.pack(side="left")
        self.main_cloudflare_tunnel_name.insert(0, "gpu-pool")
        cf_actions = ctk.CTkFrame(cloud, fg_color="transparent")
        cf_actions.pack(fill="x", pady=(0, 4))
        ctk.CTkButton(cf_actions, text="Publish Quick Tunnel", width=170, fg_color=ACCENT, text_color="#0A1210", command=self._main_cloudflare_quick).pack(side="left", padx=(0, 8))
        ctk.CTkButton(cf_actions, text="Create & launch named", width=185, fg_color=ACCENT, text_color="#0A1210", command=self._main_cloudflare_named).pack(side="left", padx=(0, 8))
        ctk.CTkButton(cf_actions, text="Install helper", width=120, fg_color="#2A3544", command=self._main_cloudflare_install).pack(side="left", padx=(0, 8))
        ctk.CTkButton(cf_actions, text="Guide", width=80, fg_color="#2A3544", command=self._open_cloudflare_guide_main).pack(side="left")
        self._refresh_main_cloudflare()

        inner = self._card(scroll, "Connect — plug into the pool from code / tools")
        ctk.CTkLabel(
            inner,
            text=(
                f"{be.PRIVATE_NETWORK_BLURB} "
                "Copy the scheduler / pool-api URL into your tools, open the portal, or paste snippets. "
                "Env var: GPU_SWARM_SCHEDULER_URL"
            ),
            text_color=MUTED,
            wraplength=900,
            justify="left",
        ).pack(anchor="w")

        docs = ctk.CTkFrame(inner, fg_color="transparent")
        docs.pack(fill="x", pady=(10, 4))
        ctk.CTkButton(
            docs,
            text="Open CONNECTING.md",
            width=170,
            fg_color=ACCENT,
            text_color="#0A1210",
            command=lambda: self._open_doc(be.CONNECTING_DOC),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            docs,
            text="Open examples/",
            width=130,
            fg_color="#2A3544",
            command=lambda: self._open_doc(be.CODING_AGENT_EXAMPLE.parent),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            docs,
            text="coding_agent_pool.py",
            width=180,
            fg_color="#2A3544",
            command=lambda: self._open_doc(be.CODING_AGENT_EXAMPLE),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            docs,
            text="Local LLM notes",
            width=130,
            fg_color="#2A3544",
            command=lambda: self._open_doc(be.LOCAL_OFFLOAD_DOC),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            docs,
            text="LOCAL_MODEL.md",
            width=140,
            fg_color="#2A3544",
            command=lambda: self._open_doc(be.LOCAL_MODEL_DOC),
        ).pack(side="left")

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=(12, 4))
        ctk.CTkLabel(row, text="Scheduler URL  (GPU_SWARM_SCHEDULER_URL)", text_color=MUTED).pack(side="left")
        self.connect_sched = ctk.CTkEntry(row, height=36)
        self.connect_sched.pack(side="left", fill="x", expand=True, padx=10)
        default_sched = (
            pub.get("pool_api_public_url")
            if pub.get("active") and pub.get("pool_api_public_url")
            else DEFAULT_SCHEDULER_URL
        )
        self.connect_sched.insert(0, default_sched)
        ctk.CTkButton(row, text="Copy", width=80, fg_color=ACCENT, text_color="#0A1210", command=self._copy_sched_url).pack(
            side="left", padx=(0, 4)
        )
        ctk.CTkButton(
            row, text="Local", width=70, fg_color="#2A3544",
            command=lambda: self._set_entry(self.connect_sched, DEFAULT_LOCAL_SCHEDULER_URL),
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            row, text="Tailscale", width=90, fg_color="#2A3544",
            command=lambda: self._set_entry(self.connect_sched, DEFAULT_SCHEDULER_URL),
        ).pack(side="left", padx=(0, 4))
        if pub.get("active") and pub.get("pool_api_public_url"):
            ctk.CTkButton(
                row,
                text="Public API",
                width=100,
                fg_color="#2A3544",
                command=lambda u=pub.get("pool_api_public_url"): self._set_entry(self.connect_sched, u or ""),
            ).pack(side="left")

        prow = ctk.CTkFrame(inner, fg_color="transparent")
        prow.pack(fill="x", pady=(4, 8))
        ctk.CTkLabel(prow, text=f"Portal URL  (invite: {PORTAL_INVITE_CODE})", text_color=MUTED).pack(side="left")
        self.connect_portal = ctk.CTkEntry(prow, height=36)
        self.connect_portal.pack(side="left", fill="x", expand=True, padx=10)
        default_portal = (
            pub.get("portal_path")
            if pub.get("active") and pub.get("portal_path")
            else DEFAULT_PORTAL_URL
        )
        self.connect_portal.insert(0, default_portal)
        ctk.CTkButton(
            prow, text="Open", width=80, fg_color=ACCENT, text_color="#0A1210", command=self._open_ts_portal
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(prow, text="Copy", width=70, fg_color="#2A3544", command=self._copy_portal_url).pack(side="left")

        trow = ctk.CTkFrame(inner, fg_color="transparent")
        trow.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(
            trow,
            text="Test Tailscale scheduler",
            width=190,
            fg_color=ACCENT,
            text_color="#0A1210",
            command=self._test_connect_scheduler,
        ).pack(side="left")
        self.connect_status_lbl = ctk.CTkLabel(
            trow, text="Connection: not tested yet", text_color=MUTED, wraplength=680, justify="left"
        )
        self.connect_status_lbl.pack(side="left", padx=10)

        tips = self._card(scroll, "Discord tips")
        tip_box = ctk.CTkTextbox(tips, height=90, fg_color="#121A24")
        tip_box.pack(fill="x")
        tip_box.insert(
            "1.0",
            "/pool — live workers + VRAM\n"
            "/submit_probe — GPU inventory job\n"
            "/submit_compute — CUDA matmul\n"
            "/job_status <id> — poll result\n",
        )
        tip_box.configure(state="disabled")

        snip = self._card(scroll, "Python GPUPool · CLI utilize · HTTP")
        self.connect_box = ctk.CTkTextbox(snip, height=320, fg_color="#121A24")
        self.connect_box.pack(fill="both", expand=True, pady=(0, 0))
        crow = ctk.CTkFrame(snip, fg_color="transparent")
        crow.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(crow, text="Refresh snippets", fg_color="#2A3544", command=self._refresh_connect_snippets).pack(
            side="left"
        )
        ctk.CTkButton(
            crow,
            text="Copy all snippets",
            fg_color=ACCENT,
            text_color="#0A1210",
            command=lambda: self._copy(self.connect_box.get("1.0", "end").strip(), "Copied connect-from-code snippets."),
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            crow,
            text="Copy env + CLI",
            fg_color="#2A3544",
            command=self._copy_agent_cmd,
        ).pack(side="left")
        self.connect_lbl = ctk.CTkLabel(crow, text="", text_color=MUTED)
        self.connect_lbl.pack(side="left", padx=8)

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
        inner = self._card(parent, "Detected GPUs + live host metrics")
        self.gpu_box = ctk.CTkTextbox(inner, height=110, fg_color="#121A24")
        self.gpu_box.pack(fill="x")
        self.host_lbl = ctk.CTkLabel(inner, text="", text_color=MUTED, font=ctk.CTkFont(size=11))
        self.host_lbl.pack(anchor="w", pady=(6, 0))

    def _build_caps(self, parent: Any) -> None:
        inner = self._card(parent, "Dedication — VRAM · CPU · RAM · Disk")
        ctk.CTkLabel(
            inner,
            text=(
                "Only you control how much of your PC is offered. Change anytime on your machine "
                "or in your Contribute settings. Saves to local joiner settings for this worker only. "
                "Host GPU safety (default ON) still clamps offer + pauses jobs so the desktop cannot freeze."
            ),
            text_color=MUTED,
            wraplength=900,
            justify="left",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", pady=(0, 8))
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
        self._build_availability_controls(inner)
        self.host_protect_var = ctk.BooleanVar(value=bool(getattr(self.settings, "host_protect", True)))
        ctk.CTkCheckBox(
            inner,
            text=(
                "Host GPU safety (recommended) — ~55% VRAM offer ceiling, pause at ≥65% util / low free VRAM"
            ),
            variable=self.host_protect_var,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", pady=(10, 0))
        ctk.CTkButton(inner, text="Save caps & identity", fg_color="#2A3544", command=self._save_settings).pack(
            anchor="e", pady=(8, 0)
        )

    def _build_availability_controls(self, parent: Any, *, wizard: bool = False) -> None:
        frame = ctk.CTkFrame(parent, fg_color=PANEL if wizard else "transparent", corner_radius=8)
        frame.pack(fill="x", pady=(12, 0))
        pad = 12 if wizard else 0
        ctk.CTkLabel(
            frame,
            text="When should we use your PC?",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=pad, pady=(pad, 4))
        ctk.CTkLabel(
            frame,
            text=(
                "Pick when friends may run jobs. Outside the window the worker still checks in "
                "but pauses new jobs — same idea as host GPU safety."
            ),
            text_color=MUTED,
            wraplength=860,
            justify="left",
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=pad, pady=(0, 6))
        preset = str(getattr(self.settings, "availability_preset", "always") or "always")
        self.availability_preset_var = ctk.StringVar(value=preset)
        menu = ctk.CTkOptionMenu(
            frame,
            variable=self.availability_preset_var,
            values=list(PRESET_LABELS.keys()),
            command=lambda _v: self._update_availability_status_lbl(),
        )
        menu.pack(anchor="w", padx=pad, pady=(0, 6))
        custom_row = ctk.CTkFrame(frame, fg_color="transparent")
        custom_row.pack(fill="x", padx=pad, pady=(0, 6))
        ctk.CTkLabel(custom_row, text="Custom start (HH:MM)", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(
            side="left", padx=(0, 8)
        )
        self.avail_start_entry = ctk.CTkEntry(custom_row, width=80, height=28)
        self.avail_start_entry.pack(side="left", padx=(0, 12))
        self.avail_start_entry.insert(0, getattr(self.settings, "availability_daily_start", "22:00") or "22:00")
        ctk.CTkLabel(custom_row, text="Custom end (HH:MM)", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(
            side="left", padx=(0, 8)
        )
        self.avail_end_entry = ctk.CTkEntry(custom_row, width=80, height=28)
        self.avail_end_entry.pack(side="left")
        self.avail_end_entry.insert(0, getattr(self.settings, "availability_daily_end", "08:00") or "08:00")
        self.availability_status_lbl = ctk.CTkLabel(
            frame, text="", text_color=OK_GREEN, wraplength=860, justify="left"
        )
        self.availability_status_lbl.pack(anchor="w", padx=pad, pady=(0, pad))
        self._update_availability_status_lbl()

    def _update_availability_status_lbl(self) -> None:
        if not hasattr(self, "availability_status_lbl"):
            return
        try:
            s = be.load_config()
            _apply_availability_fields(
                s,
                self.availability_preset_var.get(),
                daily_start=self.avail_start_entry.get() if hasattr(self, "avail_start_entry") else "",
                daily_end=self.avail_end_entry.get() if hasattr(self, "avail_end_entry") else "",
            )
            self.availability_status_lbl.configure(text=be.get_availability_status(s).get("label") or "")
        except Exception as exc:  # noqa: BLE001
            self.availability_status_lbl.configure(text=f"Schedule: {exc}", text_color=WARN)

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
        inner = self._card(parent, "Status (live metrics)")
        self.status_box = ctk.CTkTextbox(inner, height=260, fg_color="#121A24")
        self.status_box.pack(fill="both", expand=True)
        ctk.CTkButton(inner, text="Refresh now", fg_color="#2A3544", command=self._poll_status).pack(
            anchor="e", pady=(8, 0)
        )

    def _build_discord(self, parent: Any) -> None:
        inner = self._card(parent, "Discord helper (Glitch Factor)")
        box = ctk.CTkTextbox(inner, height=160, fg_color="#121A24")
        box.pack(fill="x")
        box.insert("1.0", be.get_discord_helper_text())
        box.configure(state="disabled")
        ctk.CTkButton(
            inner,
            text="Copy commands",
            fg_color="#2A3544",
            command=lambda: self._copy(be.get_discord_helper_text(), "Copied Discord helper text."),
        ).pack(anchor="e", pady=(8, 0))

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
        if getattr(self, "host_protect_var", None) is not None:
            s.host_protect = bool(self.host_protect_var.get())
        if getattr(self, "availability_preset_var", None) is not None:
            _apply_availability_fields(
                s,
                self.availability_preset_var.get(),
                daily_start=self.avail_start_entry.get() if hasattr(self, "avail_start_entry") else "",
                daily_end=self.avail_end_entry.get() if hasattr(self, "avail_end_entry") else "",
            )
        return s

    def _save_settings(self) -> None:
        self.settings = self._collect()
        be.save_config(self.settings)
        hp = "ON" if getattr(self.settings, "host_protect", True) else "OFF"
        avail = be.get_availability_status(self.settings).get("label") or "Always on"
        self.action_lbl.configure(
            text=(
                "Saved your offer caps locally (this worker only). "
                f"Host GPU safety {hp}. Schedule: {avail}"
            ),
            text_color=OK_GREEN,
        )
        if hasattr(self, "availability_status_lbl"):
            self._update_availability_status_lbl()

    def _refresh_main_cloudflare(self) -> None:
        if not hasattr(self, "main_cloudflare_status_lbl"):
            return
        try:
            status = be.cloudflare_status()
            if status.get("public_active"):
                text = f"Cloudflare ON ({status.get('mode')}) — {status.get('portal_path')}"
                color = OK_GREEN
            elif status.get("named_config_present"):
                text = "Named tunnel config found — enter the hostname and launch it."
                color = OK_GREEN
            elif status.get("tool_installed"):
                text = "Helper installed — publish a Quick Tunnel or create a named tunnel."
                color = OK_GREEN
            else:
                text = "Helper not installed — Cloudflare is optional and host-controlled."
                color = MUTED
            self.main_cloudflare_status_lbl.configure(text=text, text_color=color)
        except Exception as exc:  # noqa: BLE001
            self.main_cloudflare_status_lbl.configure(text=f"Cloudflare status unavailable: {exc}", text_color=WARN)

    def _open_cloudflare_guide_main(self) -> None:
        result = be.open_cloudflare_guide()
        self.action_lbl.configure(
            text=result.get("message") or f"Opened {result.get('path') or 'Cloudflare guide'}",
            text_color=OK_GREEN if result.get("ok") else WARN,
        )

    def _main_cloudflare_install(self) -> None:
        self.main_cloudflare_status_lbl.configure(text="Installing Cloudflare helper…", text_color=ACCENT)

        def work() -> None:
            try:
                result = be.install_cloudflared()
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "message": f"Cloudflare install error: {exc}"}
            self.app.post_ui(lambda: self._main_cloudflare_result(result))

        threading.Thread(target=work, daemon=True).start()

    def _main_cloudflare_named(self) -> None:
        hostname = self.main_cloudflare_hostname.get().strip()
        tunnel_name = self.main_cloudflare_tunnel_name.get().strip() or "gpu-pool"
        if not hostname:
            self.main_cloudflare_status_lbl.configure(text="Enter a Cloudflare-managed hostname first.", text_color=WARN)
            return
        result = be.launch_cloudflare_named_setup(hostname=hostname, tunnel_name=tunnel_name, launch=True)
        self.main_cloudflare_status_lbl.configure(
            text=result.get("message") or "Named Cloudflare setup opened in a separate window.",
            text_color=ACCENT if result.get("ok") else WARN,
        )
        self.action_lbl.configure(text=result.get("message") or "Cloudflare setup started.", text_color=ACCENT if result.get("ok") else WARN)
        self.after(4000, self._refresh_main_cloudflare)

    def _main_cloudflare_quick(self) -> None:
        self.main_cloudflare_status_lbl.configure(text="Starting Cloudflare Quick Tunnel…", text_color=ACCENT)

        def work() -> None:
            try:
                result = be.publish_cloudflare(mode="quick", open_browser=True)
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "message": f"Cloudflare quick-link error: {exc}"}
            self.app.post_ui(lambda: self._main_cloudflare_result(result))

        threading.Thread(target=work, daemon=True).start()

    def _main_cloudflare_result(self, result: dict[str, Any]) -> None:
        ok = bool(result.get("ok"))
        portal = result.get("portal_path") or ""
        message = result.get("message") or ("Cloudflare ready" if ok else "Cloudflare action failed")
        if ok and portal and hasattr(self, "connect_portal"):
            self._set_entry(self.connect_portal, str(portal))
        self.main_cloudflare_status_lbl.configure(
            text=f"{message}{' — ' + str(portal) if portal else ''}",
            text_color=OK_GREEN if ok else WARN,
        )
        self.action_lbl.configure(text=message, text_color=OK_GREEN if ok else WARN)
        self._refresh_main_cloudflare()

    def _open_portal(self) -> None:
        url = self.portal_entry.get().strip()
        if not url:
            resolved = be.resolve_portal_url()
            url = resolved.get("url") or DEFAULT_LOCAL_PORTAL_URL
            self.portal_entry.delete(0, "end")
            self.portal_entry.insert(0, url)
        s = self._collect()
        s.portal_url = url
        be.save_config(s)
        result = be.open_portal_url(url)
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
            self.app.post_ui(lambda: self._apply_scheduler_test_label(self.test_lbl, result, short=True))

        threading.Thread(target=work, daemon=True).start()

    def _test_utilize_scheduler(self) -> None:
        if not hasattr(self, "utilize_conn_lbl"):
            return
        url = self.utilize_sched.get().strip() if hasattr(self, "utilize_sched") else ""
        self.utilize_conn_lbl.configure(text="Testing Tailscale/LAN scheduler…", text_color=MUTED)

        def work() -> None:
            result = be.test_scheduler(url or None)
            self.app.post_ui(lambda: self._apply_scheduler_test_label(self.utilize_conn_lbl, result))

        threading.Thread(target=work, daemon=True).start()

    def _test_connect_scheduler(self) -> None:
        if not hasattr(self, "connect_status_lbl"):
            return
        url = self.connect_sched.get().strip() if hasattr(self, "connect_sched") else ""
        self.connect_status_lbl.configure(text="Testing Tailscale/LAN scheduler…", text_color=MUTED)

        def work() -> None:
            result = be.test_scheduler(url or None)
            self.app.post_ui(lambda: self._apply_scheduler_test_label(self.connect_status_lbl, result))

        threading.Thread(target=work, daemon=True).start()

    def _apply_scheduler_test_label(self, label: Any, result: dict[str, Any], *, short: bool = False) -> None:
        ok = bool(result.get("ok"))
        if ok:
            text = f"Connected · {result.get('url') or ''}"
            if short:
                text = "Connected (Tailscale/LAN)"
        else:
            hint = (result.get("hint") or "").splitlines()
            text = hint[0] if hint else "Cannot reach scheduler — install/login Tailscale + join the private pool network"
            if short:
                text = "No Tailscale path yet"
        label.configure(text=text, text_color=OK_GREEN if ok else DANGER)
        # Keep Utilize / Connect fields aligned with the URL that worked
        if ok and result.get("url"):
            if hasattr(self, "utilize_sched") and label is getattr(self, "utilize_conn_lbl", None):
                self._set_entry(self.utilize_sched, str(result["url"]))
            if hasattr(self, "connect_sched") and label is getattr(self, "connect_status_lbl", None):
                self._set_entry(self.connect_sched, str(result["url"]))

    def _join(self) -> None:
        if self.app._busy:
            return
        self.app._busy = True
        self.action_lbl.configure(text="Starting worker…", text_color=MUTED)
        settings = self._collect()
        be.save_config(settings)

        def work() -> None:
            result = be.start_worker(settings, wait_online_sec=10.0)
            self.app.post_ui(lambda: self._join_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _join_done(self, result: dict[str, Any]) -> None:
        self.app._busy = False
        ok = bool(result.get("ok"))
        msg = result.get("message") or ("Joined" if ok else "Failed")
        if result.get("fix") and not ok:
            msg = f"{msg} — Copy log / Submit diagnostics"
        diag = result.get("diagnostics") or {}
        if not ok and diag.get("path"):
            msg = f"{msg} · log {diag['path']}"
        self.action_lbl.configure(text=msg, text_color=OK_GREEN if ok else DANGER)
        self._poll_status()

    def _leave(self) -> None:
        if self.app._busy:
            return
        self.app._busy = True
        self.action_lbl.configure(text="Stopping worker…", text_color=MUTED)

        def work() -> None:
            result = be.stop_worker()
            self.app.post_ui(lambda: self._leave_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _leave_done(self, result: dict[str, Any]) -> None:
        self.app._busy = False
        self.action_lbl.configure(
            text=result.get("message") or "Left pool",
            text_color=OK_GREEN if result.get("ok") else DANGER,
        )
        self._poll_status()

    def _copy(self, text: str, msg: str = "Copied.") -> None:
        self.clipboard_clear()
        self.clipboard_append(text)
        if hasattr(self, "action_lbl"):
            self.action_lbl.configure(text=msg, text_color=OK_GREEN)
        if hasattr(self, "utilize_lbl"):
            self.utilize_lbl.configure(text=msg, text_color=OK_GREEN)
        if hasattr(self, "connect_lbl"):
            self.connect_lbl.configure(text=msg, text_color=OK_GREEN)

    def _copy_sched_url(self) -> None:
        url = self.connect_sched.get().strip() or DEFAULT_SCHEDULER_URL
        self._copy(url, "Copied GPU_SWARM_SCHEDULER_URL.")

    def _copy_portal_url(self) -> None:
        url = self.connect_portal.get().strip() or DEFAULT_PORTAL_URL
        self._copy(url, "Copied portal URL.")

    def _open_doc(self, path: Any) -> None:
        result = be.open_repo_doc(path)
        self.connect_lbl.configure(
            text=result.get("message") or "",
            text_color=OK_GREEN if result.get("ok") else DANGER,
        )

    def _copy_agent_cmd(self) -> None:
        url = self.connect_sched.get().strip() if hasattr(self, "connect_sched") else ""
        url = url or DEFAULT_SCHEDULER_URL
        cmd = (
            f"set GPU_SWARM_SCHEDULER_URL={url}\n"
            "python -m gpu_swarm utilize status\n"
            "python -m gpu_swarm utilize probe --wait\n"
            "python -m gpu_swarm utilize cuda --wait\n"
            "python examples\\coding_agent_pool.py --job probe\n"
            "python examples\\coding_agent_pool.py --job pytorch_cuda_probe --matrix-size 1024\n"
        )
        self._copy(cmd, "Copied env + utilize CLI + example commands.")

    def _open_ts_portal(self) -> None:
        url = self.connect_portal.get().strip() or DEFAULT_PORTAL_URL
        result = be.open_portal_url(url)
        self.connect_lbl.configure(
            text=result.get("message") or url,
            text_color=OK_GREEN if result.get("ok") else WARN,
        )

    def _refresh_connect_snippets(self) -> None:
        url = ""
        if hasattr(self, "connect_sched"):
            url = self.connect_sched.get().strip()
        if not url and hasattr(self, "sched_entry"):
            url = self.sched_entry.get().strip()
        url = url or (self.settings.scheduler_url or DEFAULT_SCHEDULER_URL)
        if hasattr(self, "connect_sched"):
            self.connect_sched.delete(0, "end")
            self.connect_sched.insert(0, url)
        hints = be.get_portal_hints()
        portal = hints.get("tailscale_url") or DEFAULT_PORTAL_URL
        if hints.get("reachable") and hints.get("url"):
            # Prefer live URL; still show Tailscale for remote friends
            if "100.85." in str(hints.get("url")):
                portal = hints["url"]
        if hasattr(self, "connect_portal"):
            self.connect_portal.delete(0, "end")
            self.connect_portal.insert(0, portal)
        text = be.get_connect_from_code_text(url)
        if hasattr(self, "connect_box"):
            self.connect_box.delete("1.0", "end")
            self.connect_box.insert("1.0", text)

    def _scheduler_url_for_local_endpoint(self) -> str:
        if hasattr(self, "connect_sched"):
            url = self.connect_sched.get().strip()
            if url:
                return url
        if hasattr(self, "sched_entry"):
            url = self.sched_entry.get().strip()
            if url:
                return url
        return (self.settings.scheduler_url or DEFAULT_SCHEDULER_URL).rstrip("/")

    def _refresh_workspace(self) -> None:
        if not hasattr(self, "workspace_status_lbl"):
            return

        def work() -> None:
            try:
                st = be.workspace_status()
                plan = be.workspace_resource_plan()
            except Exception as exc:  # noqa: BLE001
                st = {"ok": False, "message": str(exc), "vm_status": "error"}
                plan = {}
            self.app.post_ui(lambda: self._render_workspace(st, plan))

        threading.Thread(target=work, daemon=True).start()

    def _render_workspace(self, st: dict[str, Any], plan: dict[str, Any] | None = None) -> None:
        if not hasattr(self, "workspace_status_lbl"):
            return
        plan = plan or st.get("plan") or {}
        mapping = str(plan.get("mapping") or st.get("message") or "")
        if hasattr(self, "workspace_plan_lbl"):
            offer = plan.get("offer") or {}
            self.workspace_plan_lbl.configure(
                text=(
                    f"Offer → VM: {plan.get('cpus', '?')} CPUs · "
                    f"{plan.get('memory_mb', '?')} MiB RAM · "
                    f"display VRAM {plan.get('display_vram_mb', 64)} MiB\n"
                    f"Contribute CPU {offer.get('max_cpu_percent', '?')}% · "
                    f"RAM cap {offer.get('max_ram_mb') or 'auto'} · "
                    f"GPU offer {offer.get('max_vram_mb', 0)} MiB (host worker only)\n"
                    f"{mapping}"
                )
            )
        running = str(st.get("vm_status") or "").lower() == "running"
        color = OK_GREEN if running else (WARN if st.get("ok") else DANGER)
        detail = str(st.get("message") or "")
        gpu = str(st.get("gpu_note") or getattr(be, "ADVANCED_VM_DOC", ""))
        caps = st.get("caps_match")
        caps_bit = ""
        if caps is True:
            caps_bit = " · caps OK"
        elif caps is False:
            caps_bit = " · above offer (halt+start to clamp)"
        self.workspace_status_lbl.configure(
            text=(
                f"Status: {st.get('vm_status', 'unknown')}{caps_bit}\n"
                f"RDP: {st.get('hint_rdp') or 'mstsc /v:127.0.0.1:3390'}  "
                f"(login {st.get('rdp_user', 'vagrant')}/{st.get('rdp_password', 'vagrant')})\n"
                f"{detail}\n"
                f"{st.get('gpu_note') or 'No NVIDIA passthrough into VirtualBox — GPU stays on host worker.'}"
            ),
            text_color=color,
        )
        if hasattr(self, "workspace_halt_btn"):
            self.workspace_halt_btn.configure(state="normal" if running else "disabled")
        _ = gpu  # doc path available via ADVANCED_VM button

    def _open_workspace(self) -> None:
        if hasattr(self, "workspace_status_lbl"):
            self.workspace_status_lbl.configure(
                text="Starting / opening workspace (Hermes agent-vm)…",
                text_color=WARN,
            )
        if hasattr(self, "workspace_open_btn"):
            self.workspace_open_btn.configure(state="disabled")

        def work() -> None:
            result = be.open_workspace(open_rdp=True, start_if_needed=True)
            self.app.post_ui(lambda: self._workspace_action_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _open_workspace_rdp(self) -> None:
        def work() -> None:
            result = be.open_workspace_rdp()
            self.app.post_ui(
                lambda: self.workspace_status_lbl.configure(
                    text=str(result.get("message") or result),
                    text_color=OK_GREEN if result.get("ok") else DANGER,
                )
                if hasattr(self, "workspace_status_lbl")
                else None,
            )

        threading.Thread(target=work, daemon=True).start()

    def _halt_workspace(self) -> None:
        if hasattr(self, "workspace_status_lbl"):
            self.workspace_status_lbl.configure(text="Halting workspace…", text_color=WARN)
        if hasattr(self, "workspace_halt_btn"):
            self.workspace_halt_btn.configure(state="disabled")

        def work() -> None:
            result = be.halt_workspace()
            self.app.post_ui(lambda: self._workspace_action_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _workspace_action_done(self, result: dict[str, Any]) -> None:
        if hasattr(self, "workspace_open_btn"):
            self.workspace_open_btn.configure(state="normal")
        self._refresh_workspace()
        if hasattr(self, "workspace_status_lbl") and result.get("message"):
            color = OK_GREEN if result.get("ok") else WARN
            # Keep refreshed status; briefly surface action result in plan line if useful
            if hasattr(self, "workspace_plan_lbl") and not result.get("ok"):
                self.workspace_plan_lbl.configure(
                    text=str(result.get("message")),
                    text_color=color,
                )

    def _save_llm_provider(self) -> None:
        if not hasattr(self, "llm_provider_entry"):
            return
        result = be.save_llm_provider_url(self.llm_provider_entry.get())
        if hasattr(self, "llm_model_status_lbl"):
            self.llm_model_status_lbl.configure(
                text=result.get("message") or "Provider setting updated.",
                text_color=OK_GREEN if result.get("ok") else WARN,
            )
        if result.get("ok"):
            self._refresh_llm_catalog()

    def _select_llm_model(self, label: str) -> None:
        entries = getattr(self, "_llm_catalog_entries", [])
        for entry in entries:
            expected = (
                f"{entry.get('model')} · {entry.get('provider') or 'openai-compatible'} · "
                f"{entry.get('worker_name') or 'worker'} · "
                f"{int((entry.get('gpu_group') or {}).get('count') or 0)} GPU(s) · "
                f"{entry.get('mount_state') or 'unknown'}"
            )
            if label == expected:
                self._llm_selected_model = str(entry.get("model") or "")
                if hasattr(self, "llm_model_status_lbl"):
                    self.llm_model_status_lbl.configure(
                        text=f"Selected `{self._llm_selected_model}`; local tools can use the live pool catalog.",
                        text_color=OK_GREEN,
                    )
                return

    def _refresh_llm_catalog(self) -> None:
        if not hasattr(self, "llm_model_status_lbl"):
            return
        self.llm_model_status_lbl.configure(text="Mounted model catalog: refreshing…", text_color=ACCENT)

        def work() -> None:
            result = be.get_llm_catalog()
            self.app.post_ui(lambda: self._render_llm_catalog(result))

        threading.Thread(target=work, daemon=True).start()

    def _render_llm_catalog(self, result: dict[str, Any]) -> None:
        if not hasattr(self, "llm_model_status_lbl"):
            return
        entries = [item for item in (result.get("models") or []) if isinstance(item, dict)]
        self._llm_catalog_entries = entries
        if not result.get("ok"):
            self.llm_model_status_lbl.configure(
                text=f"Mounted model catalog unavailable: {result.get('error') or 'scheduler unreachable'}",
                text_color=WARN,
            )
            self.llm_model_menu.configure(values=["Catalog unavailable"])
            self.llm_model_menu.set("Catalog unavailable")
            return
        if not entries:
            self.llm_model_menu.configure(values=["No online mounted models"])
            self.llm_model_menu.set("No online mounted models")
            self.llm_model_status_lbl.configure(
                text="No online worker is advertising an LLM mount. Run a local provider and wait for worker heartbeat.",
                text_color=MUTED,
            )
            return
        labels = [
            f"{entry.get('model')} · {entry.get('provider') or 'openai-compatible'} · "
            f"{entry.get('worker_name') or 'worker'} · "
            f"{int((entry.get('gpu_group') or {}).get('count') or 0)} GPU(s) · "
            f"{entry.get('mount_state') or 'unknown'}"
            for entry in entries[:50]
        ]
        self.llm_model_menu.configure(values=labels)
        selected = next(
            (label for label in labels if str(self._llm_selected_model) and label.startswith(f"{self._llm_selected_model} ·")),
            labels[0],
        )
        self.llm_model_menu.set(selected)
        self._select_llm_model(selected)
        self.llm_model_status_lbl.configure(
            text=f"{len(entries)} online mounted model route(s). Selection is model-routed; exact model presence is checked again at lease time.",
            text_color=OK_GREEN,
        )

    def _refresh_local_endpoint(self) -> None:
        if not hasattr(self, "local_ep_status_lbl"):
            return

        def work() -> None:
            st = be.local_endpoint_status()
            self.app.post_ui(lambda: self._render_local_endpoint(st))

        threading.Thread(target=work, daemon=True).start()

    def _render_local_endpoint(self, st: dict[str, Any]) -> None:
        if not hasattr(self, "local_ep_status_lbl"):
            return
        openai = str(
            st.get("openai_base")
            or st.get("openai_base_url")
            or getattr(be, "DEFAULT_OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
        )
        if hasattr(self, "local_ep_url"):
            self.local_ep_url.delete(0, "end")
            self.local_ep_url.insert(0, openai)
        available = st.get("available")
        if available is None:
            available = True  # backend stub always tries `python -m gpu_swarm local-endpoint`
        running = bool(st.get("running"))
        health = st.get("health")
        if running and health:
            status = "running"
            detail = "Listening — paste OpenAI base URL into your AI app"
            color = OK_GREEN
        elif running:
            status = "starting"
            detail = "Process up; waiting for /health (see data/local_endpoint.log)"
            color = WARN
        elif not available:
            status = "unavailable"
            detail = str(st.get("detail") or "Local endpoint module/CLI not available yet")
            color = WARN
        else:
            status = "stopped"
            detail = "Stopped — Start to expose the pool as a local AI API"
            color = MUTED
        pid = st.get("pid")
        pid_bit = f"  ·  pid {pid}" if pid else ""
        honesty = str(
            st.get("honesty")
            or st.get("blurb")
            or "Appears as a local AI API for apps — not a physical GPU device."
        )
        self.local_ep_status_lbl.configure(
            text=f"Status: {status}{pid_bit}\n{detail}\n{honesty}",
            text_color=color,
        )
        if hasattr(self, "local_ep_start_btn"):
            self.local_ep_start_btn.configure(
                state="disabled" if (running or not available) else "normal"
            )
        if hasattr(self, "local_ep_stop_btn"):
            self.local_ep_stop_btn.configure(state="normal" if running else "disabled")

    def _start_local_endpoint(self) -> None:
        if hasattr(self, "local_ep_status_lbl"):
            self.local_ep_status_lbl.configure(text="Starting local endpoint…", text_color=WARN)
        if hasattr(self, "local_ep_start_btn"):
            self.local_ep_start_btn.configure(state="disabled")
        sched = self._scheduler_url_for_local_endpoint()

        def work() -> None:
            result = be.start_local_endpoint(scheduler_url=sched)
            self.app.post_ui(lambda: self._local_endpoint_action_done(result, starting=True))

        threading.Thread(target=work, daemon=True).start()

    def _stop_local_endpoint(self) -> None:
        if hasattr(self, "local_ep_status_lbl"):
            self.local_ep_status_lbl.configure(text="Stopping local endpoint…", text_color=WARN)
        if hasattr(self, "local_ep_stop_btn"):
            self.local_ep_stop_btn.configure(state="disabled")

        def work() -> None:
            result = be.stop_local_endpoint()
            self.app.post_ui(lambda: self._local_endpoint_action_done(result, starting=False))

        threading.Thread(target=work, daemon=True).start()

    def _local_endpoint_action_done(self, result: dict[str, Any], *, starting: bool) -> None:
        st = be.local_endpoint_status()
        # Prefer URLs from the start/stop result when present
        for key in ("openai_base", "url", "env_line"):
            if result.get(key):
                st[key] = result[key]
        self._render_local_endpoint(st)
        msg = str(result.get("message") or "")
        ok = bool(result.get("ok"))
        if hasattr(self, "connect_lbl"):
            self.connect_lbl.configure(text=msg, text_color=OK_GREEN if ok else DANGER)
        openai = result.get("openai_base") or result.get("openai_base_url")
        if starting and ok and openai:
            env_line = result.get("env_line") or f"OPENAI_BASE_URL={openai}"
            self._copy(
                f"{openai}\n{env_line}",
                f"Started — copied OpenAI base URL ({openai}).",
            )

    def _copy_local_endpoint_url(self) -> None:
        url = ""
        if hasattr(self, "local_ep_url"):
            url = self.local_ep_url.get().strip()
        if not url:
            st = be.local_endpoint_status()
            url = str(
                st.get("openai_base")
                or getattr(be, "DEFAULT_OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
            )
        env_line = be.get_local_endpoint_env_line() if hasattr(be, "get_local_endpoint_env_line") else f"OPENAI_BASE_URL={url}"
        if url and "OPENAI_BASE_URL=" not in env_line:
            env_line = f"OPENAI_BASE_URL={url}"
        elif url and env_line.startswith("OPENAI_BASE_URL="):
            env_line = f"OPENAI_BASE_URL={url}"
        self._copy(f"{url}\n{env_line}", "Copied OpenAI base URL (+ OPENAI_BASE_URL=…).")

    def _refresh_pool_utilize(self) -> None:
        def work() -> None:
            url = self._scheduler_url_for_jobs()
            st = be.pool_status(url)
            self.app.post_ui(lambda: self._render_pool_utilize(st))

        threading.Thread(target=work, daemon=True).start()

    def _render_pool_utilize(self, st: dict[str, Any]) -> None:
        if not hasattr(self, "pool_box"):
            return
        if st.get("ok"):
            sched_line = f"Scheduler: reachable (Tailscale/LAN)  {st.get('url') or ''}"
        else:
            sched_line = f"Scheduler: not reachable yet  {st.get('url') or ''}"
        lines = [sched_line]
        if st.get("private_network"):
            lines.append(st["private_network"])
        if st.get("error"):
            lines.append(f"Error: {st['error']}")
        if not st.get("ok") and st.get("hint"):
            lines.append("")
            lines.append(st["hint"])
        lines += [
            f"Workers online: {st.get('workers_online', 0)} / {st.get('workers_total', 0)}",
            f"VRAM free/total: {st.get('free_vram_mb', 0)} / {st.get('total_vram_mb', 0)} MiB",
            f"CPU cores: {st.get('cpu_cores', 0)}",
            f"RAM avail/total: {st.get('ram_available_mb', 0)} / {st.get('ram_total_mb', 0)} MiB",
            f"Disk free (ad): {st.get('disk_free_mb', 0)} MiB",
            f"Jobs q/r/c/f: {((st.get('jobs') or {}).get('queued'))}/"
            f"{((st.get('jobs') or {}).get('running'))}/"
            f"{((st.get('jobs') or {}).get('completed'))}/"
            f"{((st.get('jobs') or {}).get('failed'))}",
            "",
            "GPUs:",
        ]
        for g in st.get("gpus") or []:
            lines.append(f"  • {g}")
        lines.append("")
        lines.append("Workers:")
        for w in st.get("workers") or []:
            on = "online" if w.get("online") or str(w.get("status", "")).lower() in ("online", "busy") else "off"
            lines.append(
                f"  [{on}] {w.get('name')}  vram={w.get('free_vram_mb')}/{w.get('total_vram_mb')}  "
                f"cpu={w.get('cpu_cores')}c  ram={w.get('ram_available_mb')}  disk={w.get('disk_free_mb')}"
            )
        if st.get("capacity_note"):
            lines += ["", st["capacity_note"]]
        self.pool_box.delete("1.0", "end")
        self.pool_box.insert("1.0", "\n".join(lines))
        self.pool_lbl.configure(
            text=f"Updated {time.strftime('%H:%M:%S')}",
            text_color=OK_GREEN if st.get("ok") else DANGER,
        )
        if hasattr(self, "utilize_conn_lbl"):
            if st.get("ok"):
                self.utilize_conn_lbl.configure(
                    text=f"Connected · {st.get('url') or ''}",
                    text_color=OK_GREEN,
                )
            else:
                first = ((st.get("hint") or "").splitlines() or ["Cannot reach Tailscale/LAN scheduler yet."])[0]
                self.utilize_conn_lbl.configure(text=first, text_color=DANGER)

    def _submit_utilize(self, job_type: str) -> None:
        if self.app._busy:
            return
        self.app._busy = True
        label = "Run Probe" if job_type == "probe" else "Run CUDA Job"
        if hasattr(self, "utilize_lbl"):
            self.utilize_lbl.configure(text=f"Job status: submitting {label}…", text_color=MUTED)
        url = self._scheduler_url_for_jobs()
        by = self.discord_entry.get().strip() if hasattr(self, "discord_entry") else ""
        if not by and hasattr(self, "name_entry"):
            by = self.name_entry.get().strip()

        def work() -> None:
            submitted = be.submit_job(job_type, scheduler_url=url, submitted_by=by or "desktop-utilize")
            if not submitted.get("ok"):
                self.app.post_ui(lambda: self._utilize_done(submitted, None))
                return
            jid = submitted.get("job_id") or ""
            # Persist URL that accepted the job for status polling
            used = submitted.get("url") or url
            waited = be.wait_for_job(jid, scheduler_url=used, timeout_sec=90.0)
            self.app.post_ui(lambda: self._utilize_done(submitted, waited))

        threading.Thread(target=work, daemon=True).start()

    def _utilize_done(self, submitted: dict[str, Any], waited: dict[str, Any] | None) -> None:
        import json

        self.app._busy = False
        if not submitted.get("ok"):
            err = submitted.get("error") or "Submit failed"
            hint = be.scheduler_reachability_hint(
                ok=False,
                url=self._scheduler_url_for_jobs(),
                error=str(err),
            )
            if hasattr(self, "utilize_lbl"):
                self.utilize_lbl.configure(
                    text="Job status: cannot reach Tailscale/LAN scheduler — install/login Tailscale + join the private pool network.",
                    text_color=DANGER,
                )
            if hasattr(self, "job_box"):
                self.job_box.delete("1.0", "end")
                self.job_box.insert(
                    "1.0",
                    f"{err}\n\n{hint}\n\n{json.dumps(submitted, indent=2, default=str)}",
                )
            return
        self._last_job_id = str(submitted.get("job_id") or "")
        job = (waited or {}).get("job") or submitted.get("job") or {}
        st = job.get("status") or "?"
        ok = st == "completed" or bool((waited or {}).get("ok"))
        msg = f"Job status: {st}  ·  {job.get('job_type') or '?'}  ·  id={self._last_job_id}"
        if waited and waited.get("error") and not ok:
            msg = f"Job status: failed — {waited.get('error')}"
        if submitted.get("discord"):
            msg += f"  ·  Discord: {submitted['discord'].splitlines()[0]}"
        if hasattr(self, "utilize_lbl"):
            self.utilize_lbl.configure(text=msg, text_color=OK_GREEN if ok else (WARN if st == "running" else DANGER))
        if hasattr(self, "job_box"):
            self.job_box.delete("1.0", "end")
            self.job_box.insert("1.0", json.dumps(job, indent=2, default=str))
        self._refresh_pool_utilize()
        self._refresh_home_pool()

    def _poll_last_job(self) -> None:
        import json

        jid = self._last_job_id
        if not jid:
            self.utilize_lbl.configure(text="Job status: no job id yet — Run Probe first.", text_color=WARN)
            return
        url = self._scheduler_url_for_jobs()

        def work() -> None:
            result = be.get_job(jid, scheduler_url=url)
            self.app.post_ui(
                lambda: (
                    self.job_box.delete("1.0", "end"),
                    self.job_box.insert("1.0", json.dumps(result.get("job") or result, indent=2, default=str)),
                    self.utilize_lbl.configure(
                        text=f"Job status: {result.get('status') or result.get('error')}  ·  id={jid}",
                        text_color=OK_GREEN if result.get("status") == "completed" else MUTED,
                    ),
                ),
            )

        threading.Thread(target=work, daemon=True).start()

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
            self.app.post_ui(lambda: self._render_status(status))

        threading.Thread(target=work, daemon=True).start()

    def _render_status(self, status: dict[str, Any]) -> None:
        w = status.get("worker") or {}
        sch = status.get("scheduler") or {}
        ts = status.get("tailscale_ipv4") or "n/a"
        host = status.get("host_resources") or {}
        lines = [
            f"Local worker: {'RUNNING' if w.get('running') else 'stopped'}"
            + (f"  pid={w.get('pid')}" if w.get("pid") else ""),
            f"Connected: {'yes' if w.get('connected') else 'no'}  ·  {w.get('detail') or ''}",
            f"Schedule: {(status.get('availability') or {}).get('label') or w.get('availability_label') or '—'}",
            f"Worker id:   {w.get('worker_id') or '—'}",
            f"Worker name: {w.get('worker_name') or '—'}",
            f"Last heartbeat: {w.get('last_heartbeat') or '—'}",
            f"GPUs advertised: {', '.join(w.get('gpus_advertised') or []) or '—'}",
            f"VRAM free/total (worker view): {w.get('free_vram_mb', 0)} / {w.get('total_vram_mb', 0)} MiB",
            f"CPU cores: {w.get('cpu_cores', 0)}",
            f"RAM avail/total: {w.get('ram_available_mb', 0)} / {w.get('ram_total_mb', 0)} MiB",
            f"Disk free: {w.get('disk_free_mb', 0)} MiB",
            "",
            f"Host (local): RAM {host.get('avail_ram_mb', 0)}/{host.get('total_ram_mb', 0)} MiB  ·  "
            f"Disk {host.get('free_disk_gb', 0)}/{host.get('total_disk_gb', 0)} GiB",
            "",
            (
                f"Scheduler: reachable (Tailscale/LAN)  {sch.get('url') or ''}"
                if sch.get("ok")
                else f"Scheduler: not reachable yet  {sch.get('url') or ''}"
            ),
        ]
        if sch.get("error"):
            lines.append(f"  error: {sch['error']}")
        if not sch.get("ok"):
            lines.append(f"  {be.PRIVATE_NETWORK_BLURB}")
            lines.append("  Fix: install/login Tailscale → join the private pool network → retry Test.")
        data = sch.get("data") or {}
        if data:
            lines.append(
                f"  pool workers online: {data.get('workers_online')} / {data.get('workers_total')}  "
                f"jobs q/r/c: {((data.get('jobs') or {}).get('queued'))}/"
                f"{((data.get('jobs') or {}).get('running'))}/"
                f"{((data.get('jobs') or {}).get('completed'))}"
            )
            lines.append(
                f"  pool CPU {data.get('cpu_cores')}  RAM avail {data.get('ram_available_mb')} MiB  "
                f"disk free {data.get('disk_free_mb')} MiB  "
                f"dedicated RAM {data.get('dedicated_ram_mb')} / disk {data.get('dedicated_disk_mb')}"
            )
        lines += [
            "",
            f"Portal: {status.get('portal_url') or '—'}  ·  invite {PORTAL_INVITE_CODE}",
            f"Tailscale IPv4: {ts}",
            f"Updated: {time.strftime('%H:%M:%S')}",
        ]
        self.status_box.delete("1.0", "end")
        self.status_box.insert("1.0", "\n".join(lines))

        running = bool(w.get("running"))
        self.join_btn.configure(state="disabled" if running else "normal")
        self.leave_btn.configure(state="normal" if running else "disabled")

    def _schedule_poll(self) -> None:
        self._poll_status()

        def tick() -> None:
            self._poll_status()
            if self._mode == "utilize":
                self._refresh_pool_utilize()
            elif self._mode == "home":
                self._refresh_home_pool()
            elif self._mode == "connect":
                self._refresh_local_endpoint()
                # Workspace status spawns Hermes CLI — refresh manually, not every poll tick.
            self.app._poll_after = self.after(4000, tick)

        self.app._poll_after = self.after(4000, tick)


if __name__ == "__main__":
    raise SystemExit(run_app())

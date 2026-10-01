"""
Dashboard
---------
Main application window. Talks ONLY to MonitorController -- never touches
OCR, regex, capture hooks, or threading directly. This keeps the UI simple
and means the detection logic can change without touching this file.
"""

import json
import threading
from datetime import datetime
from tkinter import ttk

import customtkinter as ctk

from monitor import MonitorState

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

STATE_COLORS = {
    "running": "#2fa84f",
    "paused": "#d99a2b",
    "stopped": "#8a8a8a",
}


class Dashboard(ctk.CTk):
    def __init__(self, controller, settings):
        super().__init__()
        self.controller = controller
        self.settings = settings

        self.title("ScreenAegis")
        self.geometry("860x580")
        self.minsize(720, 480)

        self._build_header()
        self._build_stat_cards()
        self._build_controls()
        self._build_activity_table()

        # Wire the controller's callbacks to this window AFTER widgets exist
        self.controller.on_event = self._on_event_threadsafe
        self.controller.on_alert = self._on_alert_threadsafe

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._sync_status()
        self._refresh_stats()
        self._load_recent_events()

    # ---------------- UI construction ----------------

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(header, text="ScreenAegis", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="  Real-time screen privacy protection", text_color="gray60",
                     font=ctk.CTkFont(size=12)).pack(side="left")

        self.status_label = ctk.CTkLabel(header, text="Stopped", font=ctk.CTkFont(size=14))
        self.status_label.pack(side="right")
        self.status_dot = ctk.CTkLabel(header, text="\u25CF", font=ctk.CTkFont(size=20),
                                       text_color=STATE_COLORS["stopped"])
        self.status_dot.pack(side="right", padx=(0, 6))

    def _build_stat_cards(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=10)

        self.stat_vars = {}
        cards = [
            ("captures_today", "Captures Today"),
            ("total_items_masked", "Items Masked"),
            ("recorder_alerts", "Recorder Alerts"),
            ("avg_scan_seconds", "Avg Scan Time (s)"),
        ]
        for key, label in cards:
            card = ctk.CTkFrame(row, corner_radius=10)
            card.pack(side="left", expand=True, fill="both", padx=6)
            val = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=26, weight="bold"))
            val.pack(pady=(14, 0))
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=12), text_color="gray70").pack(pady=(0, 14))
            self.stat_vars[key] = val

    def _build_controls(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 10))

        self.toggle_btn = ctk.CTkButton(row, text="Start Protection", command=self._on_toggle, width=170)
        self.toggle_btn.pack(side="left")

        self.scan_btn = ctk.CTkButton(row, text="Scan Now", command=self._on_scan_now,
                                      width=120, fg_color="gray30", hover_color="gray25")
        self.scan_btn.pack(side="left", padx=10)

        ctk.CTkLabel(row, text="Watches for Print Screen, Win+Shift+S, and known recorder apps.",
                     text_color="gray60", font=ctk.CTkFont(size=11)).pack(side="left", padx=10)

    def _build_activity_table(self):
        wrapper = ctk.CTkFrame(self)
        wrapper.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkLabel(wrapper, text="Recent Activity", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=10, pady=(10, 4))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2a2d2e", fieldbackground="#2a2d2e",
                        foreground="white", rowheight=26, borderwidth=0)
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="white", borderwidth=0)
        style.map("Treeview", background=[("selected", "#144870")])

        columns = ("time", "trigger", "app", "masked", "categories")
        self.tree = ttk.Treeview(wrapper, columns=columns, show="headings", height=10)
        headings = {"time": "Time", "trigger": "Trigger", "app": "App in Focus",
                    "masked": "Items", "categories": "Categories"}
        widths = {"time": 150, "trigger": 110, "app": 140, "masked": 60, "categories": 240}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ---------------- button handlers ----------------

    def _on_toggle(self):
        state = self.controller.state
        if state == MonitorState.STOPPED:
            self.controller.start()
        elif state == MonitorState.RUNNING:
            self.controller.pause()
        elif state == MonitorState.PAUSED:
            self.controller.resume()
        self._sync_status()

    def _on_scan_now(self):
        if self.controller.state == MonitorState.STOPPED:
            return
        # Run off the UI thread -- OCR takes real time and must not freeze the window
        threading.Thread(target=self.controller.trigger_manual_scan, daemon=True).start()

    def _sync_status(self):
        state = self.controller.state
        self.status_dot.configure(text_color=STATE_COLORS[state.value])
        self.status_label.configure(text=state.value.capitalize())

        labels = {
            MonitorState.STOPPED: "Start Protection",
            MonitorState.RUNNING: "Pause Protection",
            MonitorState.PAUSED: "Resume Protection",
        }
        self.toggle_btn.configure(text=labels[state])
        self.scan_btn.configure(state="normal" if state != MonitorState.STOPPED else "disabled")

    # ---------------- thread-safe callback bridges ----------------
    # MonitorController's on_event/on_alert fire on background threads.
    # Tkinter widgets may only be touched from the main thread, so every
    # callback hands off via `.after(0, ...)` before touching any widget.

    def _on_event_threadsafe(self, event):
        self.after(0, lambda: self._handle_event(event))

    def _on_alert_threadsafe(self, alert):
        self.after(0, lambda: self._handle_alert(alert))

    def _handle_event(self, event):
        self._refresh_stats()
        self.tree.insert("", 0, values=(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            event["reason"], event["active_app"],
            event["items_masked"], ", ".join(event["categories"]),
        ))

    def _handle_alert(self, alert):
        self._refresh_stats()
        original = self.status_label.cget("text")
        self.status_label.configure(text=f"Recorder detected: {alert['process_name']}")
        self.after(3000, lambda: self.status_label.configure(text=original))

    # ---------------- data refresh ----------------

    def _refresh_stats(self):
        stats = self.controller.get_stats()
        self.stat_vars["captures_today"].configure(text=str(stats["captures_today"]))
        self.stat_vars["total_items_masked"].configure(text=str(stats["total_items_masked"]))
        self.stat_vars["recorder_alerts"].configure(text=str(stats["recorder_alerts"]))
        self.stat_vars["avg_scan_seconds"].configure(text=str(stats["avg_scan_seconds"] or "-"))

    def _load_recent_events(self):
        for row in self.controller.get_recent_events(20):
            try:
                cats = ", ".join(json.loads(row.get("categories") or "{}").keys())
            except (TypeError, ValueError):
                cats = ""
            self.tree.insert("", "end", values=(row["timestamp"], row["trigger"],
                                                 row["active_app"], row["items_masked"], cats))

    def _on_close(self):
        self.controller.stop()
        self.destroy()

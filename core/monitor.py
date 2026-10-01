"""
Monitor Controller
-------------------
The orchestrator. Ties together CaptureDetector, ProcessWatcher, the
scan_and_mask pipeline, and the logger into ONE object with a simple
lifecycle: start() / pause() / resume() / stop().

This is the seam between the core detection logic and the UI: the
dashboard will only ever talk to THIS class, never to the individual
modules directly. That keeps the UI code simple and lets us change how
detection works internally without touching the UI.

Usage:
    controller = MonitorController(settings_manager,
                                    on_event=my_ui_update_fn,
                                    on_alert=my_ui_alert_fn)
    controller.start()
    ...
    controller.pause()   # stays "running" but ignores triggers -- instant resume
    controller.resume()
    controller.stop()    # fully tears down background threads
"""

import os
import threading
from enum import Enum

from screen_utils import capture_screen
from pipeline import scan_and_mask, save_capture_pair
from capture_detector import CaptureDetector
from process_watcher import ProcessWatcher, get_active_app
import logger

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "captures")


class MonitorState(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class MonitorController:
    def __init__(self, settings, on_event=None, on_alert=None, out_dir=OUT_DIR):
        """
        settings:  a SettingsManager instance
        on_event:  optional function(dict) called after every completed scan
                   -- this is what the dashboard hooks into for live updates
        on_alert:  optional function(dict) called when a blacklisted recorder
                   process is detected
        """
        self.settings = settings
        self.on_event = on_event
        self.on_alert = on_alert
        self.out_dir = out_dir

        self.state = MonitorState.STOPPED
        self._lock = threading.Lock()

        self._detector = None
        self._watcher = None

        logger.init_db()

    # ---------------- lifecycle ----------------

    def start(self):
        with self._lock:
            if self.state != MonitorState.STOPPED:
                return  # already running or paused -- nothing to do

            self._detector = CaptureDetector(
                on_capture=self._handle_capture,
                cooldown=self.settings.get("capture_cooldown", 2.0),
            )
            self._watcher = ProcessWatcher(
                blacklist=self.settings.get("blacklisted_processes", []),
                on_detect=self._handle_recorder,
                interval=self.settings.get("process_scan_interval", 3),
            )
            self._detector.start()
            self._watcher.start()
            self.state = MonitorState.RUNNING

    def pause(self):
        """Threads keep running, but triggers are ignored -- resume() is instant."""
        with self._lock:
            if self.state == MonitorState.RUNNING:
                self.state = MonitorState.PAUSED

    def resume(self):
        with self._lock:
            if self.state == MonitorState.PAUSED:
                self.state = MonitorState.RUNNING

    def stop(self):
        with self._lock:
            if self._detector:
                self._detector.stop()
            if self._watcher:
                self._watcher.stop()
            self._detector = None
            self._watcher = None
            self.state = MonitorState.STOPPED

    def is_active(self):
        """True if scans should actually happen (running, not paused/stopped)."""
        return self.state == MonitorState.RUNNING

    # ---------------- internal callbacks ----------------

    def _handle_capture(self, reason):
        if not self.is_active():
            return  # paused or stopped -- ignore this trigger entirely

        active_app = get_active_app()
        frame = capture_screen()
        result = scan_and_mask(frame, self.settings.enabled_categories())

        _, masked_path = save_capture_pair(
            frame, result["masked"], self.out_dir,
            save_original=self.settings.get("save_original_screenshots", True),
        )
        logger.log_detection(reason, active_app, result["flagged"],
                             result["timings"], masked_path)

        event = {
            "reason": reason,
            "active_app": active_app,
            "items_masked": len(result["flagged"]),
            "categories": sorted({f["category"] for f in result["flagged"]}),
            "timings": result["timings"],
            "masked_path": masked_path,
        }
        if self.on_event:
            self.on_event(event)

    def _handle_recorder(self, name, pid):
        if not self.is_active():
            return
        logger.log_process_event(name, pid)
        if self.on_alert:
            self.on_alert({"process_name": name, "pid": pid})

    # ---------------- data access for the UI ----------------

    def get_stats(self):
        return logger.get_stats()

    def get_recent_events(self, limit=20):
        return logger.get_recent_detections(limit)

    def trigger_manual_scan(self):
        """Lets the UI have a 'Scan Now' button, bypassing the key hook."""
        self._handle_capture("manual (dashboard)")

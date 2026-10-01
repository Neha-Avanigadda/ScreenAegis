"""
Process Watcher
---------------
1. ProcessWatcher  - background thread that scans running processes and fires a
                     callback when a blacklisted screen recorder (OBS, Camtasia...)
                     newly appears. Detect + warn + log only -- it never kills
                     processes.
2. get_active_app() - name of the program currently in focus (for the log).
"""

import platform
import threading
import time

import psutil


def _clean(name):
    """'OBS64.exe' -> 'obs64' so blacklist matching is case/extension-insensitive."""
    name = (name or "").lower()
    return name[:-4] if name.endswith(".exe") else name


class ProcessWatcher:
    def __init__(self, blacklist, on_detect, interval=3):
        """
        blacklist: iterable of process names (e.g. ["obs64", "camtasia"])
        on_detect: function(process_name, pid) called ONCE per new recorder process
        interval:  seconds between scans
        """
        self.blacklist = {_clean(n) for n in blacklist}
        self.on_detect = on_detect
        self.interval = interval
        self._seen_pids = set()
        self._running = False
        self._thread = None

    def scan_once(self):
        """Returns a list of (name, pid) for blacklisted processes currently running."""
        found = []
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                if _clean(proc.info["name"]) in self.blacklist:
                    found.append((proc.info["name"], proc.info["pid"]))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return found

    def _loop(self):
        while self._running:
            current = self.scan_once()
            current_pids = {pid for _, pid in current}
            for name, pid in current:
                if pid not in self._seen_pids:      # only alert on NEW processes
                    self.on_detect(name, pid)
            self._seen_pids = current_pids           # forgets closed ones, so a restart re-alerts
            time.sleep(self.interval)

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False


def get_active_app():
    """Name of the foreground application, or 'unknown' if it can't be determined."""
    if platform.system() != "Windows":
        return "unknown"
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return psutil.Process(pid.value).name()
    except Exception:
        return "unknown"

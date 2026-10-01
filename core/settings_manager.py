"""
Settings Manager
----------------
Loads / saves user preferences from data/settings.json.
Any missing key falls back to DEFAULT_SETTINGS, so the app never crashes
because of an old or hand-edited settings file.
"""

import copy
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(BASE_DIR, "..", "data", "settings.json")

DEFAULT_SETTINGS = {
    "first_run": True,                 # UI uses this to show the welcome screen once
    "protection_enabled": True,
    "capture_cooldown": 2.0,           # seconds between triggers
    "save_original_screenshots": True, # keep True for demos; False in real use (privacy)
    "process_scan_interval": 3,        # seconds between recorder-process scans

    # Turn individual detectors on/off (names match pattern_matcher categories)
    "detect_categories": {
        "CREDIT_CARD": True,
        "CREDIT_CARD_OR_ID": True,
        "SSN_OR_ID": True,
        "EMAIL": True,
        "PHONE": True,
        "KEYWORD_MATCH": True,
    },

    # Screen-recording / capture tools to watch for (lowercase, no .exe needed)
    "blacklisted_processes": [
        "obs64", "obs32", "obs",
        "camtasia", "camrecorder",
        "bandicam", "sharex",
        "snagiteditor", "snagit32",
        "screenpresso", "flashbackrecorder",
    ],

    # Used by the Notifier module (later stage)
    "alerts": {
        "email_enabled": False,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender": "",
        "app_password": "",
        "recipient": "",
    },
}


def _deep_merge(defaults, loaded):
    """Recursively overlays `loaded` on top of `defaults`."""
    merged = copy.deepcopy(defaults)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class SettingsManager:
    def __init__(self, path=DEFAULT_PATH):
        self.path = os.path.abspath(path)
        self.data = self.load()

    def load(self):
        if os.path.isfile(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return _deep_merge(DEFAULT_SETTINGS, json.load(f))
            except (json.JSONDecodeError, OSError):
                print("[settings] settings.json unreadable, using defaults")
        return copy.deepcopy(DEFAULT_SETTINGS)

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get(self, dotted_key, default=None):
        """get('alerts.email_enabled') -> value"""
        node = self.data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted_key, value, autosave=True):
        """set('detect_categories.EMAIL', False)"""
        parts = dotted_key.split(".")
        node = self.data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
        if autosave:
            self.save()

    def enabled_categories(self):
        """Set of category names currently switched on."""
        return {k for k, v in self.data["detect_categories"].items() if v}

    def reset(self):
        self.data = copy.deepcopy(DEFAULT_SETTINGS)
        self.save()

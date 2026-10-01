"""
main.py - Application entry point
----------------------------------
Run this from the PROJECT ROOT (the folder containing core/ and ui/):

    python main.py
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "core"))
sys.path.insert(0, os.path.join(BASE_DIR, "ui"))

from settings_manager import SettingsManager
from monitor import MonitorController
from dashboard import Dashboard


def main():
    settings = SettingsManager()
    controller = MonitorController(settings)  # on_event/on_alert wired by Dashboard itself
    app = Dashboard(controller, settings)
    app.mainloop()


if __name__ == "__main__":
    main()

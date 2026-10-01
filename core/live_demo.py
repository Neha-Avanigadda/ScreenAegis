"""
Live Demo (Stage D: now driven by MonitorController)
------------------------------------------------------
Run from inside the core folder:

    python live_demo.py          # watch for PrtScn / Win+Shift+S and recorder apps
    python live_demo.py --now    # trigger one manual scan immediately (testing)
    python live_demo.py --stats  # print summary of everything logged so far

Commands while running: type 'p' + Enter to pause, 'r' + Enter to resume,
'q' + Enter to quit.
"""

import sys
import threading

from settings_manager import SettingsManager
from monitor import MonitorController
import logger


def on_event(e):
    print(f"\n[!] Capture via {e['reason']}  (app: {e['active_app']})")
    print(f"    Masked {e['items_masked']} item(s): {e['categories']}")
    print(f"    Scan time: {e['timings']['total']}s  ->  {e['masked_path']}")


def on_alert(a):
    print(f"\n[ALERT] Screen recorder running: {a['process_name']} (pid {a['pid']})")


def print_stats():
    s = logger.get_stats()
    print("\n=== ScreenAegis summary ===")
    print(f"Captures detected : {s['total_captures']}  (today: {s['captures_today']})")
    print(f"Items masked      : {s['total_items_masked']}")
    print(f"By category       : {s['by_category']}")
    print(f"Avg scan time     : {s['avg_scan_seconds']} s")
    print(f"Recorder alerts   : {s['recorder_alerts']}")
    print(f"Last detection    : {s['last_detection']}")


def main():
    settings = SettingsManager()
    controller = MonitorController(settings, on_event=on_event, on_alert=on_alert)

    if "--stats" in sys.argv:
        print_stats()
        return

    controller.start()

    if "--now" in sys.argv:
        controller.trigger_manual_scan()
        controller.stop()
        return

    print("ScreenAegis is watching. Press Print Screen or Win+Shift+S to test.")
    print("Type 'p'=pause, 'r'=resume, 'q'=quit, then Enter.")

    def input_loop():
        for line in sys.stdin:
            cmd = line.strip().lower()
            if cmd == "p":
                controller.pause()
                print(f"[state] {controller.state.value}")
            elif cmd == "r":
                controller.resume()
                print(f"[state] {controller.state.value}")
            elif cmd == "q":
                controller.stop()
                print_stats()
                return

    input_loop()


if __name__ == "__main__":
    main()

"""
Capture Detector
----------------
Listens globally for screenshot shortcuts and fires a callback:
    - Print Screen  (also Alt+PrtScn, Ctrl+PrtScn)
    - Win + Shift + S   (Windows Snipping Tool)

IMPORTANT: this DETECTS the key press; it cannot cancel it. The OS will still
take its own screenshot. That is why the on-screen Overlay Shield (later stage)
matters -- it hides the data BEFORE the capture happens.
"""

import threading
import time


class CaptureDetector:
    def __init__(self, on_capture, cooldown=2.0):
        """
        on_capture: function(reason: str) called when a capture shortcut fires
        cooldown:   seconds to ignore repeat triggers (one keypress can
                    generate several events, e.g. press + release)
        """
        self.on_capture = on_capture
        self.cooldown = cooldown
        self._pressed = set()
        self._last_trigger = 0.0
        self._listener = None

    # ---------- pure logic (testable without a keyboard) ----------

    def handle_press(self, name):
        self._pressed.add(name)

        if name == "print_screen":
            self._trigger("PrintScreen")
        elif name == "s" and "cmd" in self._pressed and "shift" in self._pressed:
            self._trigger("Win+Shift+S")

    def handle_release(self, name):
        # Windows often reports Print Screen ONLY on key-up, so trigger here too.
        # The cooldown stops a press+release pair from firing twice.
        if name == "print_screen":
            self._trigger("PrintScreen")
        self._pressed.discard(name)

    def _trigger(self, reason):
        now = time.time()
        if now - self._last_trigger < self.cooldown:
            return
        self._last_trigger = now
        # Run on a worker thread so OCR never blocks the keyboard listener
        threading.Thread(target=self.on_capture, args=(reason,), daemon=True).start()

    # ---------- pynput wiring ----------

    @staticmethod
    def _normalize(key):
        from pynput import keyboard as kb

        if key == kb.Key.print_screen:
            return "print_screen"
        if key in (kb.Key.cmd, kb.Key.cmd_l, kb.Key.cmd_r):
            return "cmd"
        if key in (kb.Key.shift, kb.Key.shift_l, kb.Key.shift_r):
            return "shift"
        if key in (kb.Key.ctrl, kb.Key.ctrl_l, kb.Key.ctrl_r):
            return "ctrl"
        if key in (kb.Key.alt, kb.Key.alt_l, kb.Key.alt_r):
            return "alt"
        if getattr(key, "vk", None) == 83:  # 'S' key, even when Win/Shift alter the char
            return "s"
        char = getattr(key, "char", None)
        return char.lower() if char else str(key)

    def start(self):
        """Starts listening (non-blocking). Call stop() to end."""
        from pynput import keyboard as kb

        self._listener = kb.Listener(
            on_press=lambda k: self.handle_press(self._normalize(k)),
            on_release=lambda k: self.handle_release(self._normalize(k)),
        )
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()

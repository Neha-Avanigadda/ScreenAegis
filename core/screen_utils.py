"""
Screen Capture Utility
----------------------
Takes a live screenshot and returns it as a numpy array (BGR), the exact
format ocr_engine.py and masking.py already expect.

Uses `mss` instead of pyautogui because it is much faster (~10-20 ms per
grab vs. 100+ ms), which matters when we're racing a capture event.
"""

import mss
import numpy as np
import cv2


def capture_screen(monitor_index=1):
    """
    Grabs the screen.

    Args:
        monitor_index: 1 = primary monitor, 2 = second monitor, ...
                       0 = all monitors stitched together.

    Returns:
        numpy array in BGR format (same as cv2.imread output).
    """
    # A fresh mss instance per call: mss objects are not thread-safe,
    # and our hook callbacks run on worker threads.
    with mss.mss() as sct:
        if monitor_index >= len(sct.monitors):
            monitor_index = 1
        shot = sct.grab(sct.monitors[monitor_index])
        frame = np.array(shot)  # BGRA
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


if __name__ == "__main__":
    img = capture_screen()
    print(f"Captured screen: {img.shape[1]}x{img.shape[0]} px")
    cv2.imwrite("screen_test.png", img)
    print("Saved screen_test.png")

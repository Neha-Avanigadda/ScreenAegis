"""
Pipeline
--------
One function, scan_and_mask(), that runs the whole detection brain:
    image -> OCR -> pattern matching -> masking
and reports how long each step took (useful for your Performance slide).
"""

import os
import time
from datetime import datetime

import cv2

from ocr_engine import extract_text_with_boxes
from pattern_matcher import match_sensitive_data
from masking import mask_image


def scan_and_mask(image, enabled_categories=None):
    """
    Args:
        image: numpy array (BGR) or file path
        enabled_categories: optional set of category names to keep
                            (from SettingsManager.enabled_categories()).
                            None = keep everything.

    Returns:
        dict with:
            masked      - masked image (numpy array)
            flagged     - list of sensitive regions found
            timings     - seconds spent in each step
    """
    t0 = time.perf_counter()
    ocr_results = extract_text_with_boxes(image)
    t1 = time.perf_counter()
    flagged = match_sensitive_data(ocr_results)
    if enabled_categories is not None:
        flagged = [f for f in flagged if f["category"] in enabled_categories]
    t2 = time.perf_counter()
    masked = mask_image(image, flagged)
    t3 = time.perf_counter()

    return {
        "masked": masked,
        "flagged": flagged,
        "timings": {
            "ocr": round(t1 - t0, 3),
            "matching": round(t2 - t1, 3),
            "masking": round(t3 - t2, 3),
            "total": round(t3 - t0, 3),
        },
    }


def save_capture_pair(original, masked, out_dir, save_original=True):
    """Saves masked (and optionally original) screenshot with a timestamp."""
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    orig_path = os.path.join(out_dir, f"{stamp}_original.png")
    masked_path = os.path.join(out_dir, f"{stamp}_masked.png")
    if save_original:
        cv2.imwrite(orig_path, original)
    else:
        orig_path = None
    cv2.imwrite(masked_path, masked)
    return orig_path, masked_path

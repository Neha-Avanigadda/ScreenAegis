"""
Pattern Matcher
---------------
Runs RegEx rules over OCR'd text to flag sensitive data.
Works word-by-word AND on the joined full-text line, because OCR sometimes
splits things like card numbers across multiple "words" due to spacing.
"""

import re

# Each pattern maps to a category label used in logs / UI
PATTERNS = {
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "SSN_OR_ID": re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "PHONE": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"),
}

# Keyword-triggered detection: if these words appear, flag the WHOLE line
# (covers cases like "Password: hunter2" where the password itself has no fixed pattern)
SENSITIVE_KEYWORDS = ["password", "passwd", "otp", "pin", "secret", "api_key", "apikey", "token"]


def match_sensitive_data(ocr_results):
    """
    Checks OCR'd text against known sensitive patterns.

    Two passes are needed:
    1. Per-word check -- catches emails, keywords, anything OCR reads as one token.
    2. Per-line grouped-digit check -- catches things like card numbers, which
       Tesseract frequently splits into separate 4-digit "words" (e.g. "4111",
       "1111", "1111", "1111"). A single-word regex would miss these entirely,
       so we merge consecutive digit-ish words on the same line and re-check.

    Args:
        ocr_results: output of ocr_engine.extract_text_with_boxes()

    Returns:
        List of dicts: same shape as ocr_results, but only the sensitive
        ones, each tagged with a "category" field. Grouped matches (pass 2)
        include every word box that made up the match, so masking covers
        the full sequence.
    """
    flagged = []
    already_flagged_ids = set()

    # --- Pass 1: per-word check ---
    for idx, item in enumerate(ocr_results):
        category = _classify(item["text"])
        if category:
            flagged_item = dict(item)
            flagged_item["category"] = category
            flagged.append(flagged_item)
            already_flagged_ids.add(idx)

    # --- Pass 2: grouped-digit check (catches split-up card/ID numbers) ---
    for group in _group_by_line(ocr_results):
        digit_groups = _find_digit_runs(group)
        for run in digit_groups:
            joined_digits = "".join(w["text"] for w in run if w["text"].isdigit())
            if 13 <= len(joined_digits) <= 16 or len(joined_digits) == 12:
                for w in run:
                    orig_idx = w["_idx"]
                    if orig_idx in already_flagged_ids:
                        continue
                    flagged_item = {k: v for k, v in w.items() if k != "_idx"}
                    flagged_item["category"] = "CREDIT_CARD_OR_ID"
                    flagged.append(flagged_item)
                    already_flagged_ids.add(orig_idx)

    return flagged


def _group_by_line(ocr_results, y_tolerance=10):
    """Groups OCR word items into lines based on similar 'top' (y) position."""
    indexed = [dict(item, _idx=i) for i, item in enumerate(ocr_results)]
    indexed.sort(key=lambda w: (w["top"], w["left"]))

    lines = []
    current_line = []
    current_top = None

    for word in indexed:
        if current_top is None or abs(word["top"] - current_top) <= y_tolerance:
            current_line.append(word)
            current_top = word["top"] if current_top is None else current_top
        else:
            lines.append(current_line)
            current_line = [word]
            current_top = word["top"]

    if current_line:
        lines.append(current_line)

    return lines


def _find_digit_runs(line_words, max_gap_px=40):
    """Within a line, finds consecutive runs of purely-numeric words that sit close together."""
    runs = []
    current_run = []

    for word in line_words:
        is_digit_word = word["text"].replace("-", "").isdigit()
        if is_digit_word:
            if current_run:
                prev = current_run[-1]
                gap = word["left"] - (prev["left"] + prev["width"])
                if gap > max_gap_px:
                    if len(current_run) > 1:
                        runs.append(current_run)
                    current_run = [word]
                else:
                    current_run.append(word)
            else:
                current_run = [word]
        else:
            if len(current_run) > 1:
                runs.append(current_run)
            current_run = []

    if len(current_run) > 1:
        runs.append(current_run)

    return runs


def _classify(text):
    """Returns a category string if text matches a sensitive pattern, else None."""
    lowered = text.lower()

    for keyword in SENSITIVE_KEYWORDS:
        if keyword in lowered:
            return "KEYWORD_MATCH"

    for category, pattern in PATTERNS.items():
        if pattern.search(text):
            return category

    return None


if __name__ == "__main__":
    # Quick manual test
    sample = [
        {"text": "4111111111111111", "left": 10, "top": 10, "width": 100, "height": 20, "conf": 90},
        {"text": "hello@example.com", "left": 10, "top": 40, "width": 120, "height": 20, "conf": 90},
        {"text": "Password:", "left": 10, "top": 70, "width": 80, "height": 20, "conf": 90},
        {"text": "normal", "left": 10, "top": 100, "width": 60, "height": 20, "conf": 90},
    ]
    for r in match_sensitive_data(sample):
        print(r)

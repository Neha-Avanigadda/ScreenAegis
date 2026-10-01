# SentinelEye — Stage A (Core Detection Pipeline)

## What's implemented
- `core/ocr_engine.py` — Tesseract-based OCR, returns text + bounding boxes per word
- `core/pattern_matcher.py` — RegEx + keyword detection for card numbers, emails,
  phone numbers, SSNs/IDs, and password-like keywords. Includes a line-grouping
  fix so multi-word numbers (e.g. "4111 1111 1111 1111") are still caught even
  when Tesseract splits them into separate word tokens.
- `core/masking.py` — draws solid black rectangles over every flagged region.

## Requirements
```
pip install pytesseract opencv-python-headless numpy pillow
```
Also requires the Tesseract OCR binary installed on your system:
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Mac: `brew install tesseract`
- Linux: `sudo apt install tesseract-ocr`

## Run the demo
```
cd core
python3 masking.py ../data/test_image.png ../data/test_image_masked.png
```

## Known limitation (documented for capstone review)
Tesseract sometimes splits long digit sequences (like card numbers) into
several separate "words" due to spacing. A naive per-word regex check misses
these. Fixed via `_group_by_line()` + `_find_digit_runs()` in
pattern_matcher.py, which merges nearby digit-only words on the same line
before re-checking length.

"""
Tesseract Config
----------------
Fixes the most common pytesseract error:
    TesseractNotFoundError: tesseract is not installed or it's not in your PATH

This happens because pytesseract is just a Python wrapper -- it still needs
the actual Tesseract OCR *program* installed separately, and on Windows it's
usually not added to PATH automatically.

Import this file BEFORE using pytesseract anywhere (ocr_engine.py already
does this for you).
"""

import os
import shutil
import platform
import pytesseract

def configure_tesseract():
    # 1. If tesseract is already found on PATH, nothing to do.
    if shutil.which("tesseract"):
        return

    system = platform.system()

    # 2. Common install locations by OS
    candidate_paths = []
    if system == "Windows":
        candidate_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        ]
    elif system == "Darwin":  # macOS
        candidate_paths = [
            "/opt/homebrew/bin/tesseract",   # Apple Silicon Homebrew
            "/usr/local/bin/tesseract",       # Intel Homebrew
        ]
    else:  # Linux
        candidate_paths = [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
        ]

    for path in candidate_paths:
        if os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"[tesseract_config] Using Tesseract at: {path}")
            return

    # 3. Nothing found -- fail loudly with clear install instructions
    raise EnvironmentError(
        "\n\nTesseract OCR binary not found on this system.\n"
        "pytesseract needs the actual Tesseract program installed, not just the Python package.\n\n"
        "Install it:\n"
        "  Windows: https://github.com/UB-Mannheim/tesseract/wiki  (then note the install path)\n"
        "  Mac:     brew install tesseract\n"
        "  Linux:   sudo apt install tesseract-ocr\n\n"
        "If you installed it somewhere non-standard, edit tesseract_config.py and add\n"
        "your exact install path to 'candidate_paths', e.g.:\n"
        r'  r"D:\MyApps\Tesseract-OCR\tesseract.exe"' "\n"
    )


# Run automatically on import
configure_tesseract()

"""
OCR Engine
----------
Wraps pytesseract to extract text AND bounding boxes from an image.
Bounding boxes are essential -- without them we'd know sensitive text
exists on screen, but not WHERE to draw a mask over it.
"""

import cv2

import pytesseract
import numpy as np
import tesseract_config  # auto-configures the Tesseract path — must import before pytesseract is used
# Explicitly point to the installed tesseract.exe 
# (Update this path if you installed Tesseract to a different folder)


def extract_text_with_boxes(image_path_or_array, min_confidence=40):
    """
    Runs OCR on an image and returns a list of detected text blocks.

    Args:
        image_path_or_array: file path (str) OR a numpy array (e.g. from a screenshot)
        min_confidence: skip OCR results below this confidence score (0-100)

    Returns:
        List of dicts: [{"text": str, "left": int, "top": int,
                          "width": int, "height": int, "conf": float}, ...]
    """
    # Load image either from disk or use the array directly (screenshots come as arrays)
    if isinstance(image_path_or_array, str):
        image = cv2.imread(image_path_or_array)
        if image is None:
            raise FileNotFoundError(f"Could not load image: {image_path_or_array}")
    else:
        image = image_path_or_array

    # Tesseract works better on grayscale + thresholded images
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # image_to_data gives us per-word bounding boxes, not just a text blob
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

    results = []
    n_boxes = len(data["text"])
    for i in range(n_boxes):
        text = data["text"][i].strip()
        conf = float(data["conf"][i])

        if text == "" or conf < min_confidence:
            continue

        results.append({
            "text": text,
            "left": data["left"][i],
            "top": data["top"][i],
            "width": data["width"][i],
            "height": data["height"][i],
            "conf": conf,
        })

    return results


def get_full_text(ocr_results):
    """Convenience: joins all detected words back into one string."""
    return " ".join(item["text"] for item in ocr_results)


if __name__ == "__main__":
    # Quick manual test -- run: python3 core/ocr_engine.py <image_path>
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 ocr_engine.py <image_path>")
    else:
        results = extract_text_with_boxes(sys.argv[1])
        for r in results:
            print(r)


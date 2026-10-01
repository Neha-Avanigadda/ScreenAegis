"""
Masking Engine
--------------
Takes an image + a list of flagged (sensitive) OCR regions, and draws
solid black rectangles over them.
"""

import cv2


def mask_image(image_path_or_array, flagged_items, padding=3):
    """
    Draws black rectangles over each flagged region.

    Args:
        image_path_or_array: file path (str) OR numpy array
        flagged_items: output of pattern_matcher.match_sensitive_data()
        padding: extra pixels around each box so text edges are fully covered

    Returns:
        The masked image as a numpy array (does NOT save to disk automatically)
    """
    if isinstance(image_path_or_array, str):
        image = cv2.imread(image_path_or_array)
        if image is None:
            raise FileNotFoundError(f"Could not load image: {image_path_or_array}")
    else:
        image = image_path_or_array.copy()  # don't mutate the original array

    for item in flagged_items:
        x, y = item["left"], item["top"]
        w, h = item["width"], item["height"]

        top_left = (max(0, x - padding), max(0, y - padding))
        bottom_right = (x + w + padding, y + h + padding)

        # -1 thickness = filled rectangle (solid black box)
        cv2.rectangle(image, top_left, bottom_right, (0, 0, 0), thickness=-1)

    return image


def save_masked_image(image, output_path):
    cv2.imwrite(output_path, image)
    return output_path


if __name__ == "__main__":
    # Quick manual test -- run: python3 core/masking.py <image_path> <output_path>
    import sys
    from ocr_engine import extract_text_with_boxes
    from pattern_matcher import match_sensitive_data

    if len(sys.argv) < 3:
        print("Usage: python3 masking.py <input_image> <output_image>")
    else:
        ocr_results = extract_text_with_boxes(sys.argv[1])
        flagged = match_sensitive_data(ocr_results)
        print(f"Flagged {len(flagged)} sensitive region(s):")
        for f in flagged:
            print(f"  [{f['category']}] '{f['text']}'")

        masked = mask_image(sys.argv[1], flagged)
        save_masked_image(masked, sys.argv[2])
        print(f"Saved masked image to {sys.argv[2]}")

"""
Reconstructed ANPR prototype based on the code preserved in the
2021 Smart Parking final project report appendix.

The original logic used:
- image resize
- grayscale conversion
- bilateral filtering
- Canny edge detection
- contour search
- four-corner plate approximation
- masking
- Pytesseract OCR
- optional registration-number comparison

This version removes hard-coded Windows paths and exposes them as
command-line arguments. It does not claim to reproduce missing parts
of the original booking application.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import imutils
import numpy as np
import pandas as pd
import pytesseract


def normalize_plate_text(text: str) -> str:
    """Normalize OCR output for simple registration-number comparison."""
    return "".join(text.upper().split())


def localize_plate(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Return the plate-masked image and the edge image.

    The procedure follows the contour-based logic documented in the report.
    """
    resized = imutils.resize(image, width=500)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, 11, 17, 17)
    edges = cv2.Canny(filtered, 170, 200)

    contours_info = cv2.findContours(
        edges.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = contours_info[0] if len(contours_info) == 2 else contours_info[1]
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:30]

    number_plate_contour = None

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) == 4:
            number_plate_contour = approx
            break

    if number_plate_contour is None:
        raise RuntimeError("No four-corner plate candidate was found.")

    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.drawContours(mask, [number_plate_contour], 0, 255, -1)
    masked = cv2.bitwise_and(resized, resized, mask=mask)

    return masked, edges


def recognize_plate(
    image_path: Path,
    tesseract_path: str | None = None,
) -> tuple[str, np.ndarray, np.ndarray]:
    """Run the reconstructed ANPR pipeline on one image."""
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    masked, edges = localize_plate(image)

    config = "-l eng --oem 1 --psm 3"
    text = pytesseract.image_to_string(masked, config=config).strip()

    return text, masked, edges


def lookup_registration(text: str, csv_path: Path) -> pd.DataFrame:
    """
    Compare OCR text against a CSV column named 'Registration Number'.

    This matches the comparison step described in the original appendix.
    """
    data = pd.read_csv(csv_path)

    required_column = "Registration Number"
    if required_column not in data.columns:
        raise KeyError(
            f"CSV must contain a '{required_column}' column. "
            f"Found: {list(data.columns)}"
        )

    target = normalize_plate_text(text)
    normalized = data[required_column].astype(str).map(normalize_plate_text)

    return data.loc[normalized == target]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconstructed Smart Parking ANPR prototype."
    )
    parser.add_argument("image", type=Path, help="Vehicle image to process")
    parser.add_argument(
        "--tesseract",
        default=None,
        help="Optional path to the Tesseract executable",
    )
    parser.add_argument(
        "--registrations",
        type=Path,
        default=None,
        help="Optional CSV containing a 'Registration Number' column",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory for reconstructed pipeline images",
    )
    args = parser.parse_args()

    text, masked, edges = recognize_plate(args.image, args.tesseract)

    print(f"Detected text: {text!r}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output_dir / "plate_masked.png"), masked)
    cv2.imwrite(str(args.output_dir / "edges.png"), edges)

    if args.registrations:
        matches = lookup_registration(text, args.registrations)
        if matches.empty:
            print("Not registered")
        else:
            print("Registered vehicle")
            print(matches.to_string(index=False))


if __name__ == "__main__":
    main()

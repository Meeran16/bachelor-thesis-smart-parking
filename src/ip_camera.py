"""
Reconstructed IP-camera viewer based on the mobile implementation
snippet preserved in the 2021 Smart Parking project report.
"""

from __future__ import annotations

import argparse
import urllib.request

import cv2
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple IP-camera OpenCV viewer.")
    parser.add_argument(
        "url",
        help="Image-stream URL, for example http://192.168.43.61:8080/",
    )
    args = parser.parse_args()

    while True:
        response = urllib.request.urlopen(args.url)
        image_bytes = np.array(bytearray(response.read()), dtype=np.uint8)
        frame = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)

        if frame is None:
            print("Could not decode frame.")
            continue

        cv2.imshow("IPWebcam", frame)

        # Press q to stop.
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

"""QR decoding with OpenCV. Decoded content is treated strictly as TEXT.
Nothing is opened, fetched, or executed."""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image

MAX_DECODE_PIXELS = 25_000_000


class DecodeError(ValueError):
    pass


@dataclass(frozen=True)
class DecodeResult:
    found: bool
    text: str = ""
    kind: str = ""        # url | wifi | email | phone | sms | text
    message: str = ""


def classify_payload(text: str) -> str:
    lower = text.strip().lower()
    if lower.startswith(("http://", "https://")):
        return "url"
    if lower.startswith("wifi:"):
        return "wifi"
    if lower.startswith("mailto:"):
        return "email"
    if lower.startswith("tel:"):
        return "phone"
    if lower.startswith(("sms:", "smsto:")):
        return "sms"
    return "text"


def decode_image_bytes(data: bytes) -> DecodeResult:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise DecodeError("OpenCV is not installed. Run: pip install -r requirements.txt") from exc

    try:
        probe = Image.open(io.BytesIO(data))
        if probe.size[0] * probe.size[1] > MAX_DECODE_PIXELS:
            raise DecodeError("Image is too large to decode safely.")
        image = Image.open(io.BytesIO(data)).convert("RGB")
    except DecodeError:
        raise
    except Exception as exc:
        raise DecodeError("The file could not be read as an image.") from exc

    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    detector = cv2.QRCodeDetector()

    attempts = [gray]
    # Padding and upscaling help with tight crops and small images.
    attempts.append(cv2.copyMakeBorder(gray, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255))
    h, w = gray.shape
    if max(h, w) < 600:
        attempts.append(cv2.resize(attempts[1], None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST))

    for candidate in attempts:
        text, _points, _ = detector.detectAndDecode(candidate)
        if text:
            return DecodeResult(True, text, classify_payload(text))
    return DecodeResult(False, message="No readable QR code was found in this image.")

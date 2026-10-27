"""Test helper: a genuine QR module matrix from OpenCV's encoder.

Production code gets its matrix from the `qrcode` package (qr_tools.generator.make_matrix).
That package is not available in every test environment, so the rendering tests feed the
renderers a real QR matrix produced by OpenCV instead. The renderers only ever see a
boolean matrix, so the two sources are interchangeable for everything downstream.
"""

from __future__ import annotations

import cv2
import numpy as np

_LEVELS = {"L": cv2.QRCodeEncoder_CORRECT_LEVEL_L, "M": cv2.QRCodeEncoder_CORRECT_LEVEL_M,
           "Q": cv2.QRCodeEncoder_CORRECT_LEVEL_Q, "H": cv2.QRCodeEncoder_CORRECT_LEVEL_H}


def cv2_matrix(payload: str, error_correction: str = "M") -> list[list[bool]]:
    params = cv2.QRCodeEncoder_Params()
    params.correction_level = _LEVELS[error_correction]
    img = cv2.QRCodeEncoder.create(params).encode(payload)
    dark = img < 128
    ys, xs = np.where(dark)
    cropped = dark[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    row = cropped[0]
    run = 0
    while run < len(row) and row[run]:
        run += 1
    module = run / 7.0                                  # the first run of dark pixels is a 7-module finder edge
    n = int(round(cropped.shape[0] / module))
    centres = ((np.arange(n) + 0.5) * module).astype(int)
    return [[bool(cropped[y, x]) for x in centres] for y in centres]


def install(test_case, module="qr_tools.generator") -> None:
    """Make gen.make_matrix use OpenCV for the duration of a test (restored automatically)."""
    from unittest import mock

    def fake(data, error_correction="M"):
        from qr_tools.generator import QRError, build_text_payload
        data = build_text_payload(data)
        try:
            return cv2_matrix(data, error_correction)
        except Exception as exc:  # DataOverflow etc.
            raise QRError("That content is too large for a QR code at this error-correction level.") from exc

    patcher = mock.patch(f"{module}.make_matrix", side_effect=fake)
    patcher.start()
    test_case.addCleanup(patcher.stop)

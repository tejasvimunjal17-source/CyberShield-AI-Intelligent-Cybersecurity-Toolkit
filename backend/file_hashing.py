"""Local file hashing. Files are only read as bytes, never executed or opened
by any other program, and are never sent anywhere from this module."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import BinaryIO

from config import MAX_UPLOAD_BYTES

CHUNK_SIZE = 1024 * 1024  # 1 MiB


class FileTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class HashResult:
    size: int
    sha256: str
    sha1: str
    md5: str


def _new_hashers():
    # sha1/md5 are used only as lookup identifiers, not for security.
    return (
        hashlib.sha256(),
        hashlib.sha1(usedforsecurity=False),
        hashlib.md5(usedforsecurity=False),
    )


def hash_stream(stream: BinaryIO, max_bytes: int = MAX_UPLOAD_BYTES) -> HashResult:
    sha256, sha1, md5 = _new_hashers()
    total = 0
    while True:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise FileTooLargeError(f"File exceeds the {max_bytes // (1024 * 1024)} MB limit.")
        sha256.update(chunk)
        sha1.update(chunk)
        md5.update(chunk)
    return HashResult(total, sha256.hexdigest(), sha1.hexdigest(), md5.hexdigest())


def hash_bytes(data: bytes, max_bytes: int = MAX_UPLOAD_BYTES) -> HashResult:
    import io

    return hash_stream(io.BytesIO(data), max_bytes=max_bytes)

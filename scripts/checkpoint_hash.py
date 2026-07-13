"""One canonical hash contract for human checkpoint Markdown."""
from __future__ import annotations

import hashlib
from pathlib import Path


def normalize_md_text(text: str) -> str:
    return text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").strip()


def md_sha256_text(text: str) -> str:
    return hashlib.sha256(normalize_md_text(text).encode("utf-8")).hexdigest()


def md_sha256_file(path: Path) -> str:
    return md_sha256_text(path.read_text(encoding="utf-8-sig"))

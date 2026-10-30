"""Disk storage uses server-generated keys only, never upload filenames."""

import hashlib
from pathlib import Path
from .config import settings


def path_for(key: str) -> Path:
    root = settings().storage_dir.resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Unsafe storage key")
    return path


def store_pdf(data: bytes) -> tuple[str, str]:
    if len(data) > settings().max_upload_mb * 1024 * 1024:
        raise ValueError("PDF exceeds upload limit")
    if not data.startswith(b"%PDF-"):
        raise ValueError("Only PDF files are accepted")
    digest = hashlib.sha256(data).hexdigest()
    key = f"pdf/{digest}.pdf"
    path = path_for(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # Atomic replacement prevents readers from seeing a partially written PDF.
        temp = path.with_suffix(".tmp")
        temp.write_bytes(data)
        temp.replace(path)
    return digest, key

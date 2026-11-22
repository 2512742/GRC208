"""Evidence file checks: type by content (not by name), size, SHA-256, safe display name.

Allowed: PDF, PNG, JPEG, CSV/TXT, XLSX, DOCX up to 4 MB. The file's first bytes must match its
extension, so a renamed executable ("invoice.pdf" that is really an .exe) is refused. Files are
stored and hashed, never opened or interpreted (PLAN.md decision 2).
"""

from __future__ import annotations

import hashlib
import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

from app.models.records import EVIDENCE_MAX_BYTES

MIME_BY_EXTENSION: dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Office Open XML: a ZIP whose content types list names the main part of the right kind.
_OOXML_MAIN_PART = {".xlsx": "xl/workbook.xml", ".docx": "word/document.xml"}


class EvidenceRejected(ValueError):
    """The upload is not acceptable; the message is safe to show the user."""


@dataclass(frozen=True)
class CheckedFile:
    original_name: str
    mime_type: str
    size_bytes: int
    sha256: str


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def safe_display_name(filename: str) -> str:
    """Keep only the base name, drop control characters, cap the length. Display use only:
    the file is never written to disk under this name."""
    base = PureWindowsPath(PurePosixPath(filename or "").name).name
    base = unicodedata.normalize("NFC", base)
    base = "".join(ch for ch in base if unicodedata.category(ch)[0] != "C").strip(" .")
    base = re.sub(r"\s+", " ", base)
    if not base:
        raise EvidenceRejected("The file needs a name.")
    if len(base) > 255:
        stem, dot, ext = base.rpartition(".")
        base = (stem[: 255 - len(ext) - 1] + "." + ext) if dot else base[:255]
    return base


def _extension(name: str) -> str:
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in MIME_BY_EXTENSION:
        allowed = ", ".join(sorted({e.lstrip(".").upper() for e in MIME_BY_EXTENSION}))
        raise EvidenceRejected(f"File type not allowed. Allowed types: {allowed}.")
    return suffix


def _content_matches(ext: str, content: bytes) -> bool:
    if ext == ".pdf":
        return content.startswith(b"%PDF-")
    if ext == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in (".jpg", ".jpeg"):
        return content.startswith(b"\xff\xd8\xff")
    if ext in (".csv", ".txt"):
        if b"\x00" in content:
            return False
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return False
        return True
    if ext in _OOXML_MAIN_PART:
        if not content.startswith(b"PK\x03\x04"):
            return False
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = set(archive.namelist())
        except zipfile.BadZipFile:
            return False
        return "[Content_Types].xml" in names and _OOXML_MAIN_PART[ext] in names
    return False  # pragma: no cover  (extension list and checks are kept in step)


def check_evidence(filename: str, content: bytes) -> CheckedFile:
    name = safe_display_name(filename)
    ext = _extension(name)
    size = len(content)
    if size == 0:
        raise EvidenceRejected("The file is empty.")
    if size > EVIDENCE_MAX_BYTES:
        raise EvidenceRejected(
            f"The file is {size / 1_048_576:.1f} MB; the limit is "
            f"{EVIDENCE_MAX_BYTES // 1_048_576} MB."
        )
    if not _content_matches(ext, content):
        raise EvidenceRejected(f"The file's content is not a valid {ext.lstrip('.').upper()} file.")
    return CheckedFile(
        original_name=name,
        mime_type=MIME_BY_EXTENSION[ext],
        size_bytes=size,
        sha256=sha256_hex(content),
    )

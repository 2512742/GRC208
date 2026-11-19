"""P2 evidence checks: allowed types by content, size limit, hashing, safe names (T27)."""

from __future__ import annotations

import hashlib
import io
import zipfile

import pytest

from app.models.records import EVIDENCE_MAX_BYTES
from app.services.evidence import EvidenceRejected, check_evidence, safe_display_name

PDF = b"%PDF-1.7\n1 0 obj<<>>endobj\n%%EOF"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
EXE = b"MZ\x90\x00" + b"\x00" * 60


def ooxml(main_part: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(main_part, "<x/>")
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("name", "content", "mime"),
    [
        ("scan.pdf", PDF, "application/pdf"),
        ("shot.PNG", PNG, "image/png"),
        ("photo.jpeg", JPEG, "image/jpeg"),
        ("photo.jpg", JPEG, "image/jpeg"),
        ("assets.csv", b"name,type\nWallet ledger,database\n", "text/csv"),
        ("notes.txt", "Patched on 3 Dec — verified.".encode(), "text/plain"),
        (
            "plan.xlsx",
            ooxml("xl/workbook.xml"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        (
            "memo.docx",
            ooxml("word/document.xml"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    ],
)
def test_allowed_types_accepted_and_hashed(name: str, content: bytes, mime: str) -> None:
    checked = check_evidence(name, content)
    assert checked.mime_type == mime
    assert checked.size_bytes == len(content)
    assert checked.sha256 == hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("tool.exe", EXE, "File type not allowed"),
        ("invoice.pdf", EXE, "not a valid PDF"),  # renamed executable
        ("image.png", PDF, "not a valid PNG"),
        ("data.csv", b"a,b\x00c", "not a valid CSV"),
        ("data.csv", b"\xff\xfe\xfa", "not a valid CSV"),
        ("sheet.xlsx", ooxml("word/document.xml"), "not a valid XLSX"),  # a .docx renamed
        ("sheet.xlsx", b"PK\x03\x04garbage", "not a valid XLSX"),
        ("script.sh", b"#!/bin/sh", "File type not allowed"),
        ("archive.zip", ooxml("xl/workbook.xml"), "File type not allowed"),
        ("noext", PDF, "File type not allowed"),
        ("empty.pdf", b"", "empty"),
    ],
)
def test_t27_bad_files_rejected_with_a_clear_reason(
    name: str, content: bytes, message: str
) -> None:
    with pytest.raises(EvidenceRejected, match=message):
        check_evidence(name, content)


def test_t27_over_4_mb_rejected_and_exactly_4_mb_accepted() -> None:
    at_limit = PDF + b"0" * (EVIDENCE_MAX_BYTES - len(PDF))
    assert check_evidence("big.pdf", at_limit).size_bytes == EVIDENCE_MAX_BYTES
    with pytest.raises(EvidenceRejected, match="limit is 4 MB"):
        check_evidence("too-big.pdf", at_limit + b"0")


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("C:\\Users\\ocen\\Desktop\\scan.pdf", "scan.pdf"),
        ("  report\t final.pdf ", "report final.pdf"),
        ("bad\x00name\x1f.pdf", "badname.pdf"),
    ],
)
def test_display_names_are_made_safe(given: str, expected: str) -> None:
    assert safe_display_name(given) == expected


def test_long_names_keep_their_extension() -> None:
    name = safe_display_name("a" * 400 + ".pdf")
    assert len(name) == 255 and name.endswith(".pdf")


@pytest.mark.parametrize("given", ["", "   ", "...", "\x00\x01"])
def test_nameless_files_rejected(given: str) -> None:
    with pytest.raises(EvidenceRejected, match="needs a name"):
        safe_display_name(given)

"""JSON backup of every table (`python -m app.cli export-backup`).

Version-independent (no pg_dump client/server mismatch, a lesson from the Guardian project's
Render migration). Evidence bytes are base64-encoded. The file holds personal data and password
hashes: keep it out of git (backups/ is git-ignored) and delete it when no longer needed.
"""

from __future__ import annotations

import base64
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlmodel import Session, SQLModel, select

from app.services.clock import now_utc


def _plain(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def export_all(
    session: Session, out_dir: Path, *, with_evidence: bool = True
) -> tuple[Path, dict[str, int]]:
    tables: dict[str, list[dict[str, Any]]] = {}
    for table in SQLModel.metadata.sorted_tables:  # parents before children
        columns = [
            c
            for c in table.columns
            if with_evidence or not (table.name == "evidence" and c.name == "content")
        ]
        rows = session.exec(select(*columns)).mappings().all()  # type: ignore[call-overload]
        tables[table.name] = [{k: _plain(v) for k, v in row.items()} for row in rows]
    created = now_utc()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"risktrack-backup-{created:%Y%m%d-%H%M%S}.json"
    payload = {
        "created_at_utc": created.isoformat(),
        "with_evidence": with_evidence,
        "tables": tables,
    }
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return path, {name: len(rows) for name, rows in tables.items()}

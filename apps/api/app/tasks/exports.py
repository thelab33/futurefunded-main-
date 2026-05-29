from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class ExportResult:
    filename: str
    content_type: str
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "content_type": self.content_type,
            "content": self.content,
        }


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def export_rows_to_csv(
    rows: list[dict[str, Any]],
    *,
    prefix: str = "futurefunded-export",
) -> ExportResult:
    rows = rows or []
    fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else ["empty"]

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()

    if rows:
        for row in rows:
            writer.writerow(row)
    else:
        writer.writerow({"empty": ""})

    return ExportResult(
        filename=f"{prefix}-{_timestamp()}.csv",
        content_type="text/csv",
        content=buffer.getvalue(),
    )

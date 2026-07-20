from __future__ import annotations

import csv
import io
import json
from html.parser import HTMLParser
from typing import Any

SUPPORTED_FORMATS = ("json", "jsonl", "ndjson", "csv", "html")


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "tr":
            self._row = []
        elif tag.lower() in {"th", "td"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"th", "td"} and self._row is not None and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif lowered == "tr" and self._row is not None:
            if any(cell for cell in self._row):
                self.rows.append(self._row)
            self._row = None


def _normalize_row(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("each import record must be an object")
    normalized = {
        str(key).strip(): item
        for key, item in value.items()
        if str(key).strip()
    }
    if not normalized:
        raise ValueError("import record cannot be empty")
    return normalized


def _parse_json(payload_text: str) -> list[dict[str, Any]]:
    value = json.loads(payload_text)
    if isinstance(value, dict) and isinstance(value.get("records"), list):
        value = value["records"]
    if not isinstance(value, list):
        raise ValueError("JSON export must be a list or contain a records list")
    return [_normalize_row(item) for item in value]


def _parse_jsonl(payload_text: str) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(payload_text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL record on line {line_number}") from exc
        records.append(_normalize_row(value))
    return records


def _parse_csv(payload_text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(payload_text))
    if not reader.fieldnames:
        raise ValueError("CSV export requires a header row")
    return [_normalize_row(dict(row)) for row in reader]


def _parse_html(payload_text: str) -> list[dict[str, Any]]:
    parser = _TableParser()
    parser.feed(payload_text)
    if len(parser.rows) < 2:
        raise ValueError("HTML export requires a table header and at least one row")
    headers = [str(item).strip() for item in parser.rows[0]]
    if not all(headers) or len(set(headers)) != len(headers):
        raise ValueError("HTML table headers must be non-empty and unique")
    records = []
    for row_number, row in enumerate(parser.rows[1:], start=2):
        if len(row) != len(headers):
            raise ValueError(f"HTML table row {row_number} has the wrong column count")
        records.append(_normalize_row(dict(zip(headers, row, strict=True))))
    return records


def parse_export_text(export_format: str, payload_text: str) -> dict[str, Any]:
    export_format = str(export_format or "").strip().lower()
    if export_format not in SUPPORTED_FORMATS:
        raise ValueError("unsupported export format")
    if not isinstance(payload_text, str) or not payload_text.strip():
        raise ValueError("export payload text is required")

    if export_format == "json":
        records = _parse_json(payload_text)
    elif export_format in {"jsonl", "ndjson"}:
        records = _parse_jsonl(payload_text)
    elif export_format == "csv":
        records = _parse_csv(payload_text)
    else:
        records = _parse_html(payload_text)

    return {
        "schema": "socmint.import_adapter_result.v37_2",
        "version": "v37.2.0",
        "export_format": export_format,
        "records": records,
        "record_count": len(records),
        "payload_persisted": False,
        "network_access_performed": False,
        "collection_performed": False,
    }

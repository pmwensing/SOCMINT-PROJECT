from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from datetime import UTC, datetime
from typing import Any

EVIDENCE_APPENDIX_SCHEMA = "socmint.v7_5.dossier_evidence_appendix"
EVIDENCE_MANIFEST_SCHEMA = "socmint.v7_5.dossier_evidence_manifest"
REPORTABLE_SECTIONS = [
    "accounts",
    "evidence_backed_attributes",
    "timeline",
    "relationships",
    "contradictions",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _evidence_ids(item: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("evidence_refs", "evidence_ids", "source_refs"):
        values.extend(str(v) for v in _as_list(item.get(key)) if v not in (None, ""))
    for key in ("evidence_id", "artifact_id", "source_ref"):
        value = item.get(key)
        if value not in (None, ""):
            values.append(str(value))
    return list(dict.fromkeys(values))


def _source_value(item: dict[str, Any]) -> str | None:
    for key in ("source", "source_url", "platform", "source_ref"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    refs = _as_list(item.get("source_refs"))
    return str(refs[0]) if refs else None


def _claim_label(section: str, item: dict[str, Any]) -> str:
    return str(
        item.get("name")
        or item.get("claim")
        or item.get("event")
        or item.get("relationship")
        or item.get("handle")
        or item.get("url")
        or item.get("target")
        or item.get("platform")
        or item.get("id")
        or section
    )


def _iter_report_claims(payload: dict[str, Any]):
    for section in REPORTABLE_SECTIONS:
        items = payload.get(section) or []
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if isinstance(item, dict):
                yield section, index, item


def _evidence_catalog(
    raw_evidence: list[dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw_evidence or []):
        if not isinstance(item, dict):
            continue
        evidence_id = str(
            item.get("evidence_id")
            or item.get("id")
            or item.get("artifact_id")
            or f"evidence-{index + 1}"
        )
        catalog[evidence_id] = {
            "evidence_id": evidence_id,
            "label": item.get("label")
            or item.get("name")
            or item.get("event")
            or item.get("attribute")
            or evidence_id,
            "source": _source_value(item),
            "source_url": item.get("source_url") or item.get("url"),
            "artifact_id": item.get("artifact_id"),
            "sha256": item.get("sha256"),
            "mime_type": item.get("mime_type"),
            "size_bytes": item.get("size_bytes"),
            "confidence": item.get("confidence"),
            "raw": item,
        }
    return catalog


def build_evidence_appendix(
    payload: dict[str, Any], raw_evidence: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    catalog = _evidence_catalog(raw_evidence)
    entries: dict[str, dict[str, Any]] = {}
    missing_refs: list[dict[str, Any]] = []
    section_counts: Counter[str] = Counter()

    for section, index, item in _iter_report_claims(payload):
        section_counts[section] += 1
        refs = _evidence_ids(item)
        if not refs:
            missing_refs.append(
                {
                    "section": section,
                    "index": index,
                    "claim": _claim_label(section, item),
                    "missing": "evidence_refs",
                }
            )
            continue
        for ref in refs:
            base = catalog.get(
                ref, {"evidence_id": ref, "label": ref, "source": _source_value(item)}
            )
            entry = entries.setdefault(
                ref,
                {
                    "evidence_id": ref,
                    "label": base.get("label") or ref,
                    "source": base.get("source"),
                    "source_url": base.get("source_url"),
                    "artifact_id": base.get("artifact_id"),
                    "sha256": base.get("sha256"),
                    "mime_type": base.get("mime_type"),
                    "size_bytes": base.get("size_bytes"),
                    "confidence": base.get("confidence"),
                    "claim_refs": [],
                },
            )
            entry["claim_refs"].append(
                {
                    "section": section,
                    "index": index,
                    "claim": _claim_label(section, item),
                    "confidence": item.get("confidence"),
                }
            )

    appendix_entries = sorted(entries.values(), key=lambda row: row["evidence_id"])
    missing_hashes = [
        row["evidence_id"] for row in appendix_entries if not row.get("sha256")
    ]
    missing_sources = [
        row["evidence_id"]
        for row in appendix_entries
        if not row.get("source") and not row.get("source_url")
    ]
    generated_at = utc_now()
    return {
        "schema": EVIDENCE_APPENDIX_SCHEMA,
        "generated_at": generated_at,
        "approved_line": "v7.5",
        "entry_count": len(appendix_entries),
        "claim_section_counts": dict(sorted(section_counts.items())),
        "missing_ref_count": len(missing_refs),
        "missing_refs": missing_refs,
        "missing_hash_count": len(missing_hashes),
        "missing_hash_evidence_ids": missing_hashes,
        "missing_source_count": len(missing_sources),
        "missing_source_evidence_ids": missing_sources,
        "entries": appendix_entries,
    }


def build_evidence_manifest(
    payload: dict[str, Any], raw_evidence: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    appendix = build_evidence_appendix(payload, raw_evidence=raw_evidence)
    rows = []
    for entry in appendix["entries"]:
        rows.append(
            {
                "evidence_id": entry.get("evidence_id"),
                "label": entry.get("label"),
                "source": entry.get("source"),
                "source_url": entry.get("source_url"),
                "artifact_id": entry.get("artifact_id"),
                "sha256": entry.get("sha256"),
                "mime_type": entry.get("mime_type"),
                "size_bytes": entry.get("size_bytes"),
                "claim_count": len(entry.get("claim_refs") or []),
            }
        )
    manifest_body = canonical_json(rows)
    return {
        "schema": EVIDENCE_MANIFEST_SCHEMA,
        "generated_at": utc_now(),
        "approved_line": "v7.5",
        "row_count": len(rows),
        "sha256": sha256_text(manifest_body),
        "rows": rows,
        "appendix_summary": {
            "entry_count": appendix["entry_count"],
            "missing_ref_count": appendix["missing_ref_count"],
            "missing_hash_count": appendix["missing_hash_count"],
            "missing_source_count": appendix["missing_source_count"],
        },
    }


def evidence_manifest_csv(manifest: dict[str, Any]) -> str:
    fieldnames = [
        "evidence_id",
        "label",
        "source",
        "source_url",
        "artifact_id",
        "sha256",
        "mime_type",
        "size_bytes",
        "claim_count",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in manifest.get("rows", []):
        writer.writerow({field: row.get(field) for field in fieldnames})
    return output.getvalue()


def attach_evidence_appendix(
    payload: dict[str, Any], raw_evidence: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    enriched = dict(payload)
    appendix = build_evidence_appendix(payload, raw_evidence=raw_evidence)
    manifest = build_evidence_manifest(payload, raw_evidence=raw_evidence)
    enriched["evidence_appendix"] = appendix
    enriched["evidence_manifest"] = manifest
    return enriched

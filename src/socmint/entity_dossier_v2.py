from __future__ import annotations

import hashlib
import html
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text

from . import database as db
from .config import load_settings

DOSSIER_SCHEMA = "socmint.full_entity_profile_dossier.v7_8_1"
EXPORT_SCHEMA = "socmint.full_entity_profile_dossier_export.v7_5_1"
MANIFEST_SCHEMA = "socmint.full_entity_profile_dossier_manifest.v7_5_1"
DIAGNOSTIC_OBSERVATION_TYPES = {"connector_no_result", "seed_expansion_candidate"}
DIAGNOSTIC_ARCHIVE_TYPES = {"archive_candidate"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def dossier_root() -> Path:
    settings = load_settings(require_secret=False)
    root = Path(settings.data_dir) / "dossiers"
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_dossier_path(name: str) -> Path:
    root = dossier_root().resolve()
    path = (root / Path(name).name).resolve()
    if root not in path.parents and path != root:
        raise ValueError("Dossier path escapes dossier root")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_entry(path: Path, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "name": path.name,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _table_names() -> set[str]:
    try:
        return set(inspect(db.engine).get_table_names())
    except Exception:
        return set()


def _columns_for(table: str) -> set[str]:
    try:
        return {col["name"] for col in inspect(db.engine).get_columns(table)}
    except Exception:
        return set()


def _rows_for_subject(
    table: str, subject_id: int, limit: int = 200
) -> list[dict[str, Any]]:
    if table not in _table_names():
        return []
    columns = _columns_for(table)
    keys = ["subject_id", "spine_subject_id", "entity_id", "target_id", "id"]
    where_key = next((key for key in keys if key in columns), None)
    if where_key is None:
        return []
    query = text(f"select * from {table} where {where_key} = :subject_id limit :limit")
    try:
        with db.engine.begin() as conn:
            rows = conn.execute(query, {"subject_id": subject_id, "limit": limit})
            return [dict(row._mapping) for row in rows]
    except Exception:
        return []


def _first_subject_row(subject_id: int) -> dict[str, Any]:
    for table in ("spine_subjects", "subjects", "targets", "entities"):
        rows = _rows_for_subject(table, subject_id, limit=1)
        if rows:
            row = rows[0]
            row["_source_table"] = table
            return row
    return {
        "id": subject_id,
        "name": f"Subject {subject_id}",
        "_source_table": "fallback",
    }


def _safe_payload(loader_name: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        if loader_name == "review":
            from .report_review import review_summary

            return review_summary()
        if loader_name == "links":
            from .evidence_links import evidence_links_payload

            return evidence_links_payload()
        if loader_name == "custody":
            from .evidence_custody import custody_payload

            return custody_payload()
    except Exception as exc:
        fallback["error"] = str(exc)
    return fallback


def _evidence_payload(subject_id: int) -> dict[str, Any]:
    try:
        from .evidence_intake import evidence_intake_payload

        return evidence_intake_payload(subject_id=subject_id)
    except Exception as exc:
        return {"count": 0, "items": [], "error": str(exc)}


def _integrity_payload(subject_id: int) -> dict[str, Any]:
    try:
        from .evidence_integrity import integrity_dashboard_payload

        return integrity_dashboard_payload(subject_id=subject_id)
    except Exception as exc:
        return {
            "evidence_count": 0,
            "custody_event_count": 0,
            "link_count": 0,
            "error": str(exc),
        }


def _section(title: str, rows: list[dict[str, Any]], summary: str) -> dict[str, Any]:
    return {"title": title, "summary": summary, "count": len(rows), "items": rows}


def _json_from_row_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _observation_type(row: dict[str, Any]) -> str:
    return str(
        row.get("observation_type") or row.get("type") or row.get("kind") or ""
    ).strip()


def _is_diagnostic_observation(row: dict[str, Any]) -> bool:
    observation_type = _observation_type(row)
    payload = _json_from_row_value(row.get("payload_json") or row.get("payload"))
    if observation_type in DIAGNOSTIC_OBSERVATION_TYPES:
        return True
    if payload.get("diagnostic") is True:
        return True
    if observation_type in DIAGNOSTIC_ARCHIVE_TYPES:
        # ArchiveBox dry-run used to emit archive_candidate for the seed URL.
        # Treat it as troubleshooting metadata unless it has a real snapshot/capture marker.
        if payload.get("status") == "dry_run":
            return True
        if payload.get("connector") == "archivebox" and not any(
            payload.get(key)
            for key in (
                "snapshot_id",
                "snapshot_path",
                "index_path",
                "archive_path",
                "timestamp",
            )
        ):
            return True
    return False


def _split_real_observations(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    diagnostics = []
    real = []
    for row in rows:
        (diagnostics if _is_diagnostic_observation(row) else real).append(row)
    return real, diagnostics


def build_full_entity_dossier_v2(subject_id: int) -> dict[str, Any]:
    subject = _first_subject_row(subject_id)
    raw_observations = _rows_for_subject(
        "spine_observations", subject_id
    ) or _rows_for_subject("observations", subject_id)
    observations, diagnostics = _split_real_observations(raw_observations)
    assertions = _rows_for_subject(
        "spine_dossier_assertions", subject_id
    ) + _rows_for_subject("dossier_assertions", subject_id)
    findings = _rows_for_subject("findings", subject_id)
    identities = _rows_for_subject("identity_graphs", subject_id) + _rows_for_subject(
        "identity_edges", subject_id
    )
    enrichments = (
        _rows_for_subject("media_profiles", subject_id)
        + _rows_for_subject("enrichment_profiles", subject_id)
        + _rows_for_subject("enrichment_runs", subject_id)
    )
    contradictions = _rows_for_subject("contradictions", subject_id)
    dossier_exports = _rows_for_subject("dossier_exports", subject_id)

    review = _safe_payload("review", {"available": False})
    evidence = _evidence_payload(subject_id)
    links = _safe_payload("links", {"count": 0, "links": []})
    custody = _safe_payload("custody", {"event_count": 0, "events": []})
    integrity = _integrity_payload(subject_id)

    evidence_items = evidence.get("items", [])
    evidence_ids = {
        item.get("evidence_id") for item in evidence_items if item.get("evidence_id")
    }
    linked_evidence = [
        item
        for item in links.get("links", [])
        if item.get("evidence_id") in evidence_ids
        or item.get("evidence", {}).get("subject_id") == subject_id
    ]

    sections = {
        "identity_summary": _section(
            "Identity Summary",
            [subject],
            "Primary subject/entity record and source table.",
        ),
        "identity_graph": _section(
            "Identity Graph",
            identities,
            "Identity graph records, aliases, handles, and edges.",
        ),
        "dossier_assertions": _section(
            "Dossier Assertions",
            assertions,
            "Validated or candidate dossier assertions. Ultimate Dossier is the source-of-truth entity/human report.",
        ),
        "observations": _section(
            "Timeline / Real Observations",
            observations,
            "Dossier-grade observations only. Connector diagnostics and dry-run seed echoes are excluded.",
        ),
        "connector_diagnostics": _section(
            "Connector Diagnostics",
            diagnostics,
            "Troubleshooting records from connector runs. These are visible for audit/debugging but are not counted as real observations.",
        ),
        "findings": _section(
            "Findings",
            findings,
            "Analyst or system findings associated with this subject.",
        ),
        "enrichment": _section(
            "Enrichment Summary",
            enrichments,
            "Open-source enrichment outputs and profile records.",
        ),
        "contradictions": _section(
            "Contradictions",
            contradictions,
            "Assertion conflicts detected for this subject.",
        ),
        "review_decisions": {
            "title": "Analyst Review Decisions",
            "summary": "Review and quality gate payload.",
            "payload": review,
        },
        "linked_evidence": {
            "title": "Linked Evidence",
            "summary": "Evidence files and review-item links.",
            "evidence_count": len(evidence_items),
            "link_count": len(linked_evidence),
            "evidence": evidence_items,
            "links": linked_evidence,
        },
        "custody_hash_status": {
            "title": "Chain-of-Custody / Hash Status",
            "summary": "Integrity and custody status.",
            "integrity": integrity,
            "custody_event_count": custody.get("event_count", 0),
        },
        "prior_exports": _section(
            "Prior Dossier Exports",
            dossier_exports,
            "Existing dossier/export history for this subject.",
        ),
    }
    score = {
        "real_observation_count": len(observations),
        "diagnostic_count": len(diagnostics),
        "assertion_count": len(assertions),
        "evidence_count": len(evidence_items),
        "finding_count": len(findings),
        "linked_evidence_count": len(linked_evidence),
        "custody_event_count": custody.get("event_count", 0),
    }
    return {
        "schema": DOSSIER_SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "subject": subject,
        "score": score,
        "sections": sections,
    }


def render_dossier_markdown(payload: dict[str, Any]) -> str:
    subject = payload.get("subject") or {}
    name = (
        subject.get("name")
        or subject.get("label")
        or subject.get("username")
        or f"Subject {payload.get('subject_id')}"
    )
    lines = [
        "# Full Entity Profile Dossier v2",
        "",
        f"- Schema: `{payload.get('schema')}`",
        f"- Generated: `{payload.get('generated_at')}`",
        f"- Subject ID: `{payload.get('subject_id')}`",
        f"- Subject: `{name}`",
        "",
        "## Dossier Score",
        "",
    ]
    for key, value in (payload.get("score") or {}).items():
        lines.append(f"- {key}: `{value}`")
    for key, section in (payload.get("sections") or {}).items():
        lines.extend(["", f"## {section.get('title', key)}", ""])
        if section.get("summary"):
            lines.extend([section["summary"], ""])
        if "count" in section:
            lines.extend([f"- Count: `{section.get('count')}`", ""])
        for idx, item in enumerate(section.get("items", [])[:25], start=1):
            label = (
                item.get("name")
                or item.get("label")
                or item.get("title")
                or item.get("value")
                or item.get("id")
                or f"item-{idx}"
            )
            lines.extend([f"### {idx}. {label}", ""])
            for item_key, item_value in sorted(item.items()):
                if not str(item_key).startswith("_"):
                    lines.append(f"- {item_key}: `{item_value}`")
            lines.append("")
        if key == "linked_evidence":
            lines.append(f"- Evidence count: `{section.get('evidence_count')}`")
            lines.append(f"- Link count: `{section.get('link_count')}`")
            lines.append("")
        if key == "custody_hash_status":
            integrity = section.get("integrity") or {}
            lines.append(
                f"- Integrity evidence count: `{integrity.get('evidence_count')}`"
            )
            lines.append(
                f"- Integrity custody events: `{integrity.get('custody_event_count')}`"
            )
            lines.append(f"- Integrity links: `{integrity.get('link_count')}`")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_dossier_html(payload: dict[str, Any]) -> str:
    title = f"Full Entity Profile Dossier v2 — {payload.get('subject_id')}"
    body = html.escape(render_dossier_markdown(payload))
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;line-height:1.5;padding:0 1rem}"
        "pre{white-space:pre-wrap;background:#f6f6f6;padding:1rem;border-radius:10px}</style></head><body>"
        f"<h1>{html.escape(title)}</h1><pre>{body}</pre></body></html>\n"
    )


def export_full_entity_dossier_v2(subject_id: int) -> dict[str, Any]:
    payload = build_full_entity_dossier_v2(subject_id)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    base = f"subject-{subject_id}-full-entity-dossier-v2-{stamp}"
    root = dossier_root()

    json_path = root / f"{base}.json"
    md_path = root / f"{base}.md"
    html_path = root / f"{base}.html"
    manifest_path = root / f"{base}-export_manifest.json"
    zip_path = root / f"{base}.zip"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    md_path.write_text(render_dossier_markdown(payload))
    html_path.write_text(render_dossier_html(payload))

    files = [
        _manifest_entry(json_path, "dossier_json"),
        _manifest_entry(md_path, "dossier_markdown"),
        _manifest_entry(html_path, "dossier_html"),
    ]
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "artifact_count": len(files) + 1,
        "files": files,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    manifest["files"].append(_manifest_entry(manifest_path, "export_manifest"))
    manifest["artifact_count"] = len(manifest["files"])
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in (json_path, md_path, html_path, manifest_path):
            zf.write(path, arcname=path.name)
        zf.writestr(
            "README.txt",
            "\n".join(
                [
                    "SOCMINT Full Entity Profile Dossier v2",
                    f"Subject ID: {subject_id}",
                    f"Generated: {payload.get('generated_at')}",
                    "",
                    "Includes JSON, Markdown, HTML, and export_manifest.json with SHA-256 hashes.",
                ]
            ),
        )

    zip_entry = _manifest_entry(zip_path, "zip_bundle")
    manifest["files"].append(zip_entry)
    manifest["artifact_count"] = len(manifest["files"])
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    result = {
        "schema": EXPORT_SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "html_path": str(html_path),
        "manifest_path": str(manifest_path),
        "zip_path": str(zip_path),
        "manifest": manifest,
        "download_url": f"/spine/subjects/{subject_id}/dossier-v2/export/{zip_path.name}/download",
        "full_report_download_url": f"/api/v1/spine/subjects/{subject_id}/full-report/download?name={zip_path.name}",
        "dossier": payload,
    }
    result_path = root / f"{base}-EXPORT.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    result["result_path"] = str(result_path)
    return result

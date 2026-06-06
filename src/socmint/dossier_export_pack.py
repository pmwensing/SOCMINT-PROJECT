from __future__ import annotations

import hashlib
import html
import json
from datetime import UTC, datetime
from typing import Any

from .dossier_builder_v3 import DOSSIER_BUILDER_SCHEMA
from .dossier_builder_v3 import build_dossier_payload
from .dossier_builder_v3 import dossier_builder_summary

DOSSIER_EXPORT_SCHEMA = "socmint.dossier_export.v10_4_0"
SUPPORTED_EXPORT_FORMATS = ["json", "html"]
UNREVIEWED_STATES = {"unreviewed", "pending", "needs_review", "needs-review"}
CONTRADICTION_STATES = {"contradicted", "conflict", "contradiction", "blocked_contradiction"}


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_dossier_html(dossier: dict[str, Any]) -> str:
    subject = dossier.get("subject", {})
    summary = dossier_builder_summary(dossier)
    evidence_rows = []
    for item in dossier.get("evidence_matrix", []):
        evidence_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('evidence_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('label', '')))}</td>"
            f"<td>{html.escape(str(item.get('source', '')))}</td>"
            f"<td>{html.escape(str(item.get('confidence', '')))}</td>"
            f"<td>{html.escape(str(item.get('artifact_id', '') or ''))}</td>"
            "</tr>"
        )
    return "".join(
        [
            "<!doctype html><html><head><meta charset='utf-8'>",
            "<title>SOCMINT Dossier Export</title>",
            "<style>body{font-family:Arial,sans-serif;margin:2rem;}table{border-collapse:collapse;width:100%;}td,th{border:1px solid #ddd;padding:.5rem;}th{background:#f3f4f6;text-align:left;}code{background:#f3f4f6;padding:.15rem .3rem;}</style>",
            "</head><body>",
            "<h1>Full Entity Profile Dossier</h1>",
            f"<p><strong>Subject:</strong> {html.escape(str(subject.get('display_name', 'Unknown subject')))}</p>",
            f"<p><strong>Subject ID:</strong> <code>{html.escape(str(subject.get('subject_id', '')))}</code></p>",
            f"<p><strong>Case ID:</strong> <code>{html.escape(str(subject.get('case_id', '')))}</code></p>",
            f"<p><strong>Confidence:</strong> {html.escape(str(summary.get('confidence')))}</p>",
            f"<p><strong>Export ready:</strong> {html.escape(str(summary.get('export_ready')))}</p>",
            "<h2>Evidence Matrix</h2>",
            "<table><thead><tr><th>ID</th><th>Label</th><th>Source</th><th>Confidence</th><th>Artifact</th></tr></thead><tbody>",
            *evidence_rows,
            "</tbody></table>",
            "<h2>Review Queue</h2>",
            "<pre>",
            html.escape(canonical_json({"review_queue": dossier.get("review_queue", [])})),
            "</pre>",
            "</body></html>",
        ]
    )


def _evidence_claim_key(item: dict[str, Any]) -> str | None:
    for key in ("claim_id", "assertion_id"):
        if item.get(key):
            return str(item[key])
    if item.get("claim") or item.get("assertion_type"):
        return str(item.get("claim") or item.get("assertion_type"))
    return None


def export_policy_blockers(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = dossier.get("evidence_matrix") or []
    blockers: list[dict[str, Any]] = []
    unreviewed = [
        item
        for item in evidence
        if str(item.get("validation_state") or item.get("review_state") or "").lower() in UNREVIEWED_STATES
    ]
    if unreviewed:
        blockers.append(
            {
                "code": "unreviewed_assertions",
                "severity": "block",
                "count": len(unreviewed),
                "items": [item.get("assertion_id") or item.get("claim_id") or item.get("evidence_id") for item in unreviewed],
            }
        )

    claim_sources: dict[str, set[str]] = {}
    claim_items: dict[str, list[dict[str, Any]]] = {}
    for item in evidence:
        claim_key = _evidence_claim_key(item)
        if not claim_key:
            continue
        claim_sources.setdefault(claim_key, set()).add(str(item.get("source") or "unknown"))
        claim_items.setdefault(claim_key, []).append(item)
    single_source = [
        {"claim_id": claim_key, "sources": sorted(sources), "evidence_count": len(claim_items[claim_key])}
        for claim_key, sources in claim_sources.items()
        if len(sources) < 2
    ]
    if single_source:
        blockers.append(
            {
                "code": "single_source_claims",
                "severity": "block",
                "count": len(single_source),
                "items": single_source,
            }
        )

    contradictions = [
        item
        for item in evidence
        if item.get("contradiction") is True
        or str(item.get("status") or item.get("validation_state") or item.get("review_state") or "").lower() in CONTRADICTION_STATES
    ]
    dossier_contradictions = dossier.get("contradictions") or []
    if contradictions or dossier_contradictions:
        blockers.append(
            {
                "code": "contradictory_identity_claims",
                "severity": "block",
                "count": len(contradictions) + len(dossier_contradictions),
                "items": [
                    item.get("assertion_id") or item.get("claim_id") or item.get("evidence_id")
                    for item in contradictions
                ],
            }
        )
    return blockers


def export_preflight(dossier: dict[str, Any]) -> dict[str, Any]:
    builder_preflight = dossier.get("export_preflight", {})
    missing = []
    blockers = export_policy_blockers(dossier)
    if dossier.get("schema") != DOSSIER_BUILDER_SCHEMA:
        missing.append("valid dossier builder schema")
    if not dossier.get("subject", {}).get("subject_id"):
        missing.append("subject_id")
    if not dossier.get("subject", {}).get("case_id"):
        missing.append("case_id")
    if not dossier.get("evidence_matrix"):
        missing.append("evidence_matrix")
    if not builder_preflight.get("ready"):
        missing.append("builder export_preflight ready")
    return {
        "schema": DOSSIER_EXPORT_SCHEMA,
        "ready": not missing and not blockers,
        "missing": missing,
        "blockers": blockers,
        "builder_ready": bool(builder_preflight.get("ready")),
    }


def build_export_pack(
    subject: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    analyst_reviewed: bool = False,
) -> dict[str, Any]:
    dossier = build_dossier_payload(subject, evidence=evidence or [], analyst_reviewed=analyst_reviewed)
    preflight = export_preflight(dossier)
    json_body = canonical_json(dossier)
    html_body = render_dossier_html(dossier)
    generated_at = datetime.now(UTC).isoformat()
    artifacts = {
        "json": {
            "filename": "dossier.json",
            "media_type": "application/json",
            "sha256": sha256_text(json_body),
            "content": json_body,
        },
        "html": {
            "filename": "dossier.html",
            "media_type": "text/html",
            "sha256": sha256_text(html_body),
            "content": html_body,
        },
    }
    return {
        "schema": DOSSIER_EXPORT_SCHEMA,
        "generated_at": generated_at,
        "status": "ready" if preflight["ready"] else "needs_review",
        "preflight": preflight,
        "summary": dossier_builder_summary(dossier),
        "manifest": {
            "schema": DOSSIER_EXPORT_SCHEMA,
            "formats": SUPPORTED_EXPORT_FORMATS,
            "artifact_count": len(artifacts),
            "artifacts": {
                key: {
                    "filename": value["filename"],
                    "media_type": value["media_type"],
                    "sha256": value["sha256"],
                }
                for key, value in artifacts.items()
            },
        },
        "artifacts": artifacts,
    }


def export_pack_summary(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": DOSSIER_EXPORT_SCHEMA,
        "status": pack.get("status"),
        "ready": pack.get("preflight", {}).get("ready"),
        "artifact_count": pack.get("manifest", {}).get("artifact_count", 0),
        "formats": pack.get("manifest", {}).get("formats", []),
        "subject_id": pack.get("summary", {}).get("subject_id"),
        "case_id": pack.get("summary", {}).get("case_id"),
    }

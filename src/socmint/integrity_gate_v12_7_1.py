from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .authenticity_integrity_v12_7 import integrity_dashboard_payload

SCHEMA = "socmint.integrity_gate.v12_7_1"
REPORT_SCHEMA = "socmint.integrity_report_export.v12_7_1"

CRITICAL_FLAG_TYPES = {"hash_mismatch", "hash_not_verified", "preserved_file_missing"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _severity_counts(analyses: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {"critical": 0, "high": 0, "review": 0, "info": 0}
    for item in analyses:
        for flag in item.get("authenticity", {}).get("flags", []):
            severity = str(flag.get("severity") or "info")
            counts[severity] = counts.get(severity, 0) + 1
    return counts


def evidence_item_decision(item: dict[str, Any]) -> dict[str, Any]:
    flags = item.get("authenticity", {}).get("flags", [])
    flag_types = {flag.get("type") for flag in flags}
    critical = bool(flag_types & CRITICAL_FLAG_TYPES)
    decision = item.get("decision") or "analyst-review"
    if critical or item.get("composite_score", 0) < 0.4:
        usable = "hold"
    elif flags or decision in {"analyst-review", "hold"}:
        usable = "review"
    else:
        usable = "usable"
    return {
        "evidence_id": item.get("evidence_id"),
        "filename": item.get("filename"),
        "surface": item.get("surface"),
        "usable_state": usable,
        "integrity_decision": decision,
        "composite_score": item.get("composite_score"),
        "critical_flag": critical,
        "flag_count": len(flags),
        "requires_human_review": bool(item.get("requires_human_review") or flags),
        "flags": flags,
    }


def evidence_integrity_summary(root: str | None = None) -> dict[str, Any]:
    dashboard = integrity_dashboard_payload(root=root)
    analyses = dashboard.get("analyses", [])
    decisions = [evidence_item_decision(item) for item in analyses]
    usable = sum(1 for item in decisions if item["usable_state"] == "usable")
    review = sum(1 for item in decisions if item["usable_state"] == "review")
    hold = sum(1 for item in decisions if item["usable_state"] == "hold")
    critical_hash = [
        item
        for item in decisions
        if any(
            flag.get("type") in {"hash_mismatch", "hash_not_verified"}
            for flag in item.get("flags", [])
        )
    ]
    missing_originals = [
        item
        for item in decisions
        if any(
            flag.get("type") == "preserved_file_missing"
            for flag in item.get("flags", [])
        )
    ]
    flagged_review = [
        item
        for item in decisions
        if item["flag_count"] and item["usable_state"] != "hold"
    ]
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "item_count": len(analyses),
        "avg_composite_score": dashboard.get("summary", {}).get(
            "avg_composite_score", 0
        ),
        "usable_count": usable,
        "review_count": review,
        "hold_count": hold,
        "severity_counts": _severity_counts(analyses),
        "critical_hash_issues": critical_hash,
        "missing_preserved_originals": missing_originals,
        "flagged_requires_review": flagged_review,
        "item_decisions": decisions,
        "raw_integrity_dashboard": dashboard,
    }


def integrity_release_gate(root: str | None = None) -> dict[str, Any]:
    summary = evidence_integrity_summary(root=root)
    checks = [
        {
            "name": "integrity_score_available",
            "status": "pass" if summary["item_count"] > 0 else "review",
            "actual": summary["item_count"],
            "required": ">= 1 preserved evidence item for evidence-backed dossier gate",
        },
        {
            "name": "no_critical_hash_mismatch",
            "status": "pass" if not summary["critical_hash_issues"] else "fail",
            "actual": len(summary["critical_hash_issues"]),
        },
        {
            "name": "no_missing_preserved_originals",
            "status": "pass" if not summary["missing_preserved_originals"] else "fail",
            "actual": len(summary["missing_preserved_originals"]),
        },
        {
            "name": "flagged_evidence_requires_review",
            "status": "review" if summary["flagged_requires_review"] else "pass",
            "actual": len(summary["flagged_requires_review"]),
        },
        {
            "name": "no_hold_evidence_in_dossier",
            "status": "pass" if summary["hold_count"] == 0 else "fail",
            "actual": summary["hold_count"],
        },
    ]
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    review_count = sum(1 for check in checks if check["status"] == "review")
    decision = (
        "pass"
        if fail_count == 0 and review_count == 0
        else "review"
        if fail_count == 0
        else "fail"
    )
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": decision,
        "release_gate_decision": "GO"
        if decision == "pass"
        else "HOLD"
        if decision == "review"
        else "FAIL",
        "checks": checks,
        "summary": summary,
    }


def integrity_drilldown_for_claims(
    claims_by_evidence: dict[str, list[dict[str, Any]]], root: str | None = None
) -> dict[str, Any]:
    summary = evidence_integrity_summary(root=root)
    by_id = {
        item.get("evidence_id"): item for item in summary.get("item_decisions", [])
    }
    rows = []
    for evidence_id, claims in claims_by_evidence.items():
        rows.append(
            {
                "evidence_id": evidence_id,
                "claim_count": len(claims),
                "claims": claims,
                "integrity": by_id.get(
                    evidence_id,
                    {
                        "usable_state": "unknown",
                        "note": "No integrity decision found for this evidence id.",
                    },
                ),
            }
        )
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "rows": rows,
        "summary": summary,
    }


def integrity_report_root(root: str | None = None) -> Path:
    base = Path(root or "var/socmint")
    return base / "integrity_reports"


def write_integrity_report(root: str | None = None) -> dict[str, Any]:
    gate = integrity_release_gate(root=root)
    out = integrity_report_root(root)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    base = out / f"evidence_integrity_report_{stamp}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(gate, indent=2, sort_keys=True))
    lines = [
        "# Evidence Integrity Report",
        "",
        f"- Generated: `{gate.get('generated_at')}`",
        f"- Decision: `{gate.get('release_gate_decision')}`",
        f"- Status: `{gate.get('status')}`",
        f"- Items: `{gate.get('summary', {}).get('item_count')}`",
        f"- Average score: `{gate.get('summary', {}).get('avg_composite_score')}`",
        "",
        "## Gate Checks",
        "",
    ]
    for check in gate.get("checks", []):
        lines.append(
            f"- `{check.get('status')}` — {check.get('name')}: `{check.get('actual')}`"
        )
    lines.extend(["", "## Evidence Decisions", ""])
    for item in gate.get("summary", {}).get("item_decisions", []):
        lines.append(
            f"- `{item.get('usable_state')}` — {item.get('evidence_id')} — score `{item.get('composite_score')}` — flags `{item.get('flag_count')}`"
        )
    md_path.write_text("\n".join(lines) + "\n")
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": utc_now(),
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "decision": gate.get("release_gate_decision"),
        "status": gate.get("status"),
        "summary": gate.get("summary"),
    }

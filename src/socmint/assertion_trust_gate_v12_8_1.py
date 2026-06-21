from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .assertion_trust_v12_8 import (
    build_assertion_trust,
    corroboration_dashboard_payload,
)

SCHEMA = "socmint.assertion_trust_gate.v12_8_1"
REPORT_SCHEMA = "socmint.assertion_trust_report.v12_8_1"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def assertion_trust_summary(
    subject_id: int | None = None, root: str | None = None
) -> dict[str, Any]:
    trust = build_assertion_trust(subject_id=subject_id, root=root)
    assertions = trust.get("assertions", [])
    dossier_ready = [
        row for row in assertions if row.get("release_state") == "dossier-ready"
    ]
    review_queue = [
        row
        for row in assertions
        if row.get("release_state") in {"analyst-review", "hold", "low-confidence"}
    ]
    hold = [row for row in assertions if row.get("release_state") == "hold"]
    low_confidence = [
        row
        for row in assertions
        if row.get("release_state") == "low-confidence"
        or float(row.get("trust_score") or 0) < 0.5
    ]
    excluded = {row.get("assertion_id") for row in hold + low_confidence}
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "assertion_count": len(assertions),
        "dossier_ready_count": len(dossier_ready),
        "review_queue_count": len(review_queue),
        "hold_count": len(hold),
        "low_confidence_count": len(low_confidence),
        "avg_trust_score": trust.get("summary", {}).get("avg_trust_score", 0),
        "dossier_ready_assertions": dossier_ready,
        "analyst_review_queue": review_queue,
        "excluded_from_dossier_ready": [
            row for row in assertions if row.get("assertion_id") in excluded
        ],
        "raw_trust": trust,
    }


def assertion_release_gate(
    subject_id: int | None = None, root: str | None = None
) -> dict[str, Any]:
    summary = assertion_trust_summary(subject_id=subject_id, root=root)
    checks = [
        {
            "name": "assertion_trust_available",
            "status": "pass" if summary["assertion_count"] > 0 else "review",
            "actual": summary["assertion_count"],
            "required": ">= 1 assertion for trust-backed dossier gate",
        },
        {
            "name": "no_hold_assertions",
            "status": "pass" if summary["hold_count"] == 0 else "fail",
            "actual": summary["hold_count"],
        },
        {
            "name": "low_confidence_excluded_from_dossier_ready",
            "status": "pass"
            if all(
                float(row.get("trust_score") or 0) >= 0.5
                for row in summary["dossier_ready_assertions"]
            )
            else "fail",
            "actual": summary["low_confidence_count"],
        },
        {
            "name": "dossier_ready_assertions_available",
            "status": "pass" if summary["dossier_ready_count"] > 0 else "review",
            "actual": summary["dossier_ready_count"],
        },
        {
            "name": "review_queue_surfaced",
            "status": "pass",
            "actual": summary["review_queue_count"],
        },
    ]
    fail_count = sum(1 for item in checks if item["status"] == "fail")
    review_count = sum(1 for item in checks if item["status"] == "review")
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
        "subject_id": subject_id,
        "status": decision,
        "release_gate_decision": "GO"
        if decision == "pass"
        else "HOLD"
        if decision == "review"
        else "FAIL",
        "checks": checks,
        "summary": summary,
    }


def assertion_trust_report_root(root: str | None = None) -> Path:
    base = Path(root or "var/socmint")
    return base / "assertion_trust_reports"


def write_assertion_trust_report(
    subject_id: int | None = None, root: str | None = None
) -> dict[str, Any]:
    gate = assertion_release_gate(subject_id=subject_id, root=root)
    out = assertion_trust_report_root(root)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    suffix = f"subject_{subject_id}" if subject_id is not None else "case"
    base = out / f"assertion_trust_report_{suffix}_{stamp}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(gate, indent=2, sort_keys=True))
    lines = [
        "# Assertion Trust Report",
        "",
        f"- Generated: `{gate.get('generated_at')}`",
        f"- Decision: `{gate.get('release_gate_decision')}`",
        f"- Status: `{gate.get('status')}`",
        f"- Assertions: `{gate.get('summary', {}).get('assertion_count')}`",
        f"- Dossier-ready: `{gate.get('summary', {}).get('dossier_ready_count')}`",
        f"- Review queue: `{gate.get('summary', {}).get('review_queue_count')}`",
        f"- Hold: `{gate.get('summary', {}).get('hold_count')}`",
        "",
        "## Gate Checks",
        "",
    ]
    for check in gate.get("checks", []):
        lines.append(
            f"- `{check.get('status')}` — {check.get('name')}: `{check.get('actual')}`"
        )
    lines.extend(["", "## Dossier-Ready Assertions", ""])
    for row in gate.get("summary", {}).get("dossier_ready_assertions", []):
        lines.append(
            f"- `{row.get('trust_rating')}` `{row.get('trust_score')}` — {row.get('subject')} {row.get('predicate')} = {row.get('value')}"
        )
    lines.extend(["", "## Analyst Review Queue", ""])
    for row in gate.get("summary", {}).get("analyst_review_queue", []):
        lines.append(
            f"- `{row.get('release_state')}` `{row.get('trust_score')}` — {row.get('assertion_id')} — {row.get('subject')} {row.get('predicate')} = {row.get('value')}"
        )
    md_path.write_text("\n".join(lines) + "\n")
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "decision": gate.get("release_gate_decision"),
        "status": gate.get("status"),
        "summary": gate.get("summary"),
    }


def assertion_command_center_card(
    subject_id: int | None = None, root: str | None = None
) -> dict[str, Any]:
    gate = assertion_release_gate(subject_id=subject_id, root=root)
    summary = gate.get("summary", {})
    return {
        "schema": "socmint.command_center_assertion_trust_card.v12_8_1",
        "status": gate.get("status"),
        "decision": gate.get("release_gate_decision"),
        "assertion_count": summary.get("assertion_count", 0),
        "dossier_ready_count": summary.get("dossier_ready_count", 0),
        "review_queue_count": summary.get("review_queue_count", 0),
        "hold_count": summary.get("hold_count", 0),
        "avg_trust_score": summary.get("avg_trust_score", 0),
        "href": "/assertions/trust/gate",
    }


def assertion_trust_dashboard_plus(
    subject_id: int | None = None, root: str | None = None
) -> dict[str, Any]:
    return {
        "schema": "socmint.assertion_trust_dashboard_plus.v12_8_1",
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "corroboration": corroboration_dashboard_payload(
            subject_id=subject_id, root=root
        ),
        "gate": assertion_release_gate(subject_id=subject_id, root=root),
    }

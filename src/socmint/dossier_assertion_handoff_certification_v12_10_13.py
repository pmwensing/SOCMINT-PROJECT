from __future__ import annotations

import json
from typing import Any

SCHEMA = "socmint.dossier_assertion_handoff_certification.v12_10_13"
PIPELINE_STAGE = "dossier_assertion_handoff_certification"


def build_dossier_assertion_handoff_certification(
    handoff_bundle: dict[str, Any],
    handoff_seal: dict[str, Any],
    handoff_verification: dict[str, Any],
) -> dict[str, Any]:
    verification_passed = handoff_verification.get("status") == "pass"
    ready_count = int(handoff_bundle.get("ready_count", 0) or 0)
    blocked_count = int(handoff_bundle.get("blocked_count", 0) or 0)
    if not verification_passed:
        decision = "HOLD"
        next_action = "Repair handoff verification failures before analyst review."
    elif ready_count:
        decision = "GO_FOR_MANUAL_REVIEW"
        next_action = "Review ready handoff packets for manual assertion confirmation."
    else:
        decision = "REVIEW_BLOCKED_QUEUE"
        next_action = "Resolve blocked handoff packets before assertion review."
    certification_checks = [
        {"name": "handoff_verification_passed", "status": "pass" if verification_passed else "fail"},
        {"name": "handoff_seal_present", "status": "pass" if handoff_seal.get("bundle_hash_sha256") else "fail"},
        {"name": "manual_assertion_review_required", "status": "review"},
    ]
    return {
        "schema": SCHEMA,
        "stage": PIPELINE_STAGE,
        "pipeline_insert": "Handoff Verification -> Handoff Certification -> Manual Assertion Review",
        "decision": decision,
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "packet_count": int(handoff_bundle.get("total_count", 0) or 0),
        "bundle_hash_sha256": handoff_seal.get("bundle_hash_sha256"),
        "verification_status": handoff_verification.get("status"),
        "verification_failure_count": handoff_verification.get("failure_count", 0),
        "certification_checks": certification_checks,
        "next_action": next_action,
        "dossier_rule": "Certification covers handoff package integrity only. Assertions remain unconfirmed until an analyst reviews them.",
    }


def export_dossier_assertion_handoff_certification_report(payload: dict[str, Any], fmt: str = "json") -> tuple[str, str, str]:
    fmt = (fmt or "json").lower().strip()
    if fmt in {"md", "markdown"}:
        lines = [
            "# Dossier Assertion Handoff Certification",
            "",
            f"Schema: `{SCHEMA}`",
            "",
            f"Decision: {payload.get('decision', 'unknown')}",
            f"Ready packets: {payload.get('ready_count', 0)}",
            f"Blocked packets: {payload.get('blocked_count', 0)}",
            f"Bundle SHA-256: `{payload.get('bundle_hash_sha256', '')}`",
            "",
            "## Checks",
            "",
        ]
        for check in payload.get("certification_checks", []):
            lines.append(f"- {check.get('name')}: {check.get('status')}")
        lines.extend(["", "## Next Action", "", payload.get("next_action", ""), "", "## Rule", "", payload.get("dossier_rule", "")])
        return "text/markdown", "dossier-assertion-handoff-certification.md", "\n".join(lines)
    return "application/json", "dossier-assertion-handoff-certification.json", json.dumps(payload, indent=2, sort_keys=True)

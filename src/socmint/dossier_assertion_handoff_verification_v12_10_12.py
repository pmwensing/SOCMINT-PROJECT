from __future__ import annotations

import json
from typing import Any

from .dossier_assertion_handoff_seal_v12_10_11 import verify_dossier_assertion_handoff_seal

SCHEMA = "socmint.dossier_assertion_handoff_verification.v12_10_12"
PIPELINE_STAGE = "dossier_assertion_handoff_verification"


def build_dossier_assertion_handoff_verification(handoff_bundle: dict[str, Any], handoff_seal: dict[str, Any]) -> dict[str, Any]:
    seal_check = verify_dossier_assertion_handoff_seal(handoff_bundle, handoff_seal)
    counts_match = (
        int(handoff_bundle.get("total_count", 0) or 0) == int(handoff_seal.get("packet_count", 0) or 0)
        and int(handoff_bundle.get("ready_count", 0) or 0) == int(handoff_seal.get("ready_count", 0) or 0)
        and int(handoff_bundle.get("blocked_count", 0) or 0) == int(handoff_seal.get("blocked_count", 0) or 0)
    )
    schema_match = handoff_seal.get("sealed_payload_schema") == handoff_bundle.get("schema")
    checks = [
        {"name": "bundle_hash_match", "status": seal_check.get("status")},
        {"name": "packet_counts_match", "status": "pass" if counts_match else "fail"},
        {"name": "sealed_schema_matches_bundle", "status": "pass" if schema_match else "fail"},
        {"name": "manual_review_required", "status": "review"},
    ]
    failure_count = len([item for item in checks if item.get("status") == "fail"])
    return {
        "schema": SCHEMA,
        "stage": PIPELINE_STAGE,
        "pipeline_insert": "Handoff Integrity Seal -> Handoff Verification -> Manual Assertion Review",
        "status": "pass" if failure_count == 0 else "fail",
        "failure_count": failure_count,
        "checks": checks,
        "seal_check": seal_check,
        "bundle_hash_sha256": handoff_seal.get("bundle_hash_sha256"),
        "packet_count": handoff_bundle.get("total_count", 0),
        "ready_count": handoff_bundle.get("ready_count", 0),
        "blocked_count": handoff_bundle.get("blocked_count", 0),
        "dossier_rule": "Verification proves handoff integrity only. Analyst review is still required before assertion confirmation.",
    }


def export_dossier_assertion_handoff_verification_report(payload: dict[str, Any], fmt: str = "json") -> tuple[str, str, str]:
    fmt = (fmt or "json").lower().strip()
    if fmt in {"md", "markdown"}:
        lines = [
            "# Dossier Assertion Handoff Verification",
            "",
            f"Schema: `{SCHEMA}`",
            "",
            f"Status: {payload.get('status', 'unknown')}",
            f"Failures: {payload.get('failure_count', 0)}",
            f"Bundle SHA-256: `{payload.get('bundle_hash_sha256', '')}`",
            "",
            "## Checks",
            "",
        ]
        for check in payload.get("checks", []):
            lines.append(f"- {check.get('name')}: {check.get('status')}")
        lines.extend(["", "## Rule", "", payload.get("dossier_rule", "")])
        return "text/markdown", "dossier-assertion-handoff-verification.md", "\n".join(lines)
    return "application/json", "dossier-assertion-handoff-verification.json", json.dumps(payload, indent=2, sort_keys=True)

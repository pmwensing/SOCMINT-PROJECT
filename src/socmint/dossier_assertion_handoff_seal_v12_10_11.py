from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA = "socmint.dossier_assertion_handoff_seal.v12_10_11"
PIPELINE_STAGE = "dossier_assertion_handoff_seal"


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical(payload).encode()).hexdigest()


def build_dossier_assertion_handoff_seal(
    handoff_bundle: dict[str, Any],
) -> dict[str, Any]:
    ready_packets = handoff_bundle.get("ready_packets", []) or []
    blocked_packets = handoff_bundle.get("blocked_packets", []) or []
    sealed_payload = {
        "schema": handoff_bundle.get("schema"),
        "ready_packets": ready_packets,
        "blocked_packets": blocked_packets,
        "ready_count": handoff_bundle.get("ready_count", 0),
        "blocked_count": handoff_bundle.get("blocked_count", 0),
        "total_count": handoff_bundle.get("total_count", 0),
    }
    ready_hash = _sha256(ready_packets)
    blocked_hash = _sha256(blocked_packets)
    bundle_hash = _sha256(sealed_payload)
    return {
        "schema": SCHEMA,
        "stage": PIPELINE_STAGE,
        "pipeline_insert": "Analyst Handoff Bundle -> Handoff Integrity Seal -> Manual Assertion Review",
        "bundle_hash_sha256": bundle_hash,
        "ready_hash_sha256": ready_hash,
        "blocked_hash_sha256": blocked_hash,
        "packet_count": handoff_bundle.get("total_count", 0),
        "ready_count": handoff_bundle.get("ready_count", 0),
        "blocked_count": handoff_bundle.get("blocked_count", 0),
        "sealed_payload_schema": handoff_bundle.get("schema"),
        "verification": {
            "status": "sealed",
            "algorithm": "sha256",
            "canonicalization": "json-sort-keys-compact-ascii",
        },
        "dossier_rule": "The handoff seal verifies queue integrity for operator review. It does not approve or mutate assertions.",
    }


def verify_dossier_assertion_handoff_seal(
    handoff_bundle: dict[str, Any], seal: dict[str, Any]
) -> dict[str, Any]:
    expected = build_dossier_assertion_handoff_seal(handoff_bundle)
    matches = expected.get("bundle_hash_sha256") == seal.get("bundle_hash_sha256")
    return {
        "schema": f"{SCHEMA}.verification",
        "status": "pass" if matches else "fail",
        "expected_bundle_hash_sha256": expected.get("bundle_hash_sha256"),
        "actual_bundle_hash_sha256": seal.get("bundle_hash_sha256"),
        "ready_hash_sha256": expected.get("ready_hash_sha256"),
        "blocked_hash_sha256": expected.get("blocked_hash_sha256"),
    }


def export_dossier_assertion_handoff_seal_report(
    payload: dict[str, Any], fmt: str = "json"
) -> tuple[str, str, str]:
    fmt = (fmt or "json").lower().strip()
    if fmt in {"md", "markdown"}:
        lines = [
            "# Dossier Assertion Handoff Seal",
            "",
            f"Schema: `{SCHEMA}`",
            "",
            f"Bundle SHA-256: `{payload.get('bundle_hash_sha256', '')}`",
            f"Ready SHA-256: `{payload.get('ready_hash_sha256', '')}`",
            f"Blocked SHA-256: `{payload.get('blocked_hash_sha256', '')}`",
            "",
            "## Rule",
            "",
            payload.get("dossier_rule", ""),
        ]
        return "text/markdown", "dossier-assertion-handoff-seal.md", "\n".join(lines)
    return (
        "application/json",
        "dossier-assertion-handoff-seal.json",
        json.dumps(payload, indent=2, sort_keys=True),
    )

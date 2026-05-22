from __future__ import annotations

import json
from collections import Counter
from typing import Any

SCHEMA = "socmint.dossier_assertion_review_packet.v12_10_9"
PIPELINE_STAGE = "dossier_assertion_review_packet"


def _action_for_projection(projection: dict[str, Any]) -> str:
    if projection.get("status") == "ready" and projection.get("dossier_ready"):
        return "review_for_confirmation"
    if projection.get("decision") == "FAIL":
        return "keep_suppressed"
    return "resolve_blockers"


def _checklist(projection: dict[str, Any]) -> list[dict[str, Any]]:
    evidence_refs = projection.get("evidence_refs") or []
    alias_ids = projection.get("supporting_alias_ids") or []
    return [
        {"name": "identity_link_go", "status": "pass" if projection.get("decision") == "GO" else "hold"},
        {"name": "evidence_refs_present", "status": "pass" if evidence_refs else "hold"},
        {"name": "supporting_aliases_present", "status": "pass" if alias_ids else "hold"},
        {"name": "projection_not_blocked", "status": "pass" if projection.get("status") == "ready" else "hold"},
        {"name": "analyst_confirmation_required", "status": "review"},
    ]


def build_dossier_assertion_review_packet(projection_payload: dict[str, Any]) -> dict[str, Any]:
    packets: list[dict[str, Any]] = []
    for projection in projection_payload.get("projections", []) or []:
        checklist = _checklist(projection)
        blocker_names = [item["name"] for item in checklist if item["status"] == "hold"]
        packets.append(
            {
                "packet_id": f"review-packet-{projection.get('candidate_id')}",
                "projection_id": projection.get("projection_id"),
                "candidate_id": projection.get("candidate_id"),
                "assertion_type": projection.get("assertion_type"),
                "assertion_value": projection.get("assertion_value"),
                "recommended_action": _action_for_projection(projection),
                "review_state": "ready_for_analyst" if not blocker_names else "blocked",
                "confidence": projection.get("confidence", 0),
                "evidence_refs": projection.get("evidence_refs") or [],
                "supporting_alias_ids": projection.get("supporting_alias_ids") or [],
                "supporting_alias_types": projection.get("supporting_alias_types") or [],
                "blockers": blocker_names,
                "reasons": projection.get("reasons") or [],
                "checklist": checklist,
            }
        )
    counts = Counter(row["review_state"] for row in packets)
    actions = Counter(row["recommended_action"] for row in packets)
    return {
        "schema": SCHEMA,
        "stage": PIPELINE_STAGE,
        "pipeline_insert": "Dossier Assertion Projection -> Assertion Review Packet -> Analyst Assertion Review",
        "packet_count": len(packets),
        "ready_packet_count": counts.get("ready_for_analyst", 0),
        "blocked_packet_count": counts.get("blocked", 0),
        "recommended_actions": dict(actions),
        "packets": packets,
        "dossier_rule": "Review packets organize evidence and blockers. They do not create confirmed assertions without analyst action.",
    }


def export_dossier_assertion_review_packet_report(payload: dict[str, Any], fmt: str = "json") -> tuple[str, str, str]:
    fmt = (fmt or "json").lower().strip()
    if fmt in {"md", "markdown"}:
        lines = [
            "# Dossier Assertion Review Packet",
            "",
            f"Schema: `{SCHEMA}`",
            "",
            f"Ready packets: {payload.get('ready_packet_count', 0)}",
            f"Blocked packets: {payload.get('blocked_packet_count', 0)}",
            "",
            "## Rule",
            "",
            payload.get("dossier_rule", ""),
            "",
            "## Packets",
            "",
        ]
        for row in payload.get("packets", []):
            lines.extend(
                [
                    f"### {row.get('packet_id')}",
                    f"- Review state: {row.get('review_state')}",
                    f"- Recommended action: {row.get('recommended_action')}",
                    f"- Assertion: {row.get('assertion_type')} = {row.get('assertion_value')}",
                    f"- Blockers: {', '.join(row.get('blockers') or []) or 'none'}",
                    "",
                ]
            )
        return "text/markdown", "dossier-assertion-review-packet.md", "\n".join(lines)
    return "application/json", "dossier-assertion-review-packet.json", json.dumps(payload, indent=2, sort_keys=True)

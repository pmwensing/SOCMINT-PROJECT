from __future__ import annotations

import json
from typing import Any

SCHEMA = "socmint.dossier_assertion_handoff_bundle.v12_10_10"
PIPELINE_STAGE = "dossier_assertion_handoff_bundle"


def _packet_row(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_id": packet.get("packet_id"),
        "candidate_id": packet.get("candidate_id"),
        "assertion_type": packet.get("assertion_type"),
        "assertion_value": packet.get("assertion_value"),
        "recommended_action": packet.get("recommended_action"),
        "confidence": packet.get("confidence", 0),
        "evidence_refs": packet.get("evidence_refs") or [],
        "blockers": packet.get("blockers") or [],
    }


def build_dossier_assertion_handoff_bundle(
    review_packet_payload: dict[str, Any],
) -> dict[str, Any]:
    ready: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for packet in review_packet_payload.get("packets", []) or []:
        row = _packet_row(packet)
        if packet.get("review_state") == "ready_for_analyst":
            ready.append(row)
        else:
            blocked.append(row)
    ready.sort(
        key=lambda item: (
            -float(item.get("confidence") or 0),
            item.get("packet_id") or "",
        )
    )
    blocked.sort(
        key=lambda item: (len(item.get("blockers") or []), item.get("packet_id") or "")
    )
    return {
        "schema": SCHEMA,
        "stage": PIPELINE_STAGE,
        "pipeline_insert": "Assertion Review Packet -> Analyst Handoff Bundle -> Manual Assertion Review",
        "ready_count": len(ready),
        "blocked_count": len(blocked),
        "total_count": len(ready) + len(blocked),
        "ready_packets": ready,
        "blocked_packets": blocked,
        "next_actions": [
            "Review ready packets for manual assertion confirmation.",
            "Resolve blocked packet checklist items before assertion review.",
            "Keep this bundle as operator handoff context; it does not mutate dossier assertions.",
        ],
        "dossier_rule": "The handoff bundle is an operator queue. It never confirms, suppresses, or promotes assertions automatically.",
    }


def export_dossier_assertion_handoff_bundle_report(
    payload: dict[str, Any], fmt: str = "json"
) -> tuple[str, str, str]:
    fmt = (fmt or "json").lower().strip()
    if fmt in {"md", "markdown"}:
        lines = [
            "# Dossier Assertion Handoff Bundle",
            "",
            f"Schema: `{SCHEMA}`",
            "",
            f"Ready: {payload.get('ready_count', 0)}",
            f"Blocked: {payload.get('blocked_count', 0)}",
            "",
            "## Rule",
            "",
            payload.get("dossier_rule", ""),
            "",
            "## Ready Packets",
            "",
        ]
        for row in payload.get("ready_packets", []):
            lines.extend(
                [
                    f"- {row.get('packet_id')}: {row.get('assertion_value')} ({row.get('recommended_action')})"
                ]
            )
        lines.extend(["", "## Blocked Packets", ""])
        for row in payload.get("blocked_packets", []):
            lines.extend(
                [
                    f"- {row.get('packet_id')}: {', '.join(row.get('blockers') or []) or 'blocked'}"
                ]
            )
        return "text/markdown", "dossier-assertion-handoff-bundle.md", "\n".join(lines)
    return (
        "application/json",
        "dossier-assertion-handoff-bundle.json",
        json.dumps(payload, indent=2, sort_keys=True),
    )

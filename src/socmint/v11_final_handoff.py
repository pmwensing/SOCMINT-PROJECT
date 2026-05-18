from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from .connector_runtime_health import connector_runtime_health_payload
except Exception:  # pragma: no cover
    connector_runtime_health_payload = None

V11_FINAL_SCHEMA = "socmint.v11_10.final_stabilization_handoff"
V11_BASELINE = "v11 FINAL BASELINE"
V11_FINAL_HEAD = "7513b95"

MILESTONES = [
    {"version": "v11.1.1", "title": "Frontend Route Audit Harness + Command Center Polish", "pr": 146},
    {"version": "v11.2", "title": "Subject Workflow Functional Smoke + Dossier Generation QA", "pr": 147},
    {"version": "v11.3", "title": "Test Data Hygiene + Workflow Cleanup + Re-run Stability", "pr": 148},
    {"version": "v11.4", "title": "Command Center Test Data Controls + Operator QA Dashboard", "pr": 149},
    {"version": "v11.5", "title": "Legacy Absolute Import Cleanup + Docker Runtime Stability", "pr": 150},
    {"version": "v11.6", "title": "Command Center Operator Readiness + Release Gate Dashboard", "pr": 151},
    {"version": "v11.7", "title": "Connector Runtime Docker Toolchain + Template Fix", "pr": 152},
    {"version": "v11.8", "title": "Real Connector Run QA + Enrichment Normalization Upgrade", "pr": 153},
    {"version": "v11.9", "title": "Real Enrichment Run UX + Evidence Promotion Pipeline", "pr": 154},
    {"version": "v11.9.1", "title": "Import-Health Smoke Timeout-Safe Fix", "pr": 155},
    {"version": "v11.9.2", "title": "Maigret JSON Argument Compatibility", "pr": 156},
]

KNOWN_ISSUES = [
    {
        "id": "optional-connectors-phoneinfoga-archivebox",
        "severity": "review",
        "status": "accepted-for-v12-plus",
        "summary": "PhoneInfoga and ArchiveBox are optional/manual in v11 and must not block v11 finalization.",
        "handoff": "Track lifecycle monitoring and optional install/repair in v12/v12.5.",
    },
    {
        "id": "live-connector-variability",
        "severity": "review",
        "status": "expected-runtime-risk",
        "summary": "Live OSINT connector output can vary by network, target, CLI version, upstream site behavior, and rate limits.",
        "handoff": "Keep connector trust scoring and diagnostic/real badge separation in v12 production gate.",
    },
    {
        "id": "dry-run-not-evidence",
        "severity": "high",
        "status": "guarded",
        "summary": "Dry-run and diagnostic connector output must never count as dossier-grade or court-grade evidence.",
        "handoff": "v12 analyst validation and production gate must preserve this rule.",
    },
]

V12_HANDOFF = {
    "next_sequence": ["v12.0 RC", "v12.3 Recon Expansion", "v12.5 Forensic Intake"],
    "v12_0_focus": [
        "Full Entity Profile Dossier Production Gate",
        "GO / HOLD / FAIL dashboard",
        "Full export manifest and chain-of-custody validation",
        "test-all-socmint harness",
    ],
    "v12_3_focus": [
        "Dork/search recon engine",
        "File discovery",
        "Email/domain/leak intelligence",
        "Recon campaign scaffolding",
    ],
    "v12_5_focus": [
        "Drop-folder ingestion",
        "Multi-modal forensic parsing",
        "Court-safe evidence vault",
        "Hash/manifest/custody-first preservation",
    ],
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _connector_health() -> dict[str, Any]:
    if connector_runtime_health_payload is None:
        return {"available": False, "reason": "connector runtime health module unavailable"}
    try:
        return connector_runtime_health_payload()
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def final_handoff_payload() -> dict[str, Any]:
    connector_health = _connector_health()
    ready = 0
    missing = 0
    if isinstance(connector_health, dict):
        summary = connector_health.get("summary") or {}
        ready = int(summary.get("ready") or 0)
        missing = int(summary.get("missing") or 0)
    return {
        "schema": V11_FINAL_SCHEMA,
        "generated_at": utc_now(),
        "baseline": V11_BASELINE,
        "expected_head_short": V11_FINAL_HEAD,
        "status": "final-ready",
        "release_gate_decision": "GO_FOR_V12_HANDOFF",
        "milestones": MILESTONES,
        "known_issues": KNOWN_ISSUES,
        "connector_runtime": {
            "ready": ready,
            "missing": missing,
            "payload": connector_health,
        },
        "v12_handoff": V12_HANDOFF,
        "final_rules": [
            "v11 feature work is frozen after v11.10 merge unless a critical regression is found.",
            "New collection/recon/forensic features move to v12.x branches.",
            "Dry-run/diagnostic output remains excluded from dossier-grade evidence.",
            "Optional connector gaps are tracked but do not block v11 final baseline.",
        ],
    }


def write_final_handoff(root: str = "release") -> dict[str, Any]:
    payload = final_handoff_payload()
    out = Path(root)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "V11_10_FINAL_STABILIZATION_HANDOFF.json"
    md_path = out / "V11_10_FINAL_STABILIZATION_HANDOFF.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = [
        "# v11.10 — Final v11 Stabilization + RC Handoff",
        "",
        f"- Schema: `{payload['schema']}`",
        f"- Generated: `{payload['generated_at']}`",
        f"- Baseline: `{payload['baseline']}`",
        f"- Expected HEAD: `{payload['expected_head_short']}`",
        f"- Decision: `{payload['release_gate_decision']}`",
        "",
        "## v11 Milestones",
        "",
    ]
    for item in MILESTONES:
        lines.append(f"- {item['version']} — PR #{item['pr']} — {item['title']}")
    lines.extend(["", "## Known Issues / Accepted Handoff Items", ""])
    for item in KNOWN_ISSUES:
        lines.append(f"- `{item['severity']}` {item['id']}: {item['summary']} Handoff: {item['handoff']}")
    lines.extend(["", "## v12 Handoff", ""])
    for key, values in V12_HANDOFF.items():
        lines.append(f"### {key}")
        for value in values:
            lines.append(f"- {value}")
        lines.append("")
    md_path.write_text("\n".join(lines).rstrip() + "\n")
    return {"payload": payload, "json_path": str(json_path), "markdown_path": str(md_path)}


if __name__ == "__main__":
    print(json.dumps(write_final_handoff(), indent=2, sort_keys=True))

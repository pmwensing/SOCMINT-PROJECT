from __future__ import annotations

import json
from collections import Counter
from typing import Any

SCHEMA = "socmint.dossier_assertion_projection.v12_10_8"
PIPELINE_STAGE = "dossier_assertion_projection"


def _alias_lookup(alias_graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        alias.get("alias_id"): alias
        for alias in alias_graph.get("aliases", []) or []
        if alias.get("alias_id")
    }


def _supporting_evidence_refs(
    alias_ids: list[str], aliases: dict[str, dict[str, Any]]
) -> list[str]:
    refs: list[str] = []
    for alias_id in alias_ids:
        for ref in aliases.get(alias_id, {}).get("evidence_refs") or []:
            if ref and ref not in refs:
                refs.append(ref)
    return refs


def _supporting_alias_types(
    alias_ids: list[str], aliases: dict[str, dict[str, Any]]
) -> list[str]:
    types = {aliases.get(alias_id, {}).get("alias_type") for alias_id in alias_ids}
    return sorted(item for item in types if item)


def build_dossier_assertion_projection(
    identity_links: dict[str, Any], alias_graph: dict[str, Any]
) -> dict[str, Any]:
    aliases = _alias_lookup(alias_graph)
    projections: list[dict[str, Any]] = []
    for link in identity_links.get("hypotheses", []) or []:
        alias_ids = [item for item in link.get("alias_ids") or [] if item]
        evidence_refs = _supporting_evidence_refs(alias_ids, aliases)
        alias_types = _supporting_alias_types(alias_ids, aliases)
        decision = link.get("decision")
        ready = decision == "GO" and bool(evidence_refs)
        if decision == "GO" and not evidence_refs:
            status = "blocked"
            reasons = ["GO identity link lacks attached evidence references"]
        elif decision == "GO":
            status = "ready"
            reasons = ["identity link is GO with evidence-backed alias support"]
        else:
            status = "blocked"
            reasons = list(link.get("reasons") or ["identity link is not GO"])
        projections.append(
            {
                "projection_id": f"dossier-assertion-{link.get('candidate_id')}",
                "hypothesis_id": link.get("hypothesis_id"),
                "candidate_id": link.get("candidate_id"),
                "assertion_type": "same_entity_profile",
                "assertion_value": link.get("profile_url")
                or f"{link.get('platform')}/{link.get('username')}",
                "decision": decision,
                "status": status,
                "dossier_ready": ready,
                "confidence": link.get("identity_score", 0),
                "supporting_alias_types": alias_types,
                "supporting_alias_ids": alias_ids,
                "evidence_refs": evidence_refs,
                "reasons": reasons,
            }
        )
    counts = Counter(row["status"] for row in projections)
    return {
        "schema": SCHEMA,
        "stage": PIPELINE_STAGE,
        "pipeline_insert": "Identity Link Hypothesis -> Dossier Assertion Projection -> Analyst Assertion Review",
        "projection_count": len(projections),
        "ready_count": counts.get("ready", 0),
        "blocked_count": counts.get("blocked", 0),
        "projections": projections,
        "dossier_rule": "Projection is read-only. A same-entity assertion still requires analyst review before it becomes dossier-grade.",
    }


def export_dossier_assertion_projection_report(
    payload: dict[str, Any], fmt: str = "json"
) -> tuple[str, str, str]:
    fmt = (fmt or "json").lower().strip()
    if fmt in {"md", "markdown"}:
        lines = [
            "# Dossier Assertion Projection",
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
            "## Projections",
            "",
        ]
        for row in payload.get("projections", []):
            lines.extend(
                [
                    f"### {row.get('projection_id')}",
                    f"- Status: {row.get('status')}",
                    f"- Value: {row.get('assertion_value')}",
                    f"- Evidence refs: {', '.join(row.get('evidence_refs') or []) or 'n/a'}",
                    f"- Reasons: {'; '.join(row.get('reasons') or [])}",
                    "",
                ]
            )
        return "text/markdown", "dossier-assertion-projection.md", "\n".join(lines)
    return (
        "application/json",
        "dossier-assertion-projection.json",
        json.dumps(payload, indent=2, sort_keys=True),
    )

from __future__ import annotations

import json
from collections import Counter
from typing import Any

SCHEMA = "socmint.identity_link_hypothesis.v12_10_7"
PIPELINE_STAGE = "identity_link_hypothesis"
READY_STATES = {"accepted", "confirmed"}
HOLD_STATES = {"uncertain", "needs_more_evidence", "unreviewed", "candidate"}
FAIL_STATES = {"rejected", "suppressed"}
STRONG_ALIAS_TYPES = {"email", "phone", "url", "domain"}
SUPPORTING_ALIAS_TYPES = {"username", "handle", "visual_hash", "text_hash"}


def _state(candidate: dict[str, Any]) -> str:
    return (
        str((candidate.get("analyst_review") or {}).get("review_state") or "unreviewed")
        .strip()
        .lower()
    )


def _candidate_aliases(
    alias_graph: dict[str, Any], candidate_id: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for alias in alias_graph.get("aliases", []) or []:
        if candidate_id in (alias.get("candidate_ids") or []):
            rows.append(alias)
    return rows


def _collision_ids(alias_graph: dict[str, Any]) -> set[str]:
    return {
        row.get("alias_id")
        for row in alias_graph.get("collision_sets", []) or []
        if row.get("status") == "reverse_collision_review"
    }


def _evidence_ready(candidate: dict[str, Any]) -> bool:
    fp = candidate.get("profile_fingerprint") or {}
    capture = candidate.get("evidence_capture") or {}
    return bool(
        capture.get("capture_id")
        or fp.get("html_sha256")
        or fp.get("metadata_sha256")
        or fp.get("text_fingerprint_hash")
        or fp.get("visual_fingerprint_hash")
    )


def _decision(
    candidate: dict[str, Any],
    aliases: list[dict[str, Any]],
    collided_alias_ids: set[str],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    state = _state(candidate)
    if state in FAIL_STATES or candidate.get("dossier_assertion_gate", {}).get(
        "suppressed"
    ):
        return "FAIL", ["candidate was rejected or suppressed by analyst review"]
    if state in HOLD_STATES:
        reasons.append("candidate profile still requires analyst review")
    if not _evidence_ready(candidate):
        reasons.append("captured profile evidence or fingerprint hashes are missing")

    strong = [
        alias
        for alias in aliases
        if alias.get("alias_type") in STRONG_ALIAS_TYPES
        and alias.get("analyst_state") == "confirmed"
    ]
    supporting = [
        alias
        for alias in aliases
        if alias.get("alias_type") in SUPPORTING_ALIAS_TYPES
        and alias.get("analyst_state") == "confirmed"
    ]
    collisions = [
        alias for alias in aliases if alias.get("alias_id") in collided_alias_ids
    ]
    if collisions:
        reasons.append("one or more aliases appear in reverse-collision review sets")
    if not strong and len(supporting) < 2:
        reasons.append(
            "identity link needs a confirmed strong alias or two confirmed supporting aliases"
        )
    if reasons:
        return "HOLD", reasons
    return "GO", [
        "accepted candidate has reviewed evidence and confirmed alias support"
    ]


def build_identity_link_hypotheses(
    alias_graph: dict[str, Any], profile_payload: dict[str, Any]
) -> dict[str, Any]:
    collided_alias_ids = _collision_ids(alias_graph)
    hypotheses: list[dict[str, Any]] = []
    for candidate in profile_payload.get("candidates", []) or []:
        candidate_id = candidate.get("candidate_id")
        if not candidate_id:
            continue
        aliases = _candidate_aliases(alias_graph, candidate_id)
        decision, reasons = _decision(candidate, aliases, collided_alias_ids)
        fp = candidate.get("profile_fingerprint") or {}
        strong_aliases = [
            alias for alias in aliases if alias.get("alias_type") in STRONG_ALIAS_TYPES
        ]
        supporting_aliases = [
            alias
            for alias in aliases
            if alias.get("alias_type") in SUPPORTING_ALIAS_TYPES
        ]
        hypotheses.append(
            {
                "hypothesis_id": f"identity-link-{candidate_id}",
                "candidate_id": candidate_id,
                "platform": fp.get("platform"),
                "username": fp.get("username"),
                "profile_url": fp.get("profile_url"),
                "analyst_state": _state(candidate),
                "identity_score": candidate.get("identity_score", 0),
                "decision": decision,
                "reasons": reasons,
                "alias_count": len(aliases),
                "strong_alias_count": len(strong_aliases),
                "supporting_alias_count": len(supporting_aliases),
                "collision_alias_count": len(
                    [
                        alias
                        for alias in aliases
                        if alias.get("alias_id") in collided_alias_ids
                    ]
                ),
                "evidence_ready": _evidence_ready(candidate),
                "dossier_assertion_ready": decision == "GO",
                "alias_ids": [alias.get("alias_id") for alias in aliases],
            }
        )
    counts = Counter(row["decision"] for row in hypotheses)
    return {
        "schema": SCHEMA,
        "stage": PIPELINE_STAGE,
        "pipeline_insert": "Entity Alias Graph -> Identity Link Hypothesis -> Analyst Review -> Dossier Assertion",
        "hypothesis_count": len(hypotheses),
        "go_count": counts.get("GO", 0),
        "hold_count": counts.get("HOLD", 0),
        "fail_count": counts.get("FAIL", 0),
        "hypotheses": hypotheses,
        "dossier_rule": "Identity link hypotheses may support assertions only after analyst review, captured evidence, and non-colliding alias support.",
    }


def export_identity_link_hypothesis_report(
    payload: dict[str, Any], fmt: str = "json"
) -> tuple[str, str, str]:
    fmt = (fmt or "json").lower().strip()
    if fmt in {"md", "markdown"}:
        lines = [
            "# Identity Link Hypotheses",
            "",
            f"Schema: `{SCHEMA}`",
            "",
            f"GO: {payload.get('go_count', 0)}",
            f"HOLD: {payload.get('hold_count', 0)}",
            f"FAIL: {payload.get('fail_count', 0)}",
            "",
            "## Rule",
            "",
            payload.get("dossier_rule", ""),
            "",
            "## Hypotheses",
            "",
        ]
        for row in payload.get("hypotheses", []):
            lines.extend(
                [
                    f"### {row.get('hypothesis_id')}",
                    f"- Decision: {row.get('decision')}",
                    f"- Candidate: {row.get('candidate_id')}",
                    f"- Alias support: strong={row.get('strong_alias_count')} supporting={row.get('supporting_alias_count')} collisions={row.get('collision_alias_count')}",
                    f"- Reasons: {'; '.join(row.get('reasons') or [])}",
                    "",
                ]
            )
        return "text/markdown", "identity-link-hypotheses.md", "\n".join(lines)
    return (
        "application/json",
        "identity-link-hypotheses.json",
        json.dumps(payload, indent=2, sort_keys=True),
    )

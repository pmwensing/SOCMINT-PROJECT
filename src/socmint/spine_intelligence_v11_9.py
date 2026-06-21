from __future__ import annotations

import os
from typing import Any

from . import spine_intelligence as legacy
from .alias_promotion_gates_v12_10_7_1 import (
    apply_promotion_gates_to_alias_graph,
    apply_promotion_gates_to_observation,
)
from .candidate_profile_review_v12_10_4 import apply_profile_review_decisions
from .connector_normalizers import normalize_connector_output
from .dossier_assertion_handoff_bundle_v12_10_10 import (
    build_dossier_assertion_handoff_bundle,
)
from .dossier_assertion_handoff_certification_v12_10_13 import (
    build_dossier_assertion_handoff_certification,
)
from .dossier_assertion_handoff_seal_v12_10_11 import (
    build_dossier_assertion_handoff_seal,
)
from .dossier_assertion_handoff_verification_v12_10_12 import (
    build_dossier_assertion_handoff_verification,
)
from .dossier_assertion_projection_v12_10_8 import build_dossier_assertion_projection
from .dossier_assertion_review_packet_v12_10_9 import (
    build_dossier_assertion_review_packet,
)
from .entity_alias_graph_v12_10_6 import build_entity_alias_graph
from .entity_alias_review_v12_10_7 import (
    apply_alias_review_decisions,
    promote_alias_to_assertion,
)
from .identity_link_hypothesis_v12_10_7 import build_identity_link_hypotheses
from .legacy_assertion_scrubber_v12_10_7_2 import (
    apply_assertion_scrub_gates,
    scrub_summary,
)
from .profile_evidence_capture_v12_10_5 import enrich_profile_payload_with_evidence
from .profile_fingerprint_v12_10_3 import build_profile_fingerprint_payload

INTELLIGENCE_SCHEMA = "socmint.spine_intelligence.v12_10_13"

promote_observation_to_assertion = legacy.promote_observation_to_assertion
review_spine_assertion = legacy.review_spine_assertion

REVIEWED_ASSERTION_STATES = {"confirmed", "rejected", "suppressed"}
DOSSIER_READY_ASSERTION_STATES = {"confirmed"}


def minimum_reviewed_assertions() -> int:
    try:
        return max(1, int(os.environ.get("SOCMINT_MINIMUM_REVIEWED_ASSERTIONS", "1")))
    except ValueError:
        return 1


def _profile_live_capture_enabled() -> bool:
    return os.environ.get("SOCMINT_PROFILE_LIVE_CAPTURE", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _run_badge(
    status: str, normalized_count: int, real_count: int, diagnostic_count: int
) -> str:
    state = str(status or "").lower()
    if real_count:
        return "real"
    if (
        state in {"dry_run", "skipped", "timeout", "failed"}
        or diagnostic_count
        or normalized_count == 0
    ):
        return "diagnostic"
    return "review"


def _explain_run(
    status: str, normalized_count: int, real_count: int, raw: dict[str, Any]
) -> str:
    state = str(status or "").lower()
    result = raw.get("result", {}) if isinstance(raw, dict) else {}
    stderr = str(result.get("stderr") or raw.get("stderr") or "").strip()
    if real_count:
        return "Connector produced dossier-grade observations. Review and promote/confirm as needed."
    if normalized_count:
        return "Connector produced normalized findings, but no stored dossier-grade observation is attached to this run yet."
    if state == "dry_run":
        return "Diagnostic/dry-run only. Rebuild with connector CLIs enabled or disable forced dry-run mode."
    if state in {"failed", "timeout", "skipped"}:
        return (
            stderr[:240]
            or f"Connector status is {state}; no dossier-grade enrichment was produced."
        )
    return "Connector completed but produced no normalized enrichment findings for this seed."


def _normalize_for_run(
    run: dict[str, Any], seed_by_id: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    seed = seed_by_id.get(run.get("seed_id"))
    raw = run.get("raw_result") or {}
    result = raw.get("result", {}) if isinstance(raw, dict) else {}
    if not seed or not isinstance(result, dict):
        return []
    try:
        return normalize_connector_output(
            run.get("connector"), seed.get("value"), seed.get("type"), result
        )
    except Exception as exc:
        return [
            {
                "type": "normalizer_error",
                "value": str(exc),
                "source": run.get("connector"),
                "confidence": 0.0,
            }
        ]


def _assertion_review_counts(assertions: list[dict[str, Any]]) -> dict[str, int]:
    reviewed = [
        item
        for item in assertions
        if item.get("validation_state") in REVIEWED_ASSERTION_STATES
    ]
    confirmed = [
        item
        for item in assertions
        if item.get("validation_state") in DOSSIER_READY_ASSERTION_STATES
    ]
    rejected = [
        item for item in assertions if item.get("validation_state") == "rejected"
    ]
    suppressed = [
        item for item in assertions if item.get("validation_state") == "suppressed"
    ]
    unreviewed = [
        item for item in assertions if item.get("validation_state") == "unreviewed"
    ]
    return {
        "reviewed_assertions": len(reviewed),
        "confirmed_assertions": len(confirmed),
        "rejected_assertions": len(rejected),
        "suppressed_assertions": len(suppressed),
        "unreviewed_assertions": len(unreviewed),
    }


def _alias_review_decision_count(alias_graph: dict[str, Any] | None) -> int:
    alias_review = (alias_graph or {}).get("alias_review") or {}
    clusters = alias_review.get("clusters") or {}
    decision_counts = alias_review.get("decision_counts") or {}
    reviewed = sum(
        int(decision_counts.get(key, 0) or 0)
        for key in ("confirmed", "rejected", "uncertain", "needs_more_evidence")
    )
    return reviewed + len(clusters)


def _dossier_readiness_gate(
    assertions: list[dict[str, Any]],
    profile_fingerprints: dict[str, Any] | None = None,
    alias_graph: dict[str, Any] | None = None,
    identity_links: dict[str, Any] | None = None,
    assertion_projection: dict[str, Any] | None = None,
    review_packet: dict[str, Any] | None = None,
    handoff_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    minimum = minimum_reviewed_assertions()
    counts = _assertion_review_counts(assertions)
    reviewed = counts["reviewed_assertions"]
    confirmed = counts["confirmed_assertions"]
    missing = max(0, minimum - reviewed)
    profile_counts = (profile_fingerprints or {}).get("review_decision_counts", {})
    unresolved_profiles = int(
        (profile_fingerprints or {}).get("needs_review_count", 0) or 0
    )
    evidence_capture = (profile_fingerprints or {}).get("evidence_capture", {})
    alias_collisions = int((alias_graph or {}).get("collision_count", 0) or 0)
    alias_review = (alias_graph or {}).get("alias_review", {})
    alias_review_decisions = _alias_review_decision_count(alias_graph)
    promotion_gates = (alias_graph or {}).get("promotion_gates", {})
    identity_hold = int((identity_links or {}).get("hold_count", 0) or 0)
    identity_go = int((identity_links or {}).get("go_count", 0) or 0)
    projection_ready = int((assertion_projection or {}).get("ready_count", 0) or 0)
    projection_blocked = int((assertion_projection or {}).get("blocked_count", 0) or 0)
    ready_packets = int((review_packet or {}).get("ready_packet_count", 0) or 0)
    blocked_packets = int((review_packet or {}).get("blocked_packet_count", 0) or 0)
    handoff_ready = int((handoff_bundle or {}).get("ready_count", 0) or 0)
    handoff_blocked = int((handoff_bundle or {}).get("blocked_count", 0) or 0)

    hard_holds: list[str] = []
    if unresolved_profiles > 0:
        hard_holds.append("candidate_profile_review_remaining")
    if alias_collisions > 0 and alias_review_decisions <= 0:
        hard_holds.append("alias_collisions_unreviewed")
    if identity_hold > 0:
        hard_holds.append("identity_link_hypotheses_on_hold")
    if identity_go <= 0 and (identity_links or {}).get("hypothesis_count", 0):
        hard_holds.append("no_go_identity_link_hypothesis")
    if projection_blocked > 0:
        hard_holds.append("dossier_assertion_projection_blocked")
    if projection_ready <= 0 and (assertion_projection or {}).get(
        "projection_count", 0
    ):
        hard_holds.append("no_ready_dossier_assertion_projection")
    if blocked_packets > 0:
        hard_holds.append("dossier_assertion_review_packet_blocked")
    if ready_packets <= 0 and (review_packet or {}).get("packet_count", 0):
        hard_holds.append("no_ready_dossier_assertion_review_packet")
    if handoff_blocked > 0:
        hard_holds.append("dossier_assertion_handoff_bundle_blocked")
    if handoff_ready <= 0 and (handoff_bundle or {}).get("total_count", 0):
        hard_holds.append("no_ready_dossier_assertion_handoff_bundle")
    if reviewed < minimum:
        hard_holds.append("minimum_assertions_not_reviewed")
    if confirmed <= 0:
        hard_holds.append("no_confirmed_assertion")

    status = "hold" if hard_holds else "pass"
    if reviewed < minimum:
        next_action = f"Review {missing} more assertion(s), then confirm at least one dossier-ready assertion."
    elif confirmed <= 0:
        next_action = "At least one reviewed assertion must be confirmed before the dossier is marked ready."
    elif unresolved_profiles:
        next_action = f"Review {unresolved_profiles} candidate profile link(s), using captured profile evidence before acceptance."
    elif alias_collisions and alias_review_decisions <= 0:
        next_action = f"Review {alias_collisions} reverse alias collision set(s) before treating identifiers as same-entity facts."
    elif identity_hold:
        next_action = f"Resolve {identity_hold} identity-link hypothesis hold(s) before promoting same-entity facts."
    elif identity_go <= 0 and (identity_links or {}).get("hypothesis_count", 0):
        next_action = "At least one identity-link hypothesis must be GO before same-entity support is dossier-ready."
    elif projection_ready <= 0 and (assertion_projection or {}).get(
        "projection_count", 0
    ):
        next_action = "Resolve dossier assertion projection blockers before treating identity links as assertion-ready."
    elif blocked_packets:
        next_action = f"Resolve {blocked_packets} assertion review packet blocker(s) before final confirmation."
    elif handoff_blocked:
        next_action = (
            f"Resolve {handoff_blocked} handoff bundle blocker(s) before final handoff."
        )
    elif handoff_ready <= 0 and (handoff_bundle or {}).get("total_count", 0):
        next_action = "Prepare at least one ready handoff bundle item before final dossier handoff."
    else:
        next_action = "Open Full Dossier v2."
    return {
        "status": status,
        "requires": (
            f"At least {minimum} reviewed assertion(s), including at least one confirmed assertion, are required. "
            "Candidate profile review must be complete. Alias collisions require analyst review. "
            "Asset/CDN URLs and non-phone numeric artifacts are blocked from promotion. "
            "Identity-link hypotheses must resolve to GO before same-entity support is dossier-ready."
        ),
        "hard_holds": hard_holds,
        "minimum_reviewed_assertions": minimum,
        "reviewed_assertions": reviewed,
        "confirmed_assertions": confirmed,
        "rejected_assertions": counts["rejected_assertions"],
        "suppressed_assertions": counts["suppressed_assertions"],
        "unreviewed_assertions": counts["unreviewed_assertions"],
        "missing_reviewed_assertions": missing,
        "candidate_profile_review": profile_counts,
        "candidate_profile_review_remaining": unresolved_profiles,
        "candidate_profile_evidence_capture": evidence_capture,
        "entity_alias_graph": {
            "alias_count": (alias_graph or {}).get("alias_count", 0),
            "edge_count": (alias_graph or {}).get("edge_count", 0),
            "collision_count": alias_collisions,
            "state_counts": (alias_graph or {}).get("state_counts", {}),
            "alias_review": alias_review,
            "alias_review_decision_count": alias_review_decisions,
            "promotion_gates": promotion_gates,
        },
        "identity_link_hypotheses": {
            "hypothesis_count": (identity_links or {}).get("hypothesis_count", 0),
            "go_count": identity_go,
            "hold_count": identity_hold,
            "fail_count": (identity_links or {}).get("fail_count", 0),
        },
        "dossier_assertion_projection": {
            "projection_count": (assertion_projection or {}).get("projection_count", 0),
            "ready_count": projection_ready,
            "blocked_count": projection_blocked,
        },
        "dossier_assertion_review_packet": {
            "packet_count": (review_packet or {}).get("packet_count", 0),
            "ready_packet_count": ready_packets,
            "blocked_packet_count": blocked_packets,
        },
        "dossier_assertion_handoff_bundle": {
            "ready_count": handoff_ready,
            "blocked_count": handoff_blocked,
        },
        "next_action": next_action,
    }


def spine_intelligence_payload(subject_id: int) -> dict[str, Any]:
    payload = legacy.spine_intelligence_payload(subject_id)
    payload["schema"] = INTELLIGENCE_SCHEMA

    for observation in payload.get("observations", []):
        apply_promotion_gates_to_observation(observation)

    seed_by_id = {seed["id"]: seed for seed in payload.get("seeds", [])}
    observations_by_run: dict[int, list[dict[str, Any]]] = {}
    diagnostics_by_run: dict[int, list[dict[str, Any]]] = {}
    for item in payload.get("observations", []):
        observations_by_run.setdefault(item.get("run_id"), []).append(item)
    for item in payload.get("diagnostics", []):
        diagnostics_by_run.setdefault(item.get("run_id"), []).append(item)

    real_runs = 0
    diagnostic_runs = 0
    for run in payload.get("runs", []):
        normalized = _normalize_for_run(run, seed_by_id)
        for finding in normalized:
            apply_promotion_gates_to_observation(finding)
        real_obs = observations_by_run.get(run.get("id"), [])
        diag_obs = diagnostics_by_run.get(run.get("id"), [])
        badge = _run_badge(
            run.get("status"), len(normalized), len(real_obs), len(diag_obs)
        )
        if badge == "real":
            real_runs += 1
        if badge == "diagnostic":
            diagnostic_runs += 1
        seed = seed_by_id.get(run.get("seed_id"), {})
        run.update(
            {
                "badge": badge,
                "is_real": badge == "real",
                "is_diagnostic": badge == "diagnostic",
                "seed_type": seed.get("type"),
                "seed_value": seed.get("value"),
                "normalized_findings": normalized,
                "finding_count": len(normalized),
                "observations": real_obs,
                "diagnostics": diag_obs,
                "real_observation_count": len(real_obs),
                "diagnostic_count": len(diag_obs),
                "explanation": _explain_run(
                    run.get("status"),
                    len(normalized),
                    len(real_obs),
                    run.get("raw_result") or {},
                ),
            }
        )

    summary = payload.setdefault("summary", {})
    assertions = apply_assertion_scrub_gates(payload.get("assertions", []))
    payload["assertions"] = assertions
    review_counts = _assertion_review_counts(assertions)
    profile_fingerprints = build_profile_fingerprint_payload(payload)
    profile_fingerprints = enrich_profile_payload_with_evidence(
        profile_fingerprints,
        subject_id,
        live_capture_enabled=_profile_live_capture_enabled(),
    )
    profile_fingerprints = apply_profile_review_decisions(
        profile_fingerprints, subject_id
    )
    alias_graph = build_entity_alias_graph(payload, profile_fingerprints)
    alias_graph = apply_promotion_gates_to_alias_graph(alias_graph)
    alias_graph = apply_alias_review_decisions(alias_graph, subject_id)
    alias_graph = apply_promotion_gates_to_alias_graph(alias_graph)
    identity_links = build_identity_link_hypotheses(alias_graph, profile_fingerprints)
    assertion_projection = build_dossier_assertion_projection(
        identity_links, alias_graph
    )
    review_packet = build_dossier_assertion_review_packet(assertion_projection)
    handoff_bundle = build_dossier_assertion_handoff_bundle(review_packet)
    handoff_seal = build_dossier_assertion_handoff_seal(handoff_bundle)
    handoff_verification = build_dossier_assertion_handoff_verification(
        handoff_bundle, handoff_seal
    )
    handoff_certification = build_dossier_assertion_handoff_certification(
        handoff_bundle, handoff_seal, handoff_verification
    )
    payload["profile_fingerprints"] = profile_fingerprints
    payload["entity_alias_graph"] = alias_graph
    payload["identity_link_hypotheses"] = identity_links
    payload["dossier_assertion_projection"] = assertion_projection
    payload["dossier_assertion_review_packet"] = review_packet
    payload["dossier_assertion_handoff_bundle"] = handoff_bundle
    payload["dossier_assertion_handoff_seal"] = handoff_seal
    payload["dossier_assertion_handoff_verification"] = handoff_verification
    payload["dossier_assertion_handoff_certification"] = handoff_certification
    promotion_scrub = scrub_summary(
        assertions, payload.get("observations", []), alias_graph
    )
    gate = _dossier_readiness_gate(
        assertions,
        profile_fingerprints,
        alias_graph,
        identity_links,
        assertion_projection,
        review_packet,
        handoff_bundle,
    )
    summary.update(review_counts)
    summary.update(
        {
            "real_run_count": real_runs,
            "diagnostic_run_count": diagnostic_runs,
            "minimum_reviewed_assertions": gate["minimum_reviewed_assertions"],
            "dossier_ready": gate["status"] == "pass",
            "needs_review": gate["status"] != "pass"
            or review_counts["unreviewed_assertions"] > 0
            or profile_fingerprints["needs_review_count"] > 0
            or alias_graph["collision_count"] > 0
            or identity_links["hold_count"] > 0
            or assertion_projection["blocked_count"] > 0
            or review_packet["blocked_packet_count"] > 0
            or handoff_bundle["blocked_count"] > 0,
            "dossier_readiness_gate": gate,
            "profile_candidate_count": profile_fingerprints["candidate_count"],
            "profile_collision_review_count": profile_fingerprints[
                "needs_review_count"
            ],
            "profile_dossier_ready_count": profile_fingerprints["dossier_ready_count"],
            "profile_review_decision_counts": profile_fingerprints.get(
                "review_decision_counts", {}
            ),
            "profile_evidence_capture": profile_fingerprints.get(
                "evidence_capture", {}
            ),
            "alias_count": alias_graph.get("alias_count", 0),
            "alias_edge_count": alias_graph.get("edge_count", 0),
            "alias_collision_count": alias_graph.get("collision_count", 0),
            "alias_type_counts": alias_graph.get("type_counts", {}),
            "alias_state_counts": alias_graph.get("state_counts", {}),
            "alias_review": alias_graph.get("alias_review", {}),
            "alias_promotion_gates": alias_graph.get("promotion_gates", {}),
            "promotion_scrub": promotion_scrub,
            "identity_link_hypothesis_count": identity_links.get("hypothesis_count", 0),
            "identity_link_go_count": identity_links.get("go_count", 0),
            "identity_link_hold_count": identity_links.get("hold_count", 0),
            "identity_link_fail_count": identity_links.get("fail_count", 0),
            "dossier_projection_count": assertion_projection.get("projection_count", 0),
            "dossier_projection_ready_count": assertion_projection.get(
                "ready_count", 0
            ),
            "dossier_projection_blocked_count": assertion_projection.get(
                "blocked_count", 0
            ),
            "dossier_review_packet_count": review_packet.get("packet_count", 0),
            "dossier_review_ready_packet_count": review_packet.get(
                "ready_packet_count", 0
            ),
            "dossier_review_blocked_packet_count": review_packet.get(
                "blocked_packet_count", 0
            ),
            "dossier_handoff_ready_count": handoff_bundle.get("ready_count", 0),
            "dossier_handoff_blocked_count": handoff_bundle.get("blocked_count", 0),
            "dossier_handoff_seal_hash": handoff_seal.get("bundle_hash_sha256", ""),
            "dossier_handoff_verification_status": handoff_verification.get(
                "status", "unknown"
            ),
            "dossier_handoff_verification_failures": handoff_verification.get(
                "failure_count", 0
            ),
            "dossier_handoff_certification_decision": handoff_certification.get(
                "decision", "unknown"
            ),
        }
    )
    return payload

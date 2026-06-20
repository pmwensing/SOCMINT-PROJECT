from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CASE_INTELLIGENCE_REVIEW_WORKSPACE_SCHEMA = (
    "socmint.case_intelligence_review_workspace.v18_0"
)
VERSION = "v18.0.0"
SESSION_KEY = "case_intelligence_review_history_v18_6"
MAX_HISTORY = 30

DECISIONS = {"approve_review", "needs_follow_up", "hold_delivery", "return_to_analyst"}


def _items(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    return (
        [deepcopy(item) for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    evidence = _items(payload, "evidence")
    claims = _items(payload, "claims")
    identities = _items(payload, "identities")
    entities = _items(payload, "entities")
    timeline = _items(payload, "timeline")
    contradictions = _items(payload, "contradictions")
    unresolved_claims = sum(
        1
        for item in claims
        if item.get("status") not in {"supported", "verified", "resolved"}
    )
    low_confidence = sum(
        1 for item in identities + entities if float(item.get("confidence") or 0) < 0.7
    )
    return {
        "evidence_count": len(evidence),
        "claim_count": len(claims),
        "identity_count": len(identities),
        "entity_count": len(entities),
        "timeline_event_count": len(timeline),
        "contradiction_count": len(contradictions),
        "unresolved_claim_count": unresolved_claims,
        "low_confidence_resolution_count": low_confidence,
        "dossier_ready": bool(payload.get("dossier_ready")),
        "export_ready": bool(payload.get("export_ready")),
    }


def _evidence_claim_panel(payload: dict[str, Any]) -> dict[str, Any]:
    evidence = _items(payload, "evidence")
    claims = _items(payload, "claims")
    evidence_ids = {item.get("evidence_id") or item.get("id") for item in evidence}
    rows = []
    for claim in claims:
        links = (
            claim.get("evidence_ids")
            if isinstance(claim.get("evidence_ids"), list)
            else []
        )
        missing = [item for item in links if item not in evidence_ids]
        rows.append(
            {
                **claim,
                "linked_evidence_count": len(links),
                "missing_evidence_ids": missing,
            }
        )
    return {
        "evidence": evidence,
        "claims": rows,
        "unsupported_claim_count": sum(
            1 for item in rows if not item.get("evidence_ids")
        ),
        "broken_link_count": sum(len(item["missing_evidence_ids"]) for item in rows),
        "specialist_href": "/claim-evidence-ledger",
    }


def _identity_panel(payload: dict[str, Any]) -> dict[str, Any]:
    identities = _items(payload, "identities")
    entities = _items(payload, "entities")
    candidates = identities + entities
    for item in candidates:
        item["review_required"] = float(item.get("confidence") or 0) < 0.7 or item.get(
            "status"
        ) in {"candidate", "unresolved"}
    return {
        "identities": identities,
        "entities": entities,
        "review_required_count": sum(
            1 for item in candidates if item.get("review_required")
        ),
        "specialist_href": "/entity-profile-intelligence",
    }


def _timeline_panel(payload: dict[str, Any]) -> dict[str, Any]:
    events = _items(payload, "timeline")
    events.sort(
        key=lambda item: str(item.get("occurred_at") or item.get("timestamp") or "")
    )
    contradictions = _items(payload, "contradictions")
    return {
        "events": events,
        "contradictions": contradictions,
        "open_contradiction_count": sum(
            1
            for item in contradictions
            if item.get("status") not in {"resolved", "dismissed"}
        ),
    }


def build_case_intelligence_review_workspace(
    case_id: str,
    payload: dict[str, Any] | None = None,
    *,
    history: list[dict[str, Any]] | None = None,
    operator: str | None = None,
) -> dict[str, Any]:
    safe = deepcopy(payload or {})
    summary = _summary(safe)
    blockers = []
    if summary["unresolved_claim_count"]:
        blockers.append(
            {"key": "unresolved_claims", "count": summary["unresolved_claim_count"]}
        )
    if summary["low_confidence_resolution_count"]:
        blockers.append(
            {
                "key": "low_confidence_resolutions",
                "count": summary["low_confidence_resolution_count"],
            }
        )
    if summary["contradiction_count"]:
        blockers.append(
            {"key": "contradictions", "count": summary["contradiction_count"]}
        )
    status = "ready_for_analyst_decision" if not blockers else "review_required"
    entries = [
        deepcopy(item)
        for item in (history or [])
        if isinstance(item, dict) and item.get("case_id") == case_id
    ]
    entries.sort(key=lambda item: str(item.get("recorded_at") or ""), reverse=True)
    return {
        "schema": CASE_INTELLIGENCE_REVIEW_WORKSPACE_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "case": deepcopy(
            safe.get("case")
            or {"case_id": case_id, "title": safe.get("title") or case_id}
        ),
        "status": status,
        "summary": summary,
        "evidence_claim_review": _evidence_claim_panel(safe),
        "identity_entity_review": _identity_panel(safe),
        "timeline_contradiction_review": _timeline_panel(safe),
        "blockers": blockers,
        "decision_options": sorted(DECISIONS),
        "review_history": {
            "entries": entries,
            "entry_count": len(entries),
            "operator": operator,
            "persistence": "flask_session_only",
        },
        "next_action": "record_analyst_decision"
        if not blockers
        else "resolve_case_review_items",
    }


def record_case_review_decision(
    case_id: str,
    payload: dict[str, Any],
    *,
    operator: str,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    decision = str(payload.get("decision") or "").strip()
    if decision not in DECISIONS:
        return {
            "status": "blocked",
            "blockers": [
                {"key": "unsupported_decision", "detail": decision or "missing"}
            ],
            "next_action": "choose_supported_review_decision",
        }
    timestamp = recorded_at or datetime.now(UTC).isoformat()
    return {
        "status": "recorded",
        "case_id": case_id,
        "operator": operator,
        "decision": decision,
        "note": str(payload.get("note") or "").strip(),
        "recorded_at": timestamp,
        "next_action": "review_case_intelligence_workspace",
    }


def append_case_review_history(
    history: list[dict[str, Any]] | None, decision: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = [deepcopy(item) for item in (history or []) if isinstance(item, dict)]
    if decision.get("status") == "recorded":
        rows.append(deepcopy(decision))
    return rows[-MAX_HISTORY:]


def build_v18_product_review_checkpoint(
    root: str | Path = ".", *, routes: list[Any] | None = None
) -> dict[str, Any]:
    root_path = Path(root)
    required = [
        "src/socmint/case_intelligence_review_workspace_v18.py",
        "src/socmint/case_intelligence_review_routes_v18.py",
        "src/socmint/templates/case_intelligence_review_workspace.html",
        "src/socmint/static/case_intelligence_review_v18.js",
        "scripts/run_v18_7_case_intelligence_browser_e2e.py",
    ]
    notes = [
        f"release/V18_{index}_{name}.md"
        for index, name in (
            (0, "CASE_INTELLIGENCE_REVIEW_WORKSPACE"),
            (1, "CASE_INTELLIGENCE_SUMMARY_CARDS"),
            (2, "EVIDENCE_AND_CLAIM_REVIEW_PANEL"),
            (3, "IDENTITY_AND_ENTITY_RESOLUTION_PANEL"),
            (4, "TIMELINE_AND_CONTRADICTION_REVIEW"),
            (5, "ANALYST_DECISION_ACTIONS"),
            (6, "CASE_REVIEW_SESSION_HISTORY"),
            (7, "PRODUCT_REVIEW_AND_BROWSER_E2E_CHECKPOINT"),
        )
    ]
    blockers = []
    for path in required + notes:
        if not (root_path / path).exists():
            blockers.append({"key": "missing_artifact", "detail": path})
    route_rules = {str(getattr(item, "rule", item)) for item in routes or []}
    expected_routes = {
        "/case-intelligence-review/<case_id>",
        "/api/v1/case-intelligence-review/<case_id>",
        "/api/v1/case-intelligence-review/<case_id>/decisions",
        "/api/v1/case-intelligence-review/<case_id>/history",
        "/api/v1/case-intelligence-review/product-review-checkpoint",
    }
    if routes is not None:
        for route in expected_routes - route_rules:
            blockers.append({"key": "missing_route", "detail": route})
    migrations = [
        str(path)
        for directory in (root_path / "migrations", root_path / "alembic")
        if directory.exists()
        for path in directory.rglob("*v18*")
    ]
    if migrations:
        blockers.append(
            {"key": "unexpected_migration", "detail": ", ".join(migrations)}
        )
    return {
        "schema": "socmint.case_intelligence_product_review_checkpoint.v18_7",
        "version": "v18.7.0",
        "status": "ready_for_browser_validation" if not blockers else "blocked",
        "ready": not blockers,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "migration_artifacts": migrations,
        "next_action": "run_case_intelligence_browser_e2e"
        if not blockers
        else "resolve_v18_product_review_blockers",
    }

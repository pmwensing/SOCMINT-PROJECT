from __future__ import annotations

from copy import deepcopy
from typing import Any

from .dossier_readiness_v13 import STATE_DRAFT_READY
from .dossier_readiness_v13 import STATE_EXPORTED
from .dossier_readiness_v13 import STATE_FINAL_READY
from .dossier_readiness_v13 import compute_dossier_readiness
from .v10_30_case_delivery_registry import build_case_delivery_registry_from_request
from .v10_31_human_approval_gate import build_human_approval_gate


CASE_DELIVERY_WORKSPACE_SCHEMA = "socmint.case_delivery_workspace.v15_0"
CASE_DELIVERY_GATE_SCHEMA = "socmint.case_delivery_workspace.v15_0.gate"
VERSION = "v15.0.0"

READY_DOSSIER_STATES = {STATE_DRAFT_READY, STATE_FINAL_READY, STATE_EXPORTED}
READY_DELIVERY_STATES = {"ready", "approved", "deliver_ready", "delivery_ready"}


def _dossier_readiness(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("dossier_readiness"), dict):
        return deepcopy(payload["dossier_readiness"])
    readiness_input = payload.get("readiness_input") if isinstance(payload.get("readiness_input"), dict) else {}
    return compute_dossier_readiness(readiness_input)


def _export_blockers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    explicit = payload.get("export_blockers")
    if isinstance(explicit, list):
        return [deepcopy(item) for item in explicit if isinstance(item, dict)]
    export_decision = payload.get("export_decision") if isinstance(payload.get("export_decision"), dict) else {}
    blockers = export_decision.get("blockers")
    return [deepcopy(item) for item in blockers if isinstance(item, dict)] if isinstance(blockers, list) else []


def _evidence_summary(payload: dict[str, Any], dossier: dict[str, Any]) -> dict[str, Any]:
    explicit = payload.get("evidence_summary")
    if isinstance(explicit, dict):
        summary = deepcopy(explicit)
        summary.setdefault("complete", bool(summary.get("complete")))
        return summary
    counts = dossier.get("counts") if isinstance(dossier.get("counts"), dict) else {}
    hash_mismatch_count = int(counts.get("hash_mismatch_count") or 0)
    finding_count = int(counts.get("finding_count") or 0)
    return {
        "complete": hash_mismatch_count == 0 and finding_count > 0,
        "finding_count": finding_count,
        "hash_mismatch_count": hash_mismatch_count,
    }


def _latest_delivery(registry: dict[str, Any]) -> dict[str, Any]:
    deliveries = registry.get("deliveries") if isinstance(registry.get("deliveries"), list) else []
    return deepcopy(deliveries[-1]) if deliveries and isinstance(deliveries[-1], dict) else {}


def _approval_gate(case_id: str, payload: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("approval_gate"), dict):
        return deepcopy(payload["approval_gate"])
    return build_human_approval_gate(
        case_id=case_id,
        registry=registry,
        delivery_id=payload.get("delivery_id"),
        decision=payload.get("approval_decision") or payload.get("decision"),
        operator=payload.get("operator"),
        notes=payload.get("approval_notes") or payload.get("notes"),
    )


def _has_delivery_input(payload: dict[str, Any]) -> bool:
    return any(
        isinstance(payload.get(key), dict) for key in ("registry", "dashboard", "index", "pack", "bundle")
    ) or isinstance(payload.get("dashboards"), list)


def _delivery_registry(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("registry"), dict):
        return deepcopy(payload["registry"])
    if _has_delivery_input(payload):
        return build_case_delivery_registry_from_request(case_id, payload)
    return {
        "schema": "socmint.v15.case_delivery_workspace.empty_registry",
        "version": VERSION,
        "case_id": case_id,
        "delivery_count": 0,
        "latest_readiness": None,
        "latest_delivery_id": None,
        "deliveries": [],
        "summary": {
            "case_id": case_id,
            "delivery_count": 0,
            "latest_readiness": None,
            "latest_delivery_id": None,
            "readiness_counts": {},
        },
    }


def _gate_check(key: str, label: str, ok: bool, detail: str, href: str | None = None) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "detail": detail,
        "href": href,
    }


def build_case_delivery_gate(
    *,
    case_id: str,
    dossier: dict[str, Any],
    evidence: dict[str, Any],
    export_blockers: list[dict[str, Any]],
    registry: dict[str, Any],
    approval: dict[str, Any],
) -> dict[str, Any]:
    latest_delivery = _latest_delivery(registry)
    dossier_state = dossier.get("state")
    delivery_readiness = latest_delivery.get("readiness") or registry.get("latest_readiness")
    approval_decision = approval.get("decision")
    checks = [
        _gate_check(
            "dossier_ready",
            "Dossier ready",
            dossier_state in READY_DOSSIER_STATES,
            f"dossier state is {dossier_state or 'unknown'}",
            "/subjects",
        ),
        _gate_check(
            "evidence_complete",
            "Evidence complete",
            bool(evidence.get("complete")),
            "evidence summary is complete" if evidence.get("complete") else "evidence is incomplete",
            "/evidence/integrity",
        ),
        _gate_check(
            "export_clear",
            "Export clear",
            len(export_blockers) == 0,
            "no export blockers" if not export_blockers else f"{len(export_blockers)} export blocker(s)",
            "/dossier/export-blockers",
        ),
        _gate_check(
            "delivery_registered",
            "Delivery registered",
            bool(latest_delivery.get("delivery_id")),
            "latest delivery is registered" if latest_delivery.get("delivery_id") else "no delivery registered",
            f"/api/v1/v10/final-delivery/cases/{case_id}/registry",
        ),
        _gate_check(
            "delivery_ready",
            "Delivery ready",
            str(delivery_readiness or "").lower() in READY_DELIVERY_STATES,
            f"delivery readiness is {delivery_readiness or 'unknown'}",
            "/api/v1/v10/final-delivery/console",
        ),
        _gate_check(
            "human_approved",
            "Human approved",
            approval_decision == "approved",
            f"approval decision is {approval_decision or 'missing'}",
            f"/api/v1/v10/final-delivery/cases/{case_id}/approval-gate",
        ),
    ]
    blockers = [check for check in checks if not check["ok"]]
    if not blockers:
        decision = "READY_FOR_DELIVERY"
        next_action = "record_delivery"
    elif {check["key"] for check in blockers} == {"human_approved"}:
        decision = "NEEDS_HUMAN_APPROVAL"
        next_action = "approve_delivery"
    else:
        decision = "BLOCKED"
        next_action = blockers[0]["key"]
    return {
        "schema": CASE_DELIVERY_GATE_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "decision": decision,
        "status": "pass" if not blockers else "needs_review",
        "next_action": next_action,
        "checks": checks,
        "blockers": blockers,
        "blocker_count": len(blockers),
    }


def build_case_delivery_workspace(case_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    dossier = _dossier_readiness(safe_payload)
    evidence = _evidence_summary(safe_payload, dossier)
    blockers = _export_blockers(safe_payload)
    registry = _delivery_registry(case_id, safe_payload)
    approval = _approval_gate(case_id, safe_payload, registry)
    gate = build_case_delivery_gate(
        case_id=case_id,
        dossier=dossier,
        evidence=evidence,
        export_blockers=blockers,
        registry=registry,
        approval=approval,
    )
    return {
        "schema": CASE_DELIVERY_WORKSPACE_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "gate": gate,
        "dossier_readiness": dossier,
        "evidence_summary": evidence,
        "export_blockers": blockers,
        "delivery_registry": registry,
        "approval_gate": approval,
        "latest_delivery": _latest_delivery(registry),
        "operator_links": [
            {"label": "Dossier readiness", "href": "/subjects"},
            {"label": "Evidence integrity", "href": "/evidence/integrity"},
            {"label": "Export blockers", "href": "/dossier/export-blockers"},
            {"label": "Release console", "href": "/operator/release-console"},
        ],
    }


def build_case_delivery_workspace_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return build_case_delivery_workspace(case_id, payload)

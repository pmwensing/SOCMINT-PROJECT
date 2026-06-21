from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from . import database
from .analytic_dossier_contribution_v30_6 import current_contribution_decisions
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details

SCHEMA = "socmint.publication_review_workspace.v31_0"
VERSION = "v31.0.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DOSSIER_CONTRACTS = (
    "src/socmint/dossier_assembly_workspace_v21_0.py",
    "src/socmint/dossier_assembly_import_workspace_v21_1.py",
    "src/socmint/dossier_final_export_package_v21_6.py",
    "src/socmint/dossier_release_workspace_v22_0.py",
    "src/socmint/dossier_release_authorization_v22_1.py",
    "src/socmint/dossier_release_preview_v22_2.py",
    "src/socmint/dossier_secure_distribution_v22_3.py",
    "src/socmint/dossier_release_history_v22_6.py",
)
RELEASE_ACTIONS = (
    "case_dossier_release_authorization",
    "case_dossier_release_preview",
    "case_dossier_secure_distribution",
    "case_dossier_delivery_receipt",
    "case_dossier_recipient_acknowledgement",
    "case_dossier_failed_delivery_review",
    "case_dossier_recall_request",
    "case_dossier_reissue_authorization",
)


def _release_records() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_(RELEASE_ACTIONS))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "case_id": row.target_value,
                "action": row.action,
                "actor": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def build_publication_review_workspace(root: str | Path | None = None) -> dict[str, Any]:
    database.ensure_configured()
    root_path = Path(root) if root is not None else REPO_ROOT
    contributions = current_contribution_decisions()
    approved = [item for item in contributions if item.get("decision") == "approved"]
    releases = _release_records()
    contracts = [
        {"path": path, "available": (root_path / path).exists()}
        for path in DOSSIER_CONTRACTS
    ]
    missing = [item["path"] for item in contracts if not item["available"]]
    by_case: dict[str, list[dict[str, Any]]] = {}
    for item in releases:
        by_case.setdefault(str(item.get("case_id") or "unknown"), []).append(item)
    drafts = [
        item
        for item in releases
        if item.get("action")
        in {"case_dossier_release_preview", "case_dossier_release_authorization"}
    ]
    published = [
        item
        for item in releases
        if item.get("action")
        in {"case_dossier_secure_distribution", "case_dossier_recipient_acknowledgement"}
    ]
    no_case = [item for item in approved if not item.get("case_id")]
    no_target = [item for item in approved if not item.get("target_section")]
    blockers: list[dict[str, Any]] = []
    if missing:
        blockers.append({"key": "dossier_contracts_missing", "count": len(missing), "paths": missing})
    if no_case:
        blockers.append({"key": "approved_contributions_missing_case_binding", "count": len(no_case)})
    if no_target:
        blockers.append({"key": "approved_contributions_missing_target_section", "count": len(no_target)})
    ready = bool(approved) and not blockers
    findings = []
    if approved:
        findings.append({"severity": "info", "key": "approved_v30_contributions_available", "count": len(approved)})
    else:
        findings.append({"severity": "medium", "key": "no_approved_v30_contributions", "count": 0})
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready" if ready else "needs_review",
        "read_only": True,
        "publication_ready": ready,
        "approved_contribution_inventory": approved,
        "approved_contribution_count": len(approved),
        "all_contribution_decision_count": len(contributions),
        "approved_contribution_case_count": len({str(i.get("case_id")) for i in approved if i.get("case_id")}),
        "dossier_contract_inventory": contracts,
        "dossier_contract_count": len(contracts),
        "missing_dossier_contract_count": len(missing),
        "release_record_inventory": releases,
        "release_record_count": len(releases),
        "release_action_counts": dict(sorted(Counter(str(i.get("action") or "unknown") for i in releases).items())),
        "draft_revision_inventory": drafts,
        "draft_revision_count": len(drafts),
        "published_revision_inventory": published,
        "published_revision_count": len(published),
        "release_history_case_count": len(by_case),
        "approved_with_release_history_count": len([i for i in approved if str(i.get("case_id") or "") in by_case]),
        "human_release_ready_count": len(approved) - len(no_case) - len(no_target),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "publication_findings": findings,
        "publication_finding_count": len(findings),
        "automatic_publication_performed": False,
        "release_approval_performed": False,
        "dossier_mutated": False,
        "published_revision_mutated": False,
        "connector_execution_performed": False,
        "next_action": "create_publication_candidate_contract" if ready else (blockers[0]["key"] if blockers else "await_approved_v30_contribution"),
    }

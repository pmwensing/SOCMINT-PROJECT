from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from . import database
from .analytic_dossier_contribution_v30_6 import current_contribution_decisions
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details
from .draft_dossier_revision_v31_2 import current_draft_revisions
from .editorial_validation_v31_3 import current_editorial_validations
from .human_release_approval_v31_4 import current_release_approvals
from .immutable_published_revision_v31_5 import current_published_revisions
from .publication_candidate_v31_1 import current_publication_candidates

SCHEMA = "socmint.publication_review_workspace.v31_0"
VERSION = "v31.5.0"
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
    candidates = current_publication_candidates()
    proposed_candidates = [item for item in candidates if item.get("candidate_state") == "proposed"]
    draft_revisions = current_draft_revisions()
    validations = current_editorial_validations()
    passed_validations = [item for item in validations if item.get("gate_status") == "passed"]
    needs_revision_validations = [item for item in validations if item.get("gate_status") == "needs_revision"]
    approvals = current_release_approvals()
    approved_releases = [item for item in approvals if item.get("result_status") == "approved"]
    held_releases = [item for item in approvals if item.get("result_status") == "held"]
    returned_releases = [item for item in approvals if item.get("result_status") == "returned"]
    published_revisions = current_published_revisions()
    releases = _release_records()
    contracts = [
        {"path": path, "available": (root_path / path).exists()}
        for path in DOSSIER_CONTRACTS
    ]
    missing = [item["path"] for item in contracts if not item["available"]]
    by_case: dict[str, list[dict[str, Any]]] = {}
    for item in releases:
        by_case.setdefault(str(item.get("case_id") or "unknown"), []).append(item)
    release_previews = [
        item
        for item in releases
        if item.get("action")
        in {"case_dossier_release_preview", "case_dossier_release_authorization"}
    ]
    distribution_records = [
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
    findings: list[dict[str, Any]] = []
    if approved:
        findings.append({"severity": "info", "key": "approved_v30_contributions_available", "count": len(approved)})
    else:
        findings.append({"severity": "medium", "key": "no_approved_v30_contributions", "count": 0})
    if proposed_candidates:
        findings.append({"severity": "info", "key": "proposed_publication_candidates_available", "count": len(proposed_candidates)})
    if draft_revisions:
        findings.append({"severity": "info", "key": "draft_dossier_revisions_available", "count": len(draft_revisions)})
    if passed_validations:
        findings.append({"severity": "info", "key": "editorial_validations_passed", "count": len(passed_validations)})
    if needs_revision_validations:
        findings.append({"severity": "medium", "key": "editorial_validations_need_revision", "count": len(needs_revision_validations)})
    if approved_releases:
        findings.append({"severity": "info", "key": "human_release_approvals_available", "count": len(approved_releases)})
    if published_revisions:
        findings.append({"severity": "info", "key": "immutable_published_revisions_available", "count": len(published_revisions)})
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready" if ready else "needs_review",
        "read_only": True,
        "publication_ready": ready,
        "approved_contribution_inventory": approved,
        "approved_contribution_count": len(approved),
        "all_contribution_decision_count": len(contributions),
        "approved_contribution_case_count": len({str(item.get("case_id")) for item in approved if item.get("case_id")}),
        "publication_candidate_inventory": candidates,
        "publication_candidate_count": len(candidates),
        "proposed_publication_candidate_count": len(proposed_candidates),
        "draft_dossier_revision_inventory": draft_revisions,
        "draft_dossier_revision_count": len(draft_revisions),
        "editorial_validation_inventory": validations,
        "editorial_validation_count": len(validations),
        "passed_editorial_validation_count": len(passed_validations),
        "needs_revision_validation_count": len(needs_revision_validations),
        "human_release_approval_inventory": approvals,
        "human_release_approval_count": len(approvals),
        "approved_release_count": len(approved_releases),
        "held_release_count": len(held_releases),
        "returned_release_count": len(returned_releases),
        "published_revision_inventory": published_revisions,
        "published_revision_count": len(published_revisions),
        "dossier_contract_inventory": contracts,
        "dossier_contract_count": len(contracts),
        "missing_dossier_contract_count": len(missing),
        "release_record_inventory": releases,
        "release_record_count": len(releases),
        "release_action_counts": dict(sorted(Counter(str(item.get("action") or "unknown") for item in releases).items())),
        "release_preview_inventory": release_previews,
        "release_preview_count": len(release_previews),
        "distribution_record_inventory": distribution_records,
        "distribution_record_count": len(distribution_records),
        "release_history_case_count": len(by_case),
        "approved_with_release_history_count": len([item for item in approved if str(item.get("case_id") or "") in by_case]),
        "human_release_ready_count": len(passed_validations),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "publication_findings": findings,
        "publication_finding_count": len(findings),
        "automatic_publication_performed": False,
        "release_approval_performed": bool(approvals),
        "dossier_mutated": False,
        "published_revision_mutated": False,
        "connector_execution_performed": False,
        "next_action": (
            "manage_supersession_and_revision_history"
            if published_revisions
            else (
                "create_immutable_published_revision"
                if approved_releases
                else (
                    "await_human_release_decision"
                    if held_releases
                    else (
                        "revise_draft_dossier_revision"
                        if returned_releases or needs_revision_validations
                        else (
                            "request_human_release_approval"
                            if passed_validations
                            else (
                                "run_editorial_validation_and_policy_gate"
                                if draft_revisions
                                else (
                                    "assemble_draft_dossier_revision"
                                    if proposed_candidates
                                    else (
                                        "create_publication_candidate_contract"
                                        if ready
                                        else (blockers[0]["key"] if blockers else "await_approved_v30_contribution")
                                    )
                                )
                            )
                        )
                    )
                )
            )
        ),
    }

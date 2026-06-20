from __future__ import annotations

from typing import Any

SCHEMA = "socmint.command_center_next_action.v13_0"


def dossier_readiness_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    subjects = payload.get("subjects") or []
    targets = payload.get("targets") or []
    findings_count = int(summary.get("findings_count") or 0)
    report_count = int(summary.get("report_count") or 0)

    if not subjects:
        return {
            "state": "blocked",
            "label": "No subject yet",
            "blockers": ["Create or import a subject before building a dossier."],
            "warnings": [],
        }
    if report_count > 0:
        return {
            "state": "exported",
            "label": "Dossier export exists",
            "blockers": [],
            "warnings": [],
        }

    blockers = []
    warnings = []
    if not targets:
        blockers.append("Add at least one seed or target to anchor collection.")
    if findings_count <= 0:
        warnings.append(
            "No findings are available yet; run or import collection before final export."
        )

    state = "blocked" if blockers else "draft_ready"
    return {
        "state": state,
        "label": "Draft dossier ready"
        if state == "draft_ready"
        else "Needs seed intake",
        "blockers": blockers,
        "warnings": warnings,
    }


def next_best_action_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    subjects = payload.get("subjects") or []
    targets = payload.get("targets") or []
    jobs = payload.get("jobs") or []
    guided = payload.get("guided_investigation") or {}
    dossier = dossier_readiness_from_payload(payload)

    queued_or_running = [
        job for job in jobs if job.get("status") in {"queued", "running"}
    ]
    failed_jobs = [job for job in jobs if job.get("status") == "failed"]
    findings_count = int(summary.get("findings_count") or 0)

    if not subjects:
        return {
            "key": "create_subject",
            "label": "Create or open a subject",
            "href": "/spine",
            "reason": "A dossier needs a primary subject or entity anchor.",
            "priority": "primary",
        }
    if not targets:
        return {
            "key": "add_seed",
            "label": "Add a seed or target",
            "href": "/targets",
            "reason": "Collection and review need at least one seed.",
            "priority": "primary",
        }
    if queued_or_running:
        return {
            "key": "process_jobs",
            "label": "Process queued jobs",
            "href": "/command-center/process-jobs",
            "reason": "Collection work is queued or running and should finish before review.",
            "priority": "primary",
        }
    if failed_jobs:
        return {
            "key": "review_failed_jobs",
            "label": "Review failed jobs",
            "href": "/jobs",
            "reason": "One or more collection jobs failed and may need retry or repair.",
            "priority": "primary",
        }
    if findings_count <= 0:
        return {
            "key": "run_collection",
            "label": "Run or import collection",
            "href": "/targets",
            "reason": "Seeds exist but no findings have been normalized yet.",
            "priority": "primary",
        }
    if int(guided.get("action_count") or 0) > 0:
        next_action = guided.get("next_action") or {}
        return {
            "key": "guided_next_action",
            "label": next_action.get("label") or "Do next guided action",
            "href": next_action.get("href")
            or guided.get("href", "/investigation/flow"),
            "reason": next_action.get("reason")
            or "Guided investigation has pending work.",
            "priority": "primary",
        }
    if dossier.get("state") != "exported":
        subject_id = (subjects[0] or {}).get("id")
        return {
            "key": "generate_dossier",
            "label": "Generate dossier",
            "href": f"/spine/subjects/{subject_id}/full-report",
            "reason": "Findings are available and should become a reviewable dossier.",
            "priority": "primary",
        }
    return {
        "key": "export_case_package",
        "label": "Open export center",
        "href": "/reports/export-center",
        "reason": "A dossier exists; package and verify it for review or handoff.",
        "priority": "primary",
    }


def command_center_next_action_payload(payload: dict[str, Any]) -> dict[str, Any]:
    dossier = dossier_readiness_from_payload(payload)
    next_action = next_best_action_from_payload(payload)
    return {
        "schema": SCHEMA,
        "base_schema": payload.get("schema"),
        "dossier_readiness": dossier,
        "next_best_action": next_action,
        "operator_flow": [
            "create_case_or_subject",
            "add_seed",
            "run_or_import_collection",
            "review_findings",
            "link_evidence",
            "generate_dossier",
            "export_case_package",
        ],
    }

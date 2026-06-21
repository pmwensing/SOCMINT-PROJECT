from __future__ import annotations

import json
from collections import Counter
from typing import Any

from . import database as db
from .full_report_history import full_report_export_history
from .dossier_export_gate import export_gate_decision
from .dossier_export_index import export_index
from .guided_investigation_v12_9 import guided_investigation_payload
from .narrative_export_v12_6_1 import narrative_dashboard_polish_payload
from .runtime_import_health import runtime_import_health_report
from .test_data_controls import is_smoke_label, test_data_summary
from .tor_production import hidden_service_status
from .v11_readiness import v11_readiness_summary

USERNAME_TOOLS = {"sherlock", "maigret", "social-analyzer", "social_analyzer"}
EMAIL_TOOLS = {"holehe", "h8mail", "emailrep", "breach", "email"}
PHONE_TOOLS = {"phoneinfoga", "phone", "numverify"}
URL_TOOLS = {"playwright", "exiftool", "metadata", "webcapture", "wayback"}


def _job_tools(job) -> list[str]:
    try:
        return list(json.loads(job.tools or "[]"))
    except Exception:
        return []


def tool_compatibility(target_type: str, tools: list[str]) -> dict[str, Any]:
    normalized = {tool.strip().lower() for tool in tools if tool.strip()}
    warnings = []
    suggestions = []
    compatible = True
    if target_type == "email" and normalized & USERNAME_TOOLS:
        compatible = False
        warnings.append(
            "Email targets do not work well with username-first tools such as Sherlock or Maigret."
        )
        suggestions.append(
            "Use email exposure/account-discovery connectors for email targets."
        )
    if target_type in {"username", "handle"} and not normalized & USERNAME_TOOLS:
        suggestions.append(
            "Username targets are usually best tested with Sherlock/Maigret-style tools."
        )
    if target_type == "phone" and not normalized & PHONE_TOOLS:
        suggestions.append("Phone targets need phone-specific enrichment tools.")
    if target_type in {"url", "domain"} and not normalized & URL_TOOLS:
        suggestions.append(
            "URL/domain targets benefit from web capture and metadata connectors."
        )
    if not tools:
        suggestions.append(
            "No tools selected. Choose tools matched to the seed type before running."
        )
    return {
        "compatible": compatible,
        "warnings": warnings,
        "suggestions": suggestions,
        "target_type": target_type,
        "tools": sorted(normalized),
    }


def _serialize_job(job) -> dict[str, Any]:
    tools = _job_tools(job)
    return {
        "id": job.id,
        "target": job.target_value,
        "target_type": job.target_type,
        "tools": tools,
        "enrich": bool(job.enrich),
        "status": job.status,
        "requested_by": job.requested_by,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error": job.error,
        "target_id": job.target_id,
        "compatibility": tool_compatibility(job.target_type, tools),
    }


def _serialize_target(target) -> dict[str, Any]:
    return {
        "id": target.id,
        "value": target.value,
        "type": target.type,
        "created_at": target.created_at.isoformat() if target.created_at else None,
    }


def _serialize_subject(subject) -> dict[str, Any]:
    history = full_report_export_history(subject.id, limit=5)
    label = subject.label or f"Subject {subject.id}"
    return {
        "id": subject.id,
        "label": label,
        "created_at": subject.created_at.isoformat() if subject.created_at else None,
        "latest_report_available": bool(history.get("exports")),
        "latest_report_name": (history.get("exports") or [{}])[0].get("name"),
        "report_count": history.get("count", 0),
        "is_test_data": is_smoke_label(label),
    }


def _narrative_card(subjects: list[Any]) -> dict[str, Any]:
    subject_id = subjects[0].id if subjects else None
    try:
        payload = narrative_dashboard_polish_payload(subject_id=subject_id)
        confidence = payload.get("narrative_confidence_card") or {}
        return {
            "status": "ready"
            if confidence.get("rating") not in {None, "insufficient"}
            else "needs_data",
            "subject_id": subject_id,
            "rating": confidence.get("rating", "insufficient"),
            "score": confidence.get("score", 0),
            "timeline_events": len(payload.get("events", [])),
            "contradiction_actions": len(
                payload.get("contradiction_review_actions", [])
            ),
            "href": f"/narrative/storyboard?subject_id={subject_id}"
            if subject_id
            else "/narrative/storyboard",
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "subject_id": subject_id,
            "rating": "unavailable",
            "score": 0,
            "timeline_events": 0,
            "contradiction_actions": 0,
            "href": "/narrative/storyboard",
            "error": str(exc),
        }


def _guided_card(subjects: list[Any]) -> dict[str, Any]:
    subject_id = subjects[0].id if subjects else None
    try:
        payload = guided_investigation_payload(subject_id=subject_id)
        return {
            "status": payload.get("readiness", "yellow"),
            "score": payload.get("readiness_score", 0),
            "subject_id": subject_id,
            "action_count": len(payload.get("action_queue", [])),
            "next_action": payload.get("next_action", {}),
            "progress_rail": payload.get("progress_rail", []),
            "href": f"/investigation/flow?subject_id={subject_id}"
            if subject_id
            else "/investigation/flow",
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "score": 0,
            "subject_id": subject_id,
            "action_count": 0,
            "next_action": {
                "label": "Open guided investigation",
                "href": "/investigation/flow",
                "reason": str(exc),
            },
            "progress_rail": [],
            "href": "/investigation/flow",
            "error": str(exc),
        }


def _export_gate_card() -> dict[str, Any]:
    try:
        index = export_index()
        decisions = []
        for entry in index.get("entries", []):
            case_id = entry.get("case_id")
            subject_id = entry.get("subject_id")
            if not case_id or not subject_id:
                continue
            decision = export_gate_decision(
                subject_id=str(subject_id), case_id=str(case_id)
            )
            decisions.append(
                {
                    "case_id": case_id,
                    "subject_id": subject_id,
                    "decision": decision.get("decision"),
                    "blockers": decision.get("blockers", []),
                    "href": f"/dossier/export-blockers?case_id={case_id}&subject_id={subject_id}",
                }
            )
        blocked = [item for item in decisions if item["decision"] != "allow"]
        allowed = [item for item in decisions if item["decision"] == "allow"]
        return {
            "status": "blocked" if blocked else "ready" if allowed else "no_exports",
            "export_count": len(decisions),
            "allowed_count": len(allowed),
            "blocked_count": len(blocked),
            "blocked_exports": blocked[:5],
            "href": blocked[0]["href"] if blocked else "/dossier/export-blockers",
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "export_count": 0,
            "allowed_count": 0,
            "blocked_count": 0,
            "blocked_exports": [],
            "href": "/dossier/export-blockers",
            "error": str(exc),
        }


def command_center_payload() -> dict[str, Any]:
    db.ensure_configured()
    session = db.Session()
    try:
        jobs = (
            session.query(db.ScanJob)
            .order_by(db.ScanJob.created_at.desc())
            .limit(25)
            .all()
        )
        targets = (
            session.query(db.Target)
            .order_by(db.Target.created_at.desc())
            .limit(10)
            .all()
        )
        subjects = (
            session.query(db.SpineSubject)
            .order_by(db.SpineSubject.created_at.desc())
            .limit(10)
            .all()
        )
        connector_runs = (
            session.query(db.SpineConnectorRun)
            .order_by(db.SpineConnectorRun.created_at.desc())
            .limit(10)
            .all()
        )
        findings_count = session.query(db.Finding).count()
        test_data = test_data_summary()
        runtime_import_health = runtime_import_health_report()
        readiness = v11_readiness_summary()
        narrative = _narrative_card(subjects)
        guided = _guided_card(subjects)
        export_gate = _export_gate_card()
        total_report_count = 0
        for subject in subjects:
            try:
                total_report_count += int(
                    full_report_export_history(subject.id, limit=1).get("count", 0)
                )
            except Exception:
                pass
        try:
            tor_status = hidden_service_status("socmint")
        except Exception as exc:
            tor_status = {
                "schema": "socmint.tor_production.v8_4_0",
                "status": "unavailable",
                "enabled": False,
                "onion_hostname": None,
                "error": str(exc),
            }
        statuses = Counter(job.status for job in jobs)
        queued_count = statuses.get("queued", 0)
        running_count = statuses.get("running", 0)
        failed_jobs = [job for job in jobs if job.status == "failed"]
        completed_jobs = [job for job in jobs if job.status == "completed"]
        serialized_jobs = [_serialize_job(job) for job in jobs]
        compatibility_warnings = [
            job for job in serialized_jobs if job["compatibility"]["warnings"]
        ]
        latest_processed = completed_jobs[0] if completed_jobs else None
        return {
            "schema": "socmint.command_center.v12_9_1",
            "summary": {
                "subject_count": len(subjects),
                "target_count": len(targets),
                "job_count": len(jobs),
                "queued_jobs": queued_count,
                "running_jobs": running_count,
                "failed_jobs": len(failed_jobs),
                "completed_jobs": len(completed_jobs),
                "spine_connector_runs": len(connector_runs),
                "findings_count": findings_count,
                "report_count": total_report_count,
                "worker_status": "attention"
                if (queued_count or running_count or failed_jobs)
                else "healthy",
                "tor_status": tor_status.get("status", "unknown"),
                "tor_enabled": bool(tor_status.get("enabled")),
                "tor_onion_hostname": tor_status.get("onion_hostname"),
                "test_subject_count": (test_data.get("counts") or {}).get(
                    "subjects", 0
                ),
                "test_data_status": test_data.get("status"),
                "runtime_import_status": runtime_import_health.get("status"),
                "v11_readiness_status": readiness.get("status"),
                "v11_readiness_percentage": readiness.get("percentage"),
                "narrative_rating": narrative.get("rating"),
                "narrative_score": narrative.get("score"),
                "guided_readiness": guided.get("status"),
                "guided_score": guided.get("score"),
                "guided_action_count": guided.get("action_count"),
                "export_gate_status": export_gate.get("status"),
                "export_count": export_gate.get("export_count"),
                "export_blocker_count": export_gate.get("blocked_count"),
                "export_allowed_count": export_gate.get("allowed_count"),
                "worker_hint": "Jobs are queued. Run Process queued jobs now or start process-jobs."
                if queued_count
                else "No queued jobs waiting.",
            },
            "tor": tor_status,
            "test_data": test_data,
            "runtime_import_health": runtime_import_health,
            "v11_readiness": readiness,
            "narrative_confidence": narrative,
            "guided_investigation": guided,
            "export_gate": export_gate,
            "subjects": [_serialize_subject(subject) for subject in subjects],
            "targets": [_serialize_target(target) for target in targets],
            "jobs": serialized_jobs,
            "compatibility_warnings": compatibility_warnings,
            "latest_processed_job": _serialize_job(latest_processed)
            if latest_processed
            else None,
            "next_actions": [
                {
                    "label": "Open guided investigation flow",
                    "href": guided.get("href", "/investigation/flow"),
                    "priority": "primary",
                },
                {
                    "label": "Do next guided action",
                    "href": (guided.get("next_action") or {}).get(
                        "href", "/investigation/flow"
                    ),
                    "priority": "primary",
                },
                {
                    "label": "Create / open subject",
                    "href": "/spine",
                    "priority": "primary",
                },
                {
                    "label": "Review narrative storyboard",
                    "href": narrative.get("href", "/narrative/storyboard"),
                    "priority": "primary",
                },
                {
                    "label": "Review queued jobs",
                    "href": "/jobs",
                    "priority": "secondary",
                },
                {
                    "label": "Open enrichment review",
                    "href": "/spine/enrichment-review",
                    "priority": "secondary",
                },
                {
                    "label": "Open export center",
                    "href": "/reports/export-center",
                    "priority": "secondary",
                },
                {
                    "label": "Review export blockers",
                    "href": export_gate.get("href", "/dossier/export-blockers"),
                    "priority": "secondary",
                },
                {
                    "label": "Review v11 readiness",
                    "href": "/api/v1/admin/v11/readiness-summary",
                    "priority": "secondary",
                },
            ],
            "tool_guidance": [
                {
                    "target_type": "username",
                    "recommended": "Sherlock, Maigret, Social Analyzer",
                },
                {
                    "target_type": "email",
                    "recommended": "Holehe, h8mail, email exposure/account-discovery connectors",
                },
                {
                    "target_type": "phone",
                    "recommended": "PhoneInfoga or phone-specific enrichment",
                },
                {
                    "target_type": "url/domain",
                    "recommended": "Playwright capture, metadata extraction, web archive checks",
                },
            ],
        }
    finally:
        session.close()

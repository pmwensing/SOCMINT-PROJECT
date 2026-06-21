from __future__ import annotations

from pathlib import Path
from typing import Any

from .dossier_export_audit import audit_summary
from .dossier_export_gate import export_gate_decision
from .dossier_export_gate import export_gate_summary
from .dossier_export_store import DEFAULT_EXPORT_ROOT
from .dossier_export_store import load_export_manifest
from .dossier_export_verification import export_verification_summary

DOSSIER_EXPORT_CERTIFICATION_SCHEMA = "socmint.dossier_export_certification.v10_11_0"


def artifact_digest_summary(
    subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT
) -> dict[str, Any]:
    manifest = load_export_manifest(subject_id=subject_id, case_id=case_id, root=root)
    artifacts = [
        {
            "filename": item.get("filename"),
            "media_type": item.get("media_type"),
            "sha256": item.get("sha256"),
        }
        for item in manifest.get("artifacts", [])
    ]
    return {
        "schema": DOSSIER_EXPORT_CERTIFICATION_SCHEMA,
        "subject_id": subject_id,
        "case_id": case_id,
        "status": manifest.get("status", "missing"),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def export_certification_bundle(
    subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT
) -> dict[str, Any]:
    gate = export_gate_summary(subject_id=subject_id, case_id=case_id, root=root)
    decision = export_gate_decision(subject_id=subject_id, case_id=case_id, root=root)
    verification = export_verification_summary(
        subject_id=subject_id, case_id=case_id, root=root
    )
    audit = audit_summary(case_id=case_id, subject_id=subject_id, root=root)
    artifacts = artifact_digest_summary(
        subject_id=subject_id, case_id=case_id, root=root
    )
    certified = decision.get("decision") == "allow" and gate.get("ready") is True
    return {
        "schema": DOSSIER_EXPORT_CERTIFICATION_SCHEMA,
        "status": "certified" if certified else "not_certified",
        "certified": certified,
        "subject_id": subject_id,
        "case_id": case_id,
        "decision": decision,
        "gate": gate,
        "verification": verification,
        "audit": audit,
        "artifacts": artifacts,
    }


def export_certification_summary(
    subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT
) -> dict[str, Any]:
    bundle = export_certification_bundle(
        subject_id=subject_id, case_id=case_id, root=root
    )
    return {
        "schema": DOSSIER_EXPORT_CERTIFICATION_SCHEMA,
        "status": bundle["status"],
        "certified": bundle["certified"],
        "subject_id": subject_id,
        "case_id": case_id,
        "decision": bundle["decision"].get("decision"),
        "blockers": bundle["gate"].get("blockers", []),
        "verification_status": bundle["verification"].get("status"),
        "audit_event_count": bundle["audit"].get("event_count", 0),
        "artifact_count": bundle["artifacts"].get("artifact_count", 0),
    }


def export_certification_statement(
    subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT
) -> dict[str, Any]:
    summary = export_certification_summary(
        subject_id=subject_id, case_id=case_id, root=root
    )
    if summary["certified"]:
        statement = "Export bundle is certified: gate allowed, verification passed, and audit coverage is present."
    else:
        statement = "Export bundle is not certified: one or more gate, verification, audit, or artifact checks require review."
    return {
        "schema": DOSSIER_EXPORT_CERTIFICATION_SCHEMA,
        "subject_id": subject_id,
        "case_id": case_id,
        "certified": summary["certified"],
        "statement": statement,
        "summary": summary,
    }

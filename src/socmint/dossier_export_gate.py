from __future__ import annotations

from pathlib import Path
from typing import Any

from .dossier_export_store import DEFAULT_EXPORT_ROOT
from .dossier_export_verification import export_verification_report
from .dossier_export_verification import export_verification_summary

DOSSIER_EXPORT_GATE_SCHEMA = "socmint.dossier_export_gate.v10_10_0"


def export_gate_report(subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    verification = export_verification_report(subject_id=subject_id, case_id=case_id, root=root)
    checks = {
        "artifact_hashes": verification.get("checks", {}).get("artifact_hashes") is True,
        "manifest_index": verification.get("checks", {}).get("manifest_index") is True,
        "audit_coverage": verification.get("checks", {}).get("audit_coverage") is True,
    }
    ready = all(checks.values())
    blockers = [name for name, passed in checks.items() if not passed]
    return {
        "schema": DOSSIER_EXPORT_GATE_SCHEMA,
        "status": "ready" if ready else "blocked",
        "subject_id": subject_id,
        "case_id": case_id,
        "ready": ready,
        "blockers": blockers,
        "checks": checks,
        "verification_status": verification.get("status"),
        "verification": verification,
    }


def export_gate_summary(subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    gate = export_gate_report(subject_id=subject_id, case_id=case_id, root=root)
    verification = export_verification_summary(subject_id=subject_id, case_id=case_id, root=root)
    return {
        "schema": DOSSIER_EXPORT_GATE_SCHEMA,
        "status": gate["status"],
        "ready": gate["ready"],
        "subject_id": subject_id,
        "case_id": case_id,
        "blockers": gate["blockers"],
        "passed_checks": sum(1 for value in gate["checks"].values() if value),
        "total_checks": len(gate["checks"]),
        "verification_summary": verification,
    }


def export_gate_decision(subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    summary = export_gate_summary(subject_id=subject_id, case_id=case_id, root=root)
    return {
        "schema": DOSSIER_EXPORT_GATE_SCHEMA,
        "decision": "allow" if summary["ready"] else "deny",
        "reason": "all verification checks passed" if summary["ready"] else "verification blockers present",
        "subject_id": subject_id,
        "case_id": case_id,
        "blockers": summary["blockers"],
    }

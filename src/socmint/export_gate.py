from __future__ import annotations

from typing import Any

from .export_quality import export_quality_report

EXPORT_GATE_SCHEMA = "socmint.export_gate.v9_0_3"
DEFAULT_MIN_SCORE = 75


def export_preflight(
    subject_id: int, external: bool = True, min_score: int = DEFAULT_MIN_SCORE
) -> dict[str, Any]:
    quality = export_quality_report(subject_id, redacted=True)
    readiness = quality.get("readiness") or {}
    warnings = list(quality.get("warnings") or [])
    blockers: list[str] = []
    if readiness.get("state") == "blocked":
        blockers.append("Dossier readiness is blocked.")
    if quality.get("score", 0) < min_score:
        blockers.append(f"Export quality score is below {min_score}.")
    if external and quality.get("redaction", {}).get("coverage_ratio", 0) < 1:
        blockers.append(
            "External export requires complete sensitive assertion redaction coverage."
        )
    if (
        external
        and quality.get("counts", {}).get("assertions", 0)
        and not quality.get("counts", {}).get("traceable_entries", 0)
    ):
        blockers.append("External export requires source/evidence traceability.")
    allowed = not blockers
    return {
        "schema": EXPORT_GATE_SCHEMA,
        "subject_id": subject_id,
        "allowed": allowed,
        "external": external,
        "min_score": min_score,
        "blockers": blockers,
        "warnings": warnings,
        "quality": quality,
    }


def export_preflight_summary(subject_id: int) -> dict[str, Any]:
    payload = export_preflight(subject_id, external=True)
    return {
        "schema": EXPORT_GATE_SCHEMA,
        "subject_id": subject_id,
        "allowed": payload["allowed"],
        "blocker_count": len(payload["blockers"]),
        "warning_count": len(payload["warnings"]),
        "score": payload["quality"].get("score"),
        "grade": payload["quality"].get("grade"),
    }

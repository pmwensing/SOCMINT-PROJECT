from __future__ import annotations

from typing import Any

from .ultimate_dossier import dossier_export_manifest
from .ultimate_dossier import redacted_dossier_payload
from .ultimate_dossier import ultimate_dossier_payload

EXPORT_QUALITY_SCHEMA = "socmint.export_quality.v8_6_0"


def _score_bool(value: bool, points: int) -> int:
    return points if value else 0


def redaction_coverage(payload: dict[str, Any], redacted: dict[str, Any]) -> dict[str, Any]:
    sensitive_types = set(redacted.get("redaction", {}).get("sensitive_types") or [])
    original_sensitive = [item for item in payload.get("assertions", []) if item.get("type") in sensitive_types]
    redacted_sensitive = [item for item in redacted.get("assertions", []) if item.get("type") in sensitive_types]
    protected = [item for item in redacted_sensitive if str(item.get("value", "")).startswith("redacted:")]
    return {
        "sensitive_assertion_count": len(original_sensitive),
        "redacted_assertion_count": len(protected),
        "coverage_ratio": 1.0 if not original_sensitive else round(len(protected) / len(original_sensitive), 3),
        "sensitive_types": sorted(sensitive_types),
    }


def export_quality_report(subject_id: int, redacted: bool = True) -> dict[str, Any]:
    payload = ultimate_dossier_payload(subject_id)
    manifest = dossier_export_manifest(payload, redacted=redacted)
    redacted_payload = redacted_dossier_payload(payload)
    redaction = redaction_coverage(payload, redacted_payload)
    readiness = payload.get("readiness") or {}
    parity = manifest.get("parity") or {}
    assertions = payload.get("assertions") or []
    traceability = payload.get("traceability") or []
    traceable = [item for item in traceability if item.get("source_refs") or item.get("evidence_refs")]
    confirmed = [item for item in assertions if item.get("validation_state") == "confirmed"]

    score = 0
    score += _score_bool(manifest.get("assertion_count") == manifest.get("csv_assertion_count"), 20)
    score += _score_bool(parity.get("csv_matches_assertions", False), 20)
    score += _score_bool(readiness.get("state") != "blocked", 20)
    score += _score_bool(redaction.get("coverage_ratio", 0) >= 1, 20)
    score += _score_bool(bool(traceable) or not assertions, 10)
    score += _score_bool(bool(confirmed) or not assertions, 10)

    warnings = []
    if manifest.get("assertion_count") != manifest.get("csv_assertion_count"):
        warnings.append("CSV assertion count does not match JSON assertion count.")
    if readiness.get("state") == "blocked":
        warnings.append("Dossier readiness is blocked.")
    if redaction.get("coverage_ratio", 0) < 1:
        warnings.append("Sensitive assertion redaction coverage is incomplete.")
    if assertions and not traceable:
        warnings.append("No assertions have source/evidence traceability references.")
    if assertions and not confirmed:
        warnings.append("No confirmed assertions are present.")

    return {
        "schema": EXPORT_QUALITY_SCHEMA,
        "subject_id": subject_id,
        "score": score,
        "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D",
        "warnings": warnings,
        "manifest": manifest,
        "redaction": redaction,
        "readiness": readiness,
        "counts": {
            "assertions": len(assertions),
            "confirmed_assertions": len(confirmed),
            "traceability_entries": len(traceability),
            "traceable_entries": len(traceable),
        },
    }


def export_quality_summary(subject_id: int) -> dict[str, Any]:
    report = export_quality_report(subject_id, redacted=True)
    return {
        "schema": EXPORT_QUALITY_SCHEMA,
        "subject_id": subject_id,
        "score": report["score"],
        "grade": report["grade"],
        "warning_count": len(report["warnings"]),
        "warnings": report["warnings"],
    }

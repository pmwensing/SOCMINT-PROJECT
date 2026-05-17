from __future__ import annotations

from typing import Any

from . import spine_intelligence as legacy
from .connector_normalizers import normalize_connector_output

INTELLIGENCE_SCHEMA = "socmint.spine_intelligence.v11_9"

promote_observation_to_assertion = legacy.promote_observation_to_assertion
review_spine_assertion = legacy.review_spine_assertion


def _run_badge(status: str, normalized_count: int, real_count: int, diagnostic_count: int) -> str:
    state = str(status or "").lower()
    if real_count:
        return "real"
    if state in {"dry_run", "skipped", "timeout", "failed"} or diagnostic_count or normalized_count == 0:
        return "diagnostic"
    return "review"


def _explain_run(status: str, normalized_count: int, real_count: int, raw: dict[str, Any]) -> str:
    state = str(status or "").lower()
    result = raw.get("result", {}) if isinstance(raw, dict) else {}
    stderr = str(result.get("stderr") or raw.get("stderr") or "").strip()
    if real_count:
        return "Connector produced dossier-grade observations. Review and promote/confirm as needed."
    if normalized_count:
        return "Connector produced normalized findings, but no stored dossier-grade observation is attached to this run yet."
    if state == "dry_run":
        return "Diagnostic/dry-run only. Rebuild with connector CLIs enabled or disable forced dry-run mode."
    if state in {"failed", "timeout", "skipped"}:
        return stderr[:240] or f"Connector status is {state}; no dossier-grade enrichment was produced."
    return "Connector completed but produced no normalized enrichment findings for this seed."


def _normalize_for_run(run: dict[str, Any], seed_by_id: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    seed = seed_by_id.get(run.get("seed_id"))
    raw = run.get("raw_result") or {}
    result = raw.get("result", {}) if isinstance(raw, dict) else {}
    if not seed or not isinstance(result, dict):
        return []
    try:
        return normalize_connector_output(
            run.get("connector"),
            seed.get("value"),
            seed.get("type"),
            result,
        )
    except Exception as exc:
        return [{"type": "normalizer_error", "value": str(exc), "source": run.get("connector"), "confidence": 0.0}]


def spine_intelligence_payload(subject_id: int) -> dict[str, Any]:
    payload = legacy.spine_intelligence_payload(subject_id)
    payload["schema"] = INTELLIGENCE_SCHEMA

    seed_by_id = {seed["id"]: seed for seed in payload.get("seeds", [])}
    observations_by_run: dict[int, list[dict[str, Any]]] = {}
    diagnostics_by_run: dict[int, list[dict[str, Any]]] = {}
    for item in payload.get("observations", []):
        observations_by_run.setdefault(item.get("run_id"), []).append(item)
    for item in payload.get("diagnostics", []):
        diagnostics_by_run.setdefault(item.get("run_id"), []).append(item)

    real_runs = 0
    diagnostic_runs = 0
    for run in payload.get("runs", []):
        normalized = _normalize_for_run(run, seed_by_id)
        real_obs = observations_by_run.get(run.get("id"), [])
        diag_obs = diagnostics_by_run.get(run.get("id"), [])
        badge = _run_badge(run.get("status"), len(normalized), len(real_obs), len(diag_obs))
        if badge == "real":
            real_runs += 1
        if badge == "diagnostic":
            diagnostic_runs += 1
        seed = seed_by_id.get(run.get("seed_id"), {})
        run.update({
            "badge": badge,
            "is_real": badge == "real",
            "is_diagnostic": badge == "diagnostic",
            "seed_type": seed.get("type"),
            "seed_value": seed.get("value"),
            "normalized_findings": normalized,
            "finding_count": len(normalized),
            "observations": real_obs,
            "diagnostics": diag_obs,
            "real_observation_count": len(real_obs),
            "diagnostic_count": len(diag_obs),
            "explanation": _explain_run(run.get("status"), len(normalized), len(real_obs), run.get("raw_result") or {}),
        })

    summary = payload.setdefault("summary", {})
    confirmed = int(summary.get("confirmed_assertions") or 0)
    summary.update({
        "real_run_count": real_runs,
        "diagnostic_run_count": diagnostic_runs,
        "dossier_ready": confirmed > 0,
        "dossier_readiness_gate": {
            "status": "pass" if confirmed > 0 else "hold",
            "requires": "At least one reviewed/confirmed assertion is required before the dossier is marked ready.",
            "confirmed_assertions": confirmed,
            "next_action": "Open Full Dossier v2." if confirmed > 0 else "Promote a real observation, then confirm at least one assertion.",
        },
    })
    return payload

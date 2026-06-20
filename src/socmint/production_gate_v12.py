from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .assertion_trust_gate_v12_8_1 import assertion_release_gate
from .assertion_trust_gate_v12_8_1 import assertion_trust_summary
from .entity_dossier_v2 import export_full_entity_dossier_v2
from .entity_dossier_v2 import sha256_file
from .integrity_gate_v12_7_1 import evidence_integrity_summary
from .integrity_gate_v12_7_1 import integrity_release_gate
from .narrative_export_v12_6_1 import dossier_story_layer
from .spine_intelligence_v11_9 import spine_intelligence_payload

PRODUCTION_GATE_SCHEMA = "socmint.production_gate.v12_0"
FULL_DOSSIER_SCHEMA = "socmint.full_dossier_pack.v12_0"

CORE_CONNECTORS = {"maigret", "sherlock", "socialscan", "holehe", "h8mail"}
OPTIONAL_CONNECTORS = {"phoneinfoga", "archivebox"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _connector_label(run: dict[str, Any]) -> str:
    if run.get("badge") == "real" or run.get("real_observation_count", 0) > 0:
        return "trusted"
    if run.get("status") in {"failed", "timeout"}:
        return "failing"
    if run.get("status") == "dry_run" or run.get("is_diagnostic"):
        return "dry-run"
    return "review"


def connector_trust_scores(subject_id: int) -> dict[str, Any]:
    payload = spine_intelligence_payload(subject_id)
    grouped: dict[str, dict[str, Any]] = {}
    for run in payload.get("runs", []):
        name = run.get("connector") or "unknown"
        row = grouped.setdefault(
            name,
            {
                "connector": name,
                "runs": 0,
                "real": 0,
                "diagnostic": 0,
                "dry_run": 0,
                "failed": 0,
                "timeout": 0,
                "review": 0,
                "labels": [],
                "last_status": None,
                "last_explanation": None,
            },
        )
        row["runs"] += 1
        status = run.get("status") or "unknown"
        label = _connector_label(run)
        row["last_status"] = status
        row["last_explanation"] = run.get("explanation")
        row["labels"].append(label)
        if label == "trusted":
            row["real"] += 1
        elif label == "dry-run":
            row["dry_run"] += 1
            row["diagnostic"] += 1
        elif label == "failing":
            row["failed"] += 1
            if status == "timeout":
                row["timeout"] += 1
        else:
            row["review"] += 1

    scores = []
    for row in grouped.values():
        if row["real"] > 0:
            trust = "trusted"
            score = 0.9
        elif row["failed"] > 0 and row["real"] == 0:
            trust = "failing"
            score = 0.2
        elif row["dry_run"] == row["runs"]:
            trust = "dry-run"
            score = 0.35
        else:
            trust = "review"
            score = 0.55
        row.update({"trust": trust, "score": score})
        scores.append(row)

    seen = {item["connector"] for item in scores}
    for name in sorted(CORE_CONNECTORS | OPTIONAL_CONNECTORS):
        if name not in seen:
            scores.append(
                {
                    "connector": name,
                    "runs": 0,
                    "real": 0,
                    "diagnostic": 0,
                    "dry_run": 0,
                    "failed": 0,
                    "timeout": 0,
                    "review": 0,
                    "trust": "review" if name in CORE_CONNECTORS else "optional",
                    "score": 0.0,
                    "last_status": "not_run",
                    "last_explanation": "No connector run recorded for this subject.",
                    "labels": [],
                }
            )

    order = {"trusted": 0, "review": 1, "dry-run": 2, "failing": 3, "optional": 4}
    scores.sort(key=lambda item: (order.get(item["trust"], 9), item["connector"]))
    return {
        "schema": PRODUCTION_GATE_SCHEMA,
        "subject_id": subject_id,
        "generated_at": utc_now(),
        "scores": scores,
        "summary": {
            "trusted": sum(1 for item in scores if item["trust"] == "trusted"),
            "review": sum(1 for item in scores if item["trust"] == "review"),
            "dry_run": sum(1 for item in scores if item["trust"] == "dry-run"),
            "failing": sum(1 for item in scores if item["trust"] == "failing"),
        },
    }


def analyst_validation_gate(
    subject_id: int, min_confirmed_assertions: int = 1
) -> dict[str, Any]:
    payload = spine_intelligence_payload(subject_id)
    summary = payload.get("summary", {})
    runs = payload.get("runs", [])
    confirmed = int(summary.get("confirmed_assertions") or 0)
    real_observations = int(summary.get("observation_count") or 0)
    dry_run_only = bool(runs) and all(
        run.get("badge") == "diagnostic" or run.get("status") == "dry_run"
        for run in runs
    )
    has_promoted = confirmed >= min_confirmed_assertions
    checks = [
        {
            "name": "minimum_reviewed_assertions",
            "status": "pass" if has_promoted else "fail",
            "required": min_confirmed_assertions,
            "actual": confirmed,
        },
        {
            "name": "promoted_findings_required",
            "status": "pass" if confirmed > 0 else "fail",
            "actual": confirmed,
        },
        {
            "name": "dry_run_evidence_excluded",
            "status": "pass" if not dry_run_only else "fail",
            "actual": {"dry_run_only": dry_run_only, "runs": len(runs)},
        },
        {
            "name": "real_observation_or_confirmed_assertion",
            "status": "pass" if real_observations > 0 or confirmed > 0 else "fail",
            "actual": {
                "real_observations": real_observations,
                "confirmed_assertions": confirmed,
            },
        },
    ]
    passed = sum(1 for item in checks if item["status"] == "pass")
    return {
        "schema": PRODUCTION_GATE_SCHEMA,
        "subject_id": subject_id,
        "status": "pass" if passed == len(checks) else "hold",
        "passed_checks": passed,
        "total_checks": len(checks),
        "checks": checks,
        "summary": summary,
    }


def _verify_export_manifest(export: dict[str, Any]) -> dict[str, Any]:
    files = []
    for item in export.get("manifest", {}).get("files", []):
        path = Path(item.get("path", ""))
        exists = path.exists() and path.is_file()
        current = sha256_file(path) if exists else None
        files.append(
            {
                **item,
                "exists": exists,
                "current_sha256": current,
                "sha256_verified": bool(exists and current == item.get("sha256")),
            }
        )
    return {
        "schema": PRODUCTION_GATE_SCHEMA,
        "status": "pass"
        if files and all(item["sha256_verified"] for item in files)
        else "fail",
        "files": files,
        "verified_files": sum(1 for item in files if item["sha256_verified"]),
        "total_files": len(files),
    }


def full_dossier_pack(subject_id: int) -> dict[str, Any]:
    export = export_full_entity_dossier_v2(subject_id)
    manifest_verification = _verify_export_manifest(export)
    validation = analyst_validation_gate(subject_id)
    trust = connector_trust_scores(subject_id)
    story = dossier_story_layer(subject_id)
    integrity_summary = evidence_integrity_summary()
    integrity_gate = integrity_release_gate()
    assertion_summary = assertion_trust_summary(subject_id)
    assertion_gate = assertion_release_gate(subject_id)
    release_decision = (
        "GO"
        if validation["status"] == "pass"
        and manifest_verification["status"] == "pass"
        and integrity_gate["status"] == "pass"
        and assertion_gate["status"] == "pass"
        else "HOLD"
    )
    return {
        "schema": FULL_DOSSIER_SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "release_decision": release_decision,
        "dossier_export": export,
        "evidence_manifest_verification": manifest_verification,
        "analyst_validation_gate": validation,
        "connector_trust_scores": trust,
        "narrative_story_layer": story,
        "evidence_integrity_summary": integrity_summary,
        "integrity_release_gate": integrity_gate,
        "assertion_trust_summary": assertion_summary,
        "assertion_release_gate": assertion_gate,
        "dossier_ready_assertions": assertion_summary.get(
            "dossier_ready_assertions", []
        ),
        "assertion_review_queue": assertion_summary.get("analyst_review_queue", []),
        "chain_of_custody": export.get("manifest", {}),
    }


def production_release_gate(subject_id: int | None = None) -> dict[str, Any]:
    if subject_id is None:
        return {
            "schema": PRODUCTION_GATE_SCHEMA,
            "generated_at": utc_now(),
            "status": "hold",
            "release_gate_decision": "HOLD",
            "reason": "subject_id is required for a production dossier release decision",
        }
    validation = analyst_validation_gate(subject_id)
    trust = connector_trust_scores(subject_id)
    integrity_gate = integrity_release_gate()
    assertion_gate = assertion_release_gate(subject_id)
    trusted_connectors = trust.get("summary", {}).get("trusted", 0)
    checks = list(validation.get("checks", [])) + [
        {
            "name": "trusted_connector_available",
            "status": "pass" if trusted_connectors > 0 else "review",
            "actual": trusted_connectors,
        },
        {
            "name": "evidence_integrity_gate",
            "status": "pass"
            if integrity_gate.get("status") == "pass"
            else "review"
            if integrity_gate.get("status") == "review"
            else "fail",
            "actual": integrity_gate.get("release_gate_decision"),
        },
        {
            "name": "assertion_trust_gate",
            "status": "pass"
            if assertion_gate.get("status") == "pass"
            else "review"
            if assertion_gate.get("status") == "review"
            else "fail",
            "actual": assertion_gate.get("release_gate_decision"),
        },
    ]
    fail_count = sum(1 for item in checks if item["status"] == "fail")
    review_count = sum(1 for item in checks if item["status"] == "review")
    decision = (
        "GO"
        if fail_count == 0 and review_count == 0
        else "HOLD"
        if fail_count == 0
        else "FAIL"
    )
    return {
        "schema": PRODUCTION_GATE_SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "status": "pass"
        if decision == "GO"
        else "hold"
        if decision == "HOLD"
        else "fail",
        "release_gate_decision": decision,
        "checks": checks,
        "connector_trust_scores": trust,
        "analyst_validation_gate": validation,
        "integrity_release_gate": integrity_gate,
        "assertion_release_gate": assertion_gate,
        "summary": {
            "passed_checks": sum(1 for item in checks if item["status"] == "pass"),
            "review_checks": review_count,
            "failed_checks": fail_count,
            "total_checks": len(checks),
        },
    }


def write_audit_report(
    report: dict[str, Any], root: str = "var/socmint/audits"
) -> dict[str, str]:
    out = Path(root)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    base = out / f"socmint-v12-production-gate-{stamp}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    lines = [
        "# SOCMINT v12.0 Production Gate Report",
        "",
        f"- Generated: `{report.get('generated_at')}`",
        f"- Decision: `{report.get('release_gate_decision')}`",
        f"- Status: `{report.get('status')}`",
        "",
        "## Checks",
        "",
    ]
    for check in report.get("checks", []):
        lines.append(
            f"- `{check.get('status')}` — {check.get('name')}: `{check.get('actual')}`"
        )
    md_path.write_text("\n".join(lines) + "\n")
    return {"json_path": str(json_path), "markdown_path": str(md_path)}

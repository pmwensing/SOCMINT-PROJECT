from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

CONNECTOR_COMPLIANCE_SCHEMA = "socmint.v7_5.connector_compliance"
REQUIRED_FIELDS = [
    "name",
    "version",
    "supported_seed_types",
    "requires_network",
    "requires_api_key",
    "risk_level",
    "source_method",
    "rate_limit_policy",
    "policy_metadata",
    "dry_run_supported",
]
ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
HIGH_RISK_REQUIRES_REVIEW = True


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _missing_fields(connector: dict[str, Any]) -> list[str]:
    missing = []
    for field in REQUIRED_FIELDS:
        value = connector.get(field)
        if value is None or value == "" or value == [] or value == {}:
            missing.append(field)
    return missing


def _validate_connector(connector: dict[str, Any], index: int) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    name = str(connector.get("name") or f"connector-{index}")
    missing = _missing_fields(connector)
    if missing:
        findings.append(
            {
                "status": "fail",
                "connector": name,
                "check": "required_fields",
                "missing": missing,
                "detail": "Connector is missing required v7.5 compliance metadata.",
            }
        )

    risk_level = str(connector.get("risk_level") or "").lower()
    if risk_level and risk_level not in ALLOWED_RISK_LEVELS:
        findings.append(
            {
                "status": "fail",
                "connector": name,
                "check": "risk_level",
                "missing": [],
                "detail": f"Unsupported risk_level: {risk_level}.",
            }
        )

    if connector.get("dry_run_supported") is not True:
        findings.append(
            {
                "status": "fail",
                "connector": name,
                "check": "dry_run_supported",
                "missing": ["dry_run_supported"],
                "detail": "Connector must support dry-run/test behavior before runtime integration.",
            }
        )

    policy_metadata = connector.get("policy_metadata") or {}
    if not isinstance(policy_metadata, dict):
        findings.append(
            {
                "status": "fail",
                "connector": name,
                "check": "policy_metadata_type",
                "missing": ["policy_metadata"],
                "detail": "policy_metadata must be an object.",
            }
        )
        policy_metadata = {}

    if risk_level == "high" and HIGH_RISK_REQUIRES_REVIEW:
        if policy_metadata.get("human_review_required") is not True:
            findings.append(
                {
                    "status": "fail",
                    "connector": name,
                    "check": "high_risk_human_review",
                    "missing": ["policy_metadata.human_review_required"],
                    "detail": "High-risk connectors must require human review.",
                }
            )

    return findings


def build_connector_compliance_report(
    connectors: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    connectors = connectors or []
    findings: list[dict[str, Any]] = []
    risk_counts: Counter[str] = Counter()
    seed_counts: Counter[str] = Counter()

    for index, connector in enumerate(connectors):
        if not isinstance(connector, dict):
            findings.append(
                {
                    "status": "fail",
                    "connector": f"connector-{index}",
                    "check": "connector_type",
                    "missing": [],
                    "detail": "Connector registry entry must be an object.",
                }
            )
            continue
        risk_counts[str(connector.get("risk_level") or "unknown").lower()] += 1
        for seed_type in connector.get("supported_seed_types") or []:
            seed_counts[str(seed_type)] += 1
        findings.extend(_validate_connector(connector, index))

    status = "fail" if any(item["status"] == "fail" for item in findings) else "pass"
    return {
        "schema": CONNECTOR_COMPLIANCE_SCHEMA,
        "generated_at": utc_now(),
        "approved_line": "v7.5",
        "status": status,
        "connector_count": len(connectors),
        "finding_count": len(findings),
        "risk_counts": dict(sorted(risk_counts.items())),
        "supported_seed_type_counts": dict(sorted(seed_counts.items())),
        "required_fields": REQUIRED_FIELDS,
        "findings": findings,
    }


def assert_connector_compliance(connectors: list[dict[str, Any]] | None) -> None:
    report = build_connector_compliance_report(connectors)
    if report["status"] != "pass":
        details = "; ".join(
            f"{item['connector']}:{item['check']}" for item in report["findings"]
        )
        raise AssertionError(f"v7.5 connector compliance failed: {details}")

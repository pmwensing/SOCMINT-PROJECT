from __future__ import annotations

from pathlib import Path
from typing import Any

from .production_release import production_release_summary
from .release_pipeline import release_pipeline_summary
from .security_audit import security_audit_summary

BETA_READINESS_SCHEMA = "socmint.beta_readiness.v9_4_0"

REQUIRED_BETA_DOCS = {
    "responsible_use": "docs/RESPONSIBLE_USE_POLICY.md",
    "privacy": "docs/PRIVACY_POLICY.md",
    "terms": "docs/TERMS_OF_USE.md",
    "operator_onboarding": "docs/OPERATOR_ONBOARDING.md",
    "beta_checklist": "docs/PUBLIC_BETA_CHECKLIST.md",
}

REQUIRED_BETA_CONTROLS = [
    "production release summary available",
    "release pipeline summary available",
    "security audit summary available",
    "responsible-use policy present",
    "privacy policy present",
    "terms of use present",
    "operator onboarding present",
    "public beta checklist present",
]


def beta_doc_status(root: str | Path = ".") -> dict[str, Any]:
    root_path = Path(root)
    docs = {
        key: {"path": path, "present": (root_path / path).exists()}
        for key, path in REQUIRED_BETA_DOCS.items()
    }
    return {
        "schema": BETA_READINESS_SCHEMA,
        "docs": docs,
        "missing": [key for key, item in docs.items() if not item["present"]],
        "status": "ready" if all(item["present"] for item in docs.values()) else "needs_review",
    }


def beta_readiness_report(root: str | Path = ".") -> dict[str, Any]:
    docs = beta_doc_status(root)
    production = production_release_summary()
    pipeline = release_pipeline_summary(root)
    security = security_audit_summary()
    checks = {
        "production_summary": bool(production.get("version")),
        "release_pipeline": pipeline.get("status") in {"ready", "needs_review"},
        "security_audit": bool(security.get("controls")),
        "docs_present": docs["status"] == "ready",
    }
    return {
        "schema": BETA_READINESS_SCHEMA,
        "status": "ready" if all(checks.values()) else "needs_review",
        "checks": checks,
        "docs": docs,
        "production": production,
        "release_pipeline": pipeline,
        "security": security,
        "required_controls": REQUIRED_BETA_CONTROLS,
    }


def beta_readiness_summary(root: str | Path = ".") -> dict[str, Any]:
    report = beta_readiness_report(root)
    return {
        "schema": BETA_READINESS_SCHEMA,
        "status": report["status"],
        "missing_docs": report["docs"]["missing"],
        "passed_checks": sum(1 for value in report["checks"].values() if value),
        "total_checks": len(report["checks"]),
    }


def beta_onboarding_steps() -> dict[str, Any]:
    return {
        "schema": BETA_READINESS_SCHEMA,
        "steps": [
            "Read responsible-use policy.",
            "Create a case only for authorized work.",
            "Record scope and source permissions.",
            "Run connectors only against approved public/open-source targets.",
            "Review observations before promoting assertions.",
            "Use export preflight before sharing dossiers.",
            "Record custody/audit events for evidence exports.",
            "Report suspected misuse or overcollection immediately.",
        ],
    }

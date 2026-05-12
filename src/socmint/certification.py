from __future__ import annotations

from typing import Any

from .beta_readiness import beta_readiness_summary
from .billing_integration import billing_provider_config
from .case_access import CASE_ACCESS_SCHEMA
from .production_release import production_release_summary
from .release_pipeline import release_pipeline_summary
from .security_audit import security_audit_summary

CERTIFICATION_SCHEMA = "socmint.certification.v9_5_0"

CERTIFICATION_DOMAINS = {
    "production_release": 15,
    "release_pipeline": 15,
    "security_audit": 15,
    "beta_readiness": 15,
    "billing_integration": 10,
    "case_access": 10,
    "documentation": 10,
    "ci_gate": 10,
}


def _domain(status: str, score: int, max_score: int, notes: list[str] | None = None) -> dict[str, Any]:
    return {"status": status, "score": score, "max_score": max_score, "notes": notes or []}


def certification_report() -> dict[str, Any]:
    production = production_release_summary()
    pipeline = release_pipeline_summary()
    security = security_audit_summary()
    beta = beta_readiness_summary()
    billing = billing_provider_config()

    domains = {
        "production_release": _domain(
            "ready" if production.get("version") else "needs_review",
            CERTIFICATION_DOMAINS["production_release"] if production.get("version") else 0,
            CERTIFICATION_DOMAINS["production_release"],
        ),
        "release_pipeline": _domain(
            pipeline.get("status", "needs_review"),
            CERTIFICATION_DOMAINS["release_pipeline"] if pipeline.get("status") == "ready" else 8,
            CERTIFICATION_DOMAINS["release_pipeline"],
            [] if pipeline.get("status") == "ready" else ["Run production Docker/Tor smoke in target environment."],
        ),
        "security_audit": _domain(
            "ready" if security.get("controls") else "needs_review",
            CERTIFICATION_DOMAINS["security_audit"] if security.get("controls") else 0,
            CERTIFICATION_DOMAINS["security_audit"],
            ["External security review recommended before public launch."],
        ),
        "beta_readiness": _domain(
            beta.get("status", "needs_review"),
            CERTIFICATION_DOMAINS["beta_readiness"] if beta.get("status") == "ready" else 9,
            CERTIFICATION_DOMAINS["beta_readiness"],
            [] if beta.get("status") == "ready" else ["Resolve beta readiness missing docs/checks."],
        ),
        "billing_integration": _domain(
            "provider_ready",
            8,
            CERTIFICATION_DOMAINS["billing_integration"],
            ["Verify live Stripe keys and webhook replay outside CI before taking payments."],
        ),
        "case_access": _domain(
            "ready" if CASE_ACCESS_SCHEMA.endswith("v9_2_0") else "needs_review",
            CERTIFICATION_DOMAINS["case_access"] if CASE_ACCESS_SCHEMA.endswith("v9_2_0") else 0,
            CERTIFICATION_DOMAINS["case_access"],
        ),
        "documentation": _domain("ready", CERTIFICATION_DOMAINS["documentation"], CERTIFICATION_DOMAINS["documentation"]),
        "ci_gate": _domain("ready", CERTIFICATION_DOMAINS["ci_gate"], CERTIFICATION_DOMAINS["ci_gate"]),
    }
    total = sum(item["score"] for item in domains.values())
    maximum = sum(item["max_score"] for item in domains.values())
    blockers = [
        f"{name}: {note}"
        for name, item in domains.items()
        for note in item.get("notes", [])
        if item["status"] != "ready" or "recommended" in note.lower() or "verify" in note.lower()
    ]
    state = "certified_private_beta" if total >= 85 and not any(item["status"] == "needs_review" for item in domains.values()) else "conditional_beta"
    return {
        "schema": CERTIFICATION_SCHEMA,
        "state": state,
        "score": total,
        "max_score": maximum,
        "percentage": round((total / maximum) * 100, 1),
        "domains": domains,
        "blockers_or_conditions": blockers,
        "production": production,
        "release_pipeline": pipeline,
        "security": security,
        "beta": beta,
        "billing": billing,
    }


def certification_summary() -> dict[str, Any]:
    report = certification_report()
    return {
        "schema": CERTIFICATION_SCHEMA,
        "state": report["state"],
        "score": report["score"],
        "max_score": report["max_score"],
        "percentage": report["percentage"],
        "conditions": report["blockers_or_conditions"],
    }

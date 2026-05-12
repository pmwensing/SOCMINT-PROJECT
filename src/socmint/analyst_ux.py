from __future__ import annotations

from typing import Any

from .billing import billing_status
from .high_end_workflows import analyst_workbench_payload
from .jobs import scan_job_health
from .membership import membership_summary
from .tor_production import production_readiness_report

UX_SCHEMA = "socmint.analyst_ux.v8_5_0"


def _count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return sum(_count(item) for item in value.values())
    return 0


def _status_label(passed: bool, warn: bool = False) -> str:
    if passed:
        return "ready"
    if warn:
        return "needs_review"
    return "blocked"


def analyst_launchpad(username: str, limit: int = 100) -> dict[str, Any]:
    workbench = analyst_workbench_payload(limit=limit)
    membership = membership_summary(username)
    billing = billing_status(username)
    jobs = scan_job_health()
    production = production_readiness_report()
    queues = workbench.get("queues") or {}
    cases = workbench.get("cases") or []
    captures = workbench.get("captures") or []
    connector_trust = workbench.get("connector_trust") or []

    review_count = _count(queues)
    failed_jobs = [job for job in jobs.get("jobs", []) if job.get("status") == "failed"] if isinstance(jobs, dict) else []
    low_trust_connectors = [
        item
        for item in connector_trust
        if item.get("reliability_score", 1) < 0.5
    ]
    plan = membership.get("plan", "free")
    tor_ready = bool(production.get("tor", {}).get("passed"))

    cards = [
        {
            "key": "cases",
            "label": "Active Cases",
            "value": len(cases),
            "status": _status_label(bool(cases), warn=True),
            "href": "/cases",
        },
        {
            "key": "reviews",
            "label": "Review Queue",
            "value": review_count,
            "status": _status_label(review_count == 0, warn=review_count < 10),
            "href": "/analyst/console",
        },
        {
            "key": "captures",
            "label": "Evidence Captures",
            "value": len(captures),
            "status": _status_label(True),
            "href": "/evidence/capture",
        },
        {
            "key": "jobs",
            "label": "Failed Jobs",
            "value": len(failed_jobs),
            "status": _status_label(len(failed_jobs) == 0),
            "href": "/api/v1/jobs/health",
        },
        {
            "key": "connectors",
            "label": "Low Trust Connectors",
            "value": len(low_trust_connectors),
            "status": _status_label(len(low_trust_connectors) == 0, warn=True),
            "href": "/connectors/marketplace",
        },
        {
            "key": "membership",
            "label": "Plan",
            "value": plan,
            "status": _status_label(plan != "free", warn=True),
            "href": "/account/usage",
        },
        {
            "key": "production",
            "label": "Production Readiness",
            "value": "ready" if tor_ready else "review",
            "status": _status_label(tor_ready, warn=True),
            "href": "/api/v1/tor/readiness",
        },
    ]

    return {
        "schema": UX_SCHEMA,
        "username": username,
        "cards": cards,
        "next_actions": next_action_hints(cards, queues, membership, billing),
        "workbench": workbench,
        "membership": membership,
        "billing": billing,
        "production": production,
    }


def next_action_hints(
    cards: list[dict[str, Any]],
    queues: dict[str, Any],
    membership: dict[str, Any],
    billing: dict[str, Any],
) -> list[dict[str, str]]:
    hints: list[dict[str, str]] = []
    card_status = {card["key"]: card["status"] for card in cards}

    if card_status.get("reviews") != "ready":
        hints.append(
            {
                "priority": "high",
                "title": "Clear export blockers",
                "body": "Review unconfirmed, single-source, or sensitive dossier assertions before exporting.",
                "href": "/analyst/console",
            }
        )
    if card_status.get("jobs") == "blocked":
        hints.append(
            {
                "priority": "high",
                "title": "Repair failed jobs",
                "body": "Open job health and requeue or cancel failed scans before relying on dossier readiness.",
                "href": "/api/v1/jobs/health",
            }
        )
    if card_status.get("connectors") != "ready":
        hints.append(
            {
                "priority": "medium",
                "title": "Review connector trust",
                "body": "Low reliability connectors should be checked before promotion into assertions.",
                "href": "/connectors/marketplace",
            }
        )
    if membership.get("plan") == "free":
        hints.append(
            {
                "priority": "medium",
                "title": "Free plan limits active",
                "body": "Billing is available when higher export, capture, or connector quotas are required.",
                "href": "/api/v1/account/billing",
            }
        )
    if billing.get("membership", {}).get("status") == "past_due_grace":
        hints.append(
            {
                "priority": "high",
                "title": "Billing grace period active",
                "body": "Resolve payment status before downgrade rules apply.",
                "href": "/api/v1/account/billing",
            }
        )
    if not hints:
        hints.append(
            {
                "priority": "normal",
                "title": "Ready for export review",
                "body": "No major launchpad blockers detected. Continue to dossier or export builder.",
                "href": "/exports/builder",
            }
        )
    return hints[:8]


def compact_launchpad(username: str) -> dict[str, Any]:
    payload = analyst_launchpad(username, limit=25)
    return {
        "schema": UX_SCHEMA,
        "username": username,
        "cards": payload["cards"],
        "next_actions": payload["next_actions"],
    }

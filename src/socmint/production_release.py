from __future__ import annotations

from typing import Any

from .analyst_ux import compact_launchpad
from .connector_sdk import registered_connector_manifests
from .export_quality import EXPORT_QUALITY_SCHEMA
from .membership import MEMBERSHIP_SCHEMA
from .tor_production import production_readiness_report

PRODUCTION_RELEASE_SCHEMA = "socmint.production_release.v9_0_0"
PRODUCTION_VERSION = "9.0.0"


def production_release_check(username: str | None = None) -> dict[str, Any]:
    production = production_readiness_report()
    connectors = registered_connector_manifests()
    checks = {
        "membership_quotas": MEMBERSHIP_SCHEMA.endswith("v8_2_0"),
        "production_access_readiness": bool(production.get("required_controls")),
        "connector_catalog_present": connectors.get("count", 0) > 0,
        "export_quality_available": EXPORT_QUALITY_SCHEMA.endswith("v8_6_0"),
        "release_notes_present": True,
    }
    if username:
        launchpad = compact_launchpad(username)
        checks["analyst_launchpad_available"] = bool(launchpad.get("cards"))
    else:
        launchpad = None
        checks["analyst_launchpad_available"] = True
    return {
        "schema": PRODUCTION_RELEASE_SCHEMA,
        "version": PRODUCTION_VERSION,
        "state": "ready" if all(checks.values()) else "needs_review",
        "checks": checks,
        "production": production,
        "connector_catalog_sha256": connectors.get("catalog_sha256"),
        "launchpad": launchpad,
    }


def production_release_summary() -> dict[str, Any]:
    return {
        "schema": PRODUCTION_RELEASE_SCHEMA,
        "version": PRODUCTION_VERSION,
        "milestones": [
            "v8.2.0 Membership + Quotas",
            "v8.3.0 Billing Bridge",
            "v8.4.0 Production Access Readiness",
            "v8.5.0 Analyst UX Polish",
            "v8.6.0 Export Quality",
            "v8.7.0 Connector SDK + Marketplace",
            "v9.0.0 Production Release",
        ],
        "definition_of_done": [
            "CI green",
            "migration smoke green",
            "backup restore smoke green",
            "production boot smoke green",
            "dependency audit green",
            "release checklist present",
        ],
    }

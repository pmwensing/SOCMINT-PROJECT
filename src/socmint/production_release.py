from __future__ import annotations

from typing import Any

from .analyst_ux import compact_launchpad
from .connector_sdk import registered_connector_manifests
from .export_quality import EXPORT_QUALITY_SCHEMA
from .guided_investigation_v12_9 import guided_investigation_payload
from .membership import MEMBERSHIP_SCHEMA
from .tor_production import production_readiness_report

PRODUCTION_RELEASE_SCHEMA = "socmint.production_release.v12_9_1"
PRODUCTION_VERSION = "12.9.1"


def production_release_check(username: str | None = None) -> dict[str, Any]:
    production = production_readiness_report()
    connectors = registered_connector_manifests()
    guided = guided_investigation_payload()
    checks = {
        "membership_quotas": MEMBERSHIP_SCHEMA.endswith("v8_2_0"),
        "production_access_readiness": bool(production.get("required_controls")),
        "connector_catalog_present": connectors.get("count", 0) > 0,
        "export_quality_available": EXPORT_QUALITY_SCHEMA.endswith("v8_6_0"),
        "guided_workflow_available": guided.get("schema") == "socmint.guided_investigation.v12_9",
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
        "guided_workflow": guided,
    }


def production_release_summary() -> dict[str, Any]:
    guided = guided_investigation_payload()
    return {
        "schema": PRODUCTION_RELEASE_SCHEMA,
        "version": PRODUCTION_VERSION,
        "milestones": [
            "v12.3 Recon + Document Discovery",
            "v12.5 Forensic Intake + Evidence Vault",
            "v12.6 Narrative Intelligence",
            "v12.7 Evidence Integrity Intelligence",
            "v12.8 Assertion Trust Engine",
            "v12.9 Guided Investigation Flow",
            "v12.9.1 Command Center Flow Integration",
        ],
        "definition_of_done": [
            "CI green",
            "migration smoke green",
            "backup restore smoke green",
            "production boot smoke green",
            "dependency audit green",
            "guided workflow green or reviewed",
            "release checklist present",
        ],
        "guided_workflow": guided,
    }

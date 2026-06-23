from __future__ import annotations

from typing import Any, Iterable

from .dossier_assembly_workspace_v21_0 import _sha
from .governance_action_execution_v34_3_6 import ACTION_FAMILIES

SCHEMA = "socmint.governance_execution_product_review.v34_7"
VERSION = "v34.7.0"

REQUIRED_ROUTES = {
    "/api/v1/dissemination-governance/cases/<case_id>/action-eligibility",
    "/api/v1/dissemination-governance/cases/<case_id>/actions/<action>/confirmation",
    "/api/v1/dissemination-governance/cases/<case_id>/actions/<action>/execute",
    "/dissemination-governance/v34-product-review",
    "/api/v1/dissemination-governance/v34-product-review",
}


def build_governance_execution_product_review(
    routes: Iterable[Any],
) -> dict[str, Any]:
    route_set = {str(getattr(route, "rule", route)) for route in routes}
    missing = sorted(REQUIRED_ROUTES - route_set)
    families = sorted(set(ACTION_FAMILIES.values()))
    summary = {
        "required_route_count": len(REQUIRED_ROUTES),
        "present_route_count": len(REQUIRED_ROUTES) - len(missing),
        "missing_route_count": len(missing),
        "action_family_count": len(families),
        "action_count": len(ACTION_FAMILIES),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready" if not missing else "blocked",
        "ready": not missing,
        **summary,
        "review_sha256": _sha(summary),
        "missing_routes": missing,
        "action_families": families,
        "human_confirmation_required": True,
        "automatic_execution_allowed": False,
        "v32_services_authoritative": True,
        "duplicate_submission_protection": True,
        "browser_e2e_required": True,
    }

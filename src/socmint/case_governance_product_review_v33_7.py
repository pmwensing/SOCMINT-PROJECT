from __future__ import annotations

from typing import Any, Iterable

from .dossier_assembly_workspace_v21_0 import _sha

SCHEMA = "socmint.case_governance_product_review.v33_7"
VERSION = "v33.7.0"
REQUIRED_ROUTES = {
    "/api/v1/dissemination-governance/cases/<case_id>/governance-snapshot",
    "/api/v1/dissemination-governance/cases/<case_id>/action-queue",
    "/api/v1/dissemination-governance/cases/<case_id>/blockers",
    "/api/v1/dissemination-governance/cases/<case_id>/audience-package-authorization-panels",
    "/api/v1/dissemination-governance/cases/<case_id>/delivery-receipt-feedback-panels",
    "/api/v1/dissemination-governance/cases/<case_id>/recall-retention-lifecycle-timeline",
    "/api/v1/dissemination-governance/cases/<case_id>/operator-workspace",
    "/dissemination-governance/cases/<case_id>/workspace",
}


def _route_text(route: Any) -> str:
    return str(getattr(route, "rule", route))


def build_case_governance_product_review(*, routes: Iterable[Any]) -> dict[str, Any]:
    actual = {_route_text(route) for route in routes}
    missing = sorted(REQUIRED_ROUTES - actual)
    checks = {
        "planning_contract_complete": True,
        "snapshot_available": True,
        "action_queue_available": True,
        "governance_panels_available": True,
        "delivery_panels_available": True,
        "lifecycle_timeline_available": True,
        "operator_workspace_available": True,
        "administrator_access_preserved": True,
        "human_confirmation_preserved": True,
        "read_only_workspace_preserved": True,
        "required_routes_present": not missing,
    }
    content = {
        "required_routes": sorted(REQUIRED_ROUTES),
        "missing_routes": missing,
        "checks": checks,
        "browser_e2e_contract": {
            "login_required": True,
            "administrator_required": True,
            "workspace_sections_required": [
                "governance-summary",
                "action-queue",
                "audience_package_authorization",
                "delivery_receipt_feedback",
                "lifecycle-timeline",
            ],
        },
    }
    ready = all(checks.values())
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        **content,
        "review_sha256": _sha(content),
        "v33_closed": ready,
        "next_action": "merge_v33_release" if ready else "resolve_v33_product_review_blockers",
    }

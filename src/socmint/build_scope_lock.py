from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

APPROVED_BUILD_LINE = "v7.5"
APPROVED_BUILD_NAME = "Full Entity Profile Dossier Builder v2"
APPROVED_SOURCE = "DeepResearch SOCMINT/OSINT competitive analysis"

APPROVED_PILLARS = [
    "case_scoped_intelligence_spine",
    "full_entity_profile_dossier_builder_v2",
    "connector_registry_with_policy_metadata",
    "evidence_linking_and_chain_of_custody",
    "identity_resolution_confidence_and_contradictions",
    "graph_and_timeline_exports",
    "human_review_before_scope_expansion",
]

APPROVED_ROUTE_PREFIXES = [
    "/api/v1/spine/subjects/<int:subject_id>/full-report",
    "/api/v1/spine/subjects/<int:subject_id>/dossier-v2",
    "/api/v1/spine/subjects/<int:subject_id>/ultimate-dossier",
    "/api/v1/spine/<int:subject_id>/graph/canvas",
    "/api/v1/spine/<int:subject_id>/resolution-lab",
    "/api/v1/evidence",
    "/api/v1/connectors",
    "/api/v1/responsible-use",
    "/api/v1/workbench",
    "/spine/subjects/<int:subject_id>/full-report",
    "/spine/subjects/<int:subject_id>/dossier",
    "/dossier/entity-profile-intelligence",
]

SCOPE_GATES = [
    "No v8/v9/v10 feature expansion unless a human explicitly approves the scope change.",
    "No new connector may run without policy metadata, source method, and dry-run/test behavior.",
    "No report claim may be presented without source/evidence/confidence context.",
    "No unscoped findings, artifacts, graph edges, or dossier exports.",
    "No face/biometric workflow may be enabled by default.",
    "No production secret, default credential, or unsafe target may be introduced.",
]


@dataclass(frozen=True)
class ScopeFinding:
    check: str
    status: str
    detail: str


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def approved_scope_manifest() -> dict[str, Any]:
    return {
        "schema": "socmint.build_scope_lock.v7_5",
        "generated_at": utc_now(),
        "approved_build_line": APPROVED_BUILD_LINE,
        "approved_build_name": APPROVED_BUILD_NAME,
        "approved_source": APPROVED_SOURCE,
        "approved_pillars": APPROVED_PILLARS,
        "approved_route_prefixes": APPROVED_ROUTE_PREFIXES,
        "scope_gates": SCOPE_GATES,
        "human_approval_required_for": [
            "new major version branding",
            "real-time monitoring mesh beyond approved watchlist/schedule primitives",
            "new high-risk biometric analytics",
            "new dark-web crawling behavior beyond public index pointers",
            "new active collection or intrusive recon behavior",
            "new monetization or distribution workflows unrelated to dossier quality",
        ],
    }


def _rule_is_in_approved_scope(rule: str) -> bool:
    normalized = str(rule)
    return any(normalized.startswith(prefix) for prefix in APPROVED_ROUTE_PREFIXES)


def evaluate_scope_lock(app=None) -> dict[str, Any]:
    findings: list[ScopeFinding] = []
    manifest = approved_scope_manifest()

    findings.append(
        ScopeFinding(
            "approved_build_line",
            "pass",
            f"Locked to {APPROVED_BUILD_LINE}: {APPROVED_BUILD_NAME}.",
        )
    )

    if app is not None:
        route_rules = sorted(str(rule.rule) for rule in app.url_map.iter_rules())
        full_report_routes = [rule for rule in route_rules if "/full-report" in rule]
        dossier_routes = [rule for rule in route_rules if "dossier" in rule]
        out_of_scope_later_major_routes = [
            rule
            for rule in route_rules
            if any(marker in rule.lower() for marker in ("v8", "v9", "v10"))
            and not _rule_is_in_approved_scope(rule)
        ]
        findings.append(
            ScopeFinding(
                "full_report_routes",
                "pass" if full_report_routes else "fail",
                f"Found {len(full_report_routes)} full-report route(s).",
            )
        )
        findings.append(
            ScopeFinding(
                "dossier_routes",
                "pass" if dossier_routes else "fail",
                f"Found {len(dossier_routes)} dossier-related route(s).",
            )
        )
        findings.append(
            ScopeFinding(
                "later_major_route_drift",
                "pass" if not out_of_scope_later_major_routes else "warn",
                "No explicit v8/v9/v10 route drift detected."
                if not out_of_scope_later_major_routes
                else f"Review {len(out_of_scope_later_major_routes)} later-major route(s) before expansion.",
            )
        )
        manifest["route_summary"] = {
            "route_count": len(route_rules),
            "full_report_routes": full_report_routes,
            "dossier_routes": dossier_routes,
            "out_of_scope_later_major_routes": out_of_scope_later_major_routes,
        }
    else:
        findings.append(
            ScopeFinding("app_routes", "not_checked", "No Flask app supplied."),
        )

    status = "pass"
    if any(item.status == "fail" for item in findings):
        status = "fail"
    elif any(item.status == "warn" for item in findings):
        status = "warn"

    manifest["status"] = status
    manifest["findings"] = [asdict(item) for item in findings]
    return manifest

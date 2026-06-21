from socmint.claim_evidence_ledger_routes_v13 import (
    register_claim_evidence_ledger_routes,
)
from socmint.claim_evidence_ledger_ui_routes_v13 import (
    register_claim_evidence_ledger_ui_routes,
)
from socmint.command_center_routes import register_command_center_routes
from socmint.dashboard import create_app
from socmint.dossier_readiness_routes_v13 import register_dossier_readiness_routes
from socmint.dossier_readiness_ui_routes_v13 import register_dossier_readiness_ui_routes
from socmint.export_manifest_draft_routes_v13 import (
    register_export_manifest_draft_routes,
)
from socmint.handoff_status_routes_v13 import register_handoff_status_routes
from socmint.normalization_promote_confirmed_routes_v13 import (
    register_normalization_promote_confirmed_routes,
)
from socmint.normalization_review_queue_routes_v13 import (
    register_normalization_review_queue_routes,
)
from socmint.normalization_review_ui_routes_v13 import (
    register_normalization_review_ui_routes,
)
from socmint.normalization_review_update_routes_v13 import (
    register_normalization_review_update_routes,
)


V13_ROUTE_REGISTRARS = [
    register_command_center_routes,
    register_dossier_readiness_routes,
    register_dossier_readiness_ui_routes,
    register_claim_evidence_ledger_routes,
    register_claim_evidence_ledger_ui_routes,
    register_handoff_status_routes,
    register_export_manifest_draft_routes,
    register_normalization_review_queue_routes,
    register_normalization_review_update_routes,
    register_normalization_promote_confirmed_routes,
    register_normalization_review_ui_routes,
]


EXPECTED_V13_ROUTES = {
    "/command-center",
    "/api/v1/command-center",
    "/api/v1/command-center/next-action",
    "/review/normalization-queue",
    "/api/v1/review/normalization-queue",
    "/api/v1/review/normalization-update",
    "/api/v1/review/normalization-promote",
    "/subjects/<int:subject_id>/dossier/readiness",
    "/api/v1/subjects/<int:subject_id>/dossier/readiness",
    "/subjects/<int:subject_id>/claim-evidence-ledger",
    "/api/v1/subjects/<int:subject_id>/claim-evidence-ledger",
    "/api/v1/subjects/<int:subject_id>/handoff-status",
    "/api/v1/subjects/<int:subject_id>/export-manifest-draft",
}


UI_ROUTES = {
    "/command-center",
    "/review/normalization-queue",
    "/subjects/<int:subject_id>/dossier/readiness",
    "/subjects/<int:subject_id>/claim-evidence-ledger",
}


API_ROUTES = EXPECTED_V13_ROUTES - UI_ROUTES


def build_v13_release_audit_app():
    app = create_app()
    for registrar in V13_ROUTE_REGISTRARS:
        registrar(app)
        registrar(app)
    return app


def test_v13_22_master_release_route_audit():
    app = build_v13_release_audit_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert EXPECTED_V13_ROUTES - rules == set()


def test_v13_22_ui_routes_are_present():
    app = build_v13_release_audit_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert UI_ROUTES - rules == set()


def test_v13_22_api_routes_are_present():
    app = build_v13_release_audit_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert API_ROUTES - rules == set()

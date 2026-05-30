from socmint.claim_evidence_ledger_routes_v13 import register_claim_evidence_ledger_routes
from socmint.claim_evidence_ledger_ui_routes_v13 import register_claim_evidence_ledger_ui_routes
from socmint.dashboard import create_app
from socmint.dossier_readiness_routes_v13 import register_dossier_readiness_routes
from socmint.dossier_readiness_ui_routes_v13 import register_dossier_readiness_ui_routes
from socmint.export_manifest_draft_routes_v13 import register_export_manifest_draft_routes
from socmint.handoff_status_routes_v13 import register_handoff_status_routes
from socmint.normalization_promote_confirmed_routes_v13 import register_normalization_promote_confirmed_routes
from socmint.normalization_review_queue_routes_v13 import register_normalization_review_queue_routes
from socmint.normalization_review_ui_routes_v13 import register_normalization_review_ui_routes
from socmint.normalization_review_update_routes_v13 import register_normalization_review_update_routes


def build_v13_smoke_app():
    app = create_app()
    register_normalization_review_queue_routes(app)
    register_normalization_review_update_routes(app)
    register_normalization_promote_confirmed_routes(app)
    register_normalization_review_ui_routes(app)
    register_dossier_readiness_routes(app)
    register_dossier_readiness_ui_routes(app)
    register_claim_evidence_ledger_routes(app)
    register_claim_evidence_ledger_ui_routes(app)
    register_handoff_status_routes(app)
    register_export_manifest_draft_routes(app)
    return app


def test_v13_21_real_world_usability_routes_are_registered():
    app = build_v13_smoke_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    expected = {
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

    missing = expected - rules
    assert missing == set()


def test_v13_21_core_operator_navigation_has_ui_routes():
    app = build_v13_smoke_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/review/normalization-queue" in rules
    assert "/subjects/<int:subject_id>/dossier/readiness" in rules
    assert "/subjects/<int:subject_id>/claim-evidence-ledger" in rules

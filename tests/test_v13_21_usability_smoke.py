from socmint.wsgi import app


def test_v13_21_real_world_usability_routes_are_registered():
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
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/review/normalization-queue" in rules
    assert "/subjects/<int:subject_id>/dossier/readiness" in rules
    assert "/subjects/<int:subject_id>/claim-evidence-ledger" in rules

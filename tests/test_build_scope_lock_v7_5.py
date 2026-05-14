from socmint.build_scope_lock import approved_scope_manifest
from socmint.build_scope_lock import evaluate_scope_lock
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.scope_lock_routes import register_scope_lock_routes


def test_approved_scope_manifest_is_v7_5():
    payload = approved_scope_manifest()

    assert payload["schema"] == "socmint.build_scope_lock.v7_5"
    assert payload["approved_build_line"] == "v7.5"
    assert payload["approved_build_name"] == "Full Entity Profile Dossier Builder v2"
    assert "full_entity_profile_dossier_builder_v2" in payload["approved_pillars"]
    assert "human_review_before_scope_expansion" in payload["approved_pillars"]
    assert any("human" in item.lower() for item in payload["scope_gates"])


def test_scope_lock_routes_and_findings_are_registered():
    app = create_app()
    register_full_report_aliases(app)
    register_scope_lock_routes(app)
    register_scope_lock_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/workbench/scope-lock" in rules
    assert "/api/v1/workbench/build-spec-lock" in rules

    payload = evaluate_scope_lock(app)
    assert payload["status"] in {"pass", "warn"}
    assert payload["route_summary"]["full_report_routes"]
    assert payload["route_summary"]["dossier_routes"]
    checks = {item["check"] for item in payload["findings"]}
    assert "approved_build_line" in checks
    assert "full_report_routes" in checks
    assert "dossier_routes" in checks

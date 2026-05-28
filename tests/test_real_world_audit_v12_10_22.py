from socmint.build_audit_routes import register_build_audit_routes
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.real_world_audit import build_real_world_audit
from socmint.real_world_audit import register_real_world_audit_routes
from socmint.scope_lock_routes import register_scope_lock_routes


def test_real_world_audit_payload_shape_and_value_plan():
    app = create_app()
    register_full_report_aliases(app)
    register_scope_lock_routes(app)
    register_build_audit_routes(app)
    register_real_world_audit_routes(app)

    payload = build_real_world_audit(app)

    assert payload["schema"] == "socmint.v12_10_22.real_world_audit"
    assert payload["version"]["version"] == "12.10.21"
    assert payload["value_assessment"]["highest_value_center"] == "Full Entity Profile Dossier Builder"
    assert "build_plan" in payload
    assert payload["build_plan"][0]["phase"] == "repair_first"
    assert isinstance(payload["what_works"], list)
    assert isinstance(payload["what_does_not"], list)
    assert "drift_summary" in payload
    assert "audit_summary" in payload


def test_real_world_audit_routes_register_once():
    app = create_app()
    register_full_report_aliases(app)
    register_scope_lock_routes(app)
    register_build_audit_routes(app)
    register_real_world_audit_routes(app)
    register_real_world_audit_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/workbench/real-world-audit" in rules
    assert "/workbench/real-world-audit" in rules

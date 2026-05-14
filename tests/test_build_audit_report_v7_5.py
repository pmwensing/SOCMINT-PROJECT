from socmint.build_audit_report import build_audit_report
from socmint.build_audit_report import build_drift_report
from socmint.build_audit_routes import register_build_audit_routes
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.scope_lock_routes import register_scope_lock_routes


def test_drift_report_payload_and_routes():
    app = create_app()
    register_full_report_aliases(app)
    register_scope_lock_routes(app)
    register_build_audit_routes(app)
    register_build_audit_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/workbench/drift-report" in rules
    assert "/api/v1/workbench/audit-report" in rules

    payload = build_drift_report(app)
    assert payload["schema"] == "socmint.v7_5.drift_report"
    assert payload["approved_line"] == "v7.5"
    assert "full_dossier_pipeline" in payload["allowed_workbench_job_types"]
    assert "/api/v1/workbench/scope-lock" in payload["available_routes"]
    assert payload["scope_lock"]["approved_build_line"] == "v7.5"


def test_audit_report_payload_shape():
    app = create_app()
    register_full_report_aliases(app)
    register_scope_lock_routes(app)
    register_build_audit_routes(app)

    payload = build_audit_report(app, limit=10)
    assert payload["schema"] == "socmint.v7_5.audit_report"
    assert payload["approved_line"] == "v7.5"
    assert "counts" in payload
    assert "audit_events" in payload["counts"]
    assert "policy_events" in payload["counts"]
    assert "workbench_jobs" in payload["counts"]
    assert payload["drift"]["schema"] == "socmint.v7_5.drift_report"

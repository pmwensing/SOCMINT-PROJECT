from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_recovery_chain_closure_audit_v16_18 import CHAIN_STAGES
from src.socmint.case_delivery_recovery_chain_closure_audit_v16_18 import OPERATIONS_RETURN_ROUTE
from src.socmint.case_delivery_recovery_chain_closure_audit_v16_18 import audit_case_delivery_recovery_chain_closure
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app


def _registered_routes(app):
    return list(app.url_map.iter_rules())


def test_v16_18_closure_audit_passes_with_registered_routes():
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)

    result = audit_case_delivery_recovery_chain_closure(routes=_registered_routes(app))

    assert result["status"] == "closed"
    assert result["closed"] is True
    assert result["stage_count"] == 15
    assert result["blocker_count"] == 0
    assert result["operations_return_route"] == OPERATIONS_RETURN_ROUTE
    assert result["operations_return_route_registered"] is True
    assert result["duplicate_routes"] == []
    assert result["migration_artifacts"] == []
    assert result["orphaned_artifacts"] == []
    assert result["next_action"] == "return_to_product_level_work"


def test_v16_18_audit_covers_all_recovery_versions():
    versions = [stage["version"] for stage in CHAIN_STAGES]

    assert versions == [
        "v16.3",
        "v16.4",
        "v16.5",
        "v16.6",
        "v16.7",
        "v16.8",
        "v16.9",
        "v16.10",
        "v16.11",
        "v16.12",
        "v16.13",
        "v16.14",
        "v16.15",
        "v16.16",
        "v16.17",
    ]


def test_v16_18_detects_missing_route_and_duplicate_route_drift():
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    routes = _registered_routes(app)
    trimmed_routes = [route for route in routes if route.rule != "/api/v1/case-delivery/<case_id>/recovery"]
    duplicate_routes = trimmed_routes + [next(route for route in routes if route.rule == "/api/v1/case-delivery/<case_id>/operations")]

    result = audit_case_delivery_recovery_chain_closure(routes=duplicate_routes)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "missing_route" for blocker in result["blockers"])
    assert any(blocker["key"] == "duplicate_route_drift" for blocker in result["blockers"])
    assert "v16.3" in result["orphaned_artifacts"]


def test_v16_18_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-chain-closure-audit",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_v16_18_route_returns_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-chain-closure-audit",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "closed"
    assert payload["closed"] is True
    assert payload["operations_return_route_registered"] is True
    assert payload["next_action"] == "return_to_product_level_work"


def test_v16_18_release_note_and_changelog_are_present():
    note = Path("release/V16_18_RECOVERY_CHAIN_CLOSURE_AUDIT.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-chain-closure-audit" in note
    assert "v16.18 Recovery Chain Closure / Integration Checkpoint" in changelog

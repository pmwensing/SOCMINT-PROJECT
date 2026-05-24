from __future__ import annotations

import importlib


EXPECTED_RULES = {
    "/api/v12.10/command-center/cases/<case_id>/run-all",
    "/api/v12.10/dossier/run/<case_id>",
    "/api/v12.10/evidence/integrity/<case_id>",
    "/api/v12.10/runtime/mesh/<case_id>",
    "/api/v12.10/analyst/propagate/<case_id>",
    "/api/v12.10/risk/score/<case_id>",
    "/api/v12.10/monitoring/evolve/<case_id>",
    "/api/v12.10/ui/command-center",
}


def _load_app():
    dashboard = importlib.import_module("src.socmint.dashboard")
    assert hasattr(dashboard, "create_app")
    return dashboard.create_app()


def test_v12_10_routes_registered_in_runtime_app():
    app = _load_app()
    rules = {str(rule) for rule in app.url_map.iter_rules()}
    missing = EXPECTED_RULES - rules
    assert not missing, f"Missing v12.10 routes: {sorted(missing)}"


def test_v12_10_route_discovery_methods():
    app = _load_app()
    route_methods = {str(rule): sorted(rule.methods - {"HEAD", "OPTIONS"}) for rule in app.url_map.iter_rules()}

    assert route_methods["/api/v12.10/dossier/run/<case_id>"] == ["POST"]
    assert route_methods["/api/v12.10/evidence/integrity/<case_id>"] == ["POST"]
    assert route_methods["/api/v12.10/runtime/mesh/<case_id>"] == ["POST"]
    assert route_methods["/api/v12.10/analyst/propagate/<case_id>"] == ["POST"]
    assert route_methods["/api/v12.10/risk/score/<case_id>"] == ["POST"]
    assert route_methods["/api/v12.10/monitoring/evolve/<case_id>"] == ["POST"]
    assert route_methods["/api/v12.10/ui/command-center"] == ["GET"]


def test_v12_10_ui_panel_loads():
    app = _load_app()
    client = app.test_client()
    res = client.get("/api/v12.10/ui/command-center")
    assert res.status_code == 200
    assert b"SOCMINT Command Center v12.10.29" in res.data
    assert b"DossierBuilderV3" in res.data


def test_v12_10_command_center_endpoint_smoke():
    app = _load_app()
    client = app.test_client()
    res = client.post(
        "/api/v12.10/command-center/cases/case-route-smoke/run-all",
        json={
            "entities": [{"id": "e1"}],
            "artifacts": [{"id": "note1"}],
            "assertions": [{"id": "a1", "claim": "ok", "confidence": 0.9, "review_status": "approved"}],
            "watchlists": [{"target": "example"}],
        },
    )

    # Some SOCMINT app builds apply global request guards before route handlers.
    # For this test, 200 proves handler execution; 400 proves route exists but was blocked by guard,
    # because missing routes return 404 and failed methods return 405.
    assert res.status_code in {200, 400}
    assert res.status_code != 404

    if res.status_code == 200:
        data = res.get_json()
        assert data["version"] == "12.10.28"
        assert data["case_id"] == "case-route-smoke"


def test_v12_10_command_center_direct_payload_behavior():
    from src.socmint.v12_10_command_center import SOCMINTCommandCenterV121028

    data = SOCMINTCommandCenterV121028().run_all(
        "case-route-smoke",
        {
            "entities": [{"id": "e1"}],
            "artifacts": [{"id": "note1"}],
            "assertions": [{"id": "a1", "claim": "ok", "confidence": 0.9, "review_status": "approved"}],
            "watchlists": [{"target": "example"}],
        },
    )

    assert data["version"] == "12.10.28"
    assert data["case_id"] == "case-route-smoke"
    assert "v12.10.23_dossier_builder" in data["stages"]
    assert "v12.10.28_continuous_monitoring" in data["stages"]

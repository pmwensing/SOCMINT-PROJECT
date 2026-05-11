import pytest

from src.socmint import database as db
from src.socmint.dashboard import create_app
from src.socmint.high_end_workflows import capture_snapshot
from src.socmint.high_end_workflows import case_payload
from src.socmint.high_end_workflows import create_case
from src.socmint.high_end_workflows import gate_action
from src.socmint.high_end_workflows import load_scope
from src.socmint.high_end_workflows import save_scope
from src.socmint.high_end_workflows import verify_capture
from src.socmint.spine import create_subject


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "test-secret-key-with-enough-entropy")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "true")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SOCMINT_ADMIN_USER", raising=False)
    monkeypatch.delenv("SOCMINT_ADMIN_PASSWORD", raising=False)
    app = create_app(f"sqlite:///{tmp_path / 'socmint-high-end.db'}")
    app.config.update(TESTING=True)
    return app


def authorize(client):
    with client.session_transaction() as session:
        session["user"] = "tester"
        session["role"] = "analyst"
        session["is_admin"] = True


def test_case_capture_scope_and_verification(app):
    subject_id = create_subject(
        "High End Subject",
        [{"type": "email", "value": "high@example.com"}],
    )
    case = create_case("High End Case", case_key="high-end", actor="tester")
    save_scope(
        {
            "allowed_targets": ["example.com"],
            "blocked_targets": ["blocked.example"],
        },
        actor="tester",
    )
    capture = capture_snapshot(
        "https://example.com/profile",
        "<html>profile</html>",
        case_key=case["case_key"],
        subject_id=subject_id,
        actor="tester",
    )
    verification = verify_capture(capture["captures"][0]["capture_id"])
    blocked = gate_action("capture", "https://blocked.example/profile", "tester")
    payload = case_payload("high-end")

    assert load_scope()["allowed_targets"] == ["example.com"]
    assert verification["valid"] is True
    assert blocked["allowed"] is False
    assert payload["captures"]
    assert payload["subjects"] == [subject_id]


def test_high_end_routes_render_and_return_json(app):
    subject_id = create_subject(
        "Route Subject",
        [{"type": "username", "value": "routeuser"}],
    )
    create_case("Route Case", case_key="route-case", actor="tester")

    pages = [
        "/analyst/console",
        "/evidence/capture",
        "/cases",
        "/cases/route-case",
        "/connectors/marketplace",
        "/responsible-use",
        "/exports/builder",
        f"/spine/{subject_id}/graph/canvas",
        f"/spine/{subject_id}/resolution-lab",
    ]
    apis = [
        "/api/v1/analyst/workbench",
        "/api/v1/evidence/captures",
        "/api/v1/cases",
        "/api/v1/connectors/marketplace",
        "/api/v1/responsible-use/scope",
        "/api/v1/exports/builder",
        f"/api/v1/spine/{subject_id}/graph/canvas",
        f"/api/v1/spine/{subject_id}/resolution-lab",
    ]

    with app.test_client() as client:
        authorize(client)
        for route in pages:
            assert client.get(route).status_code == 200, route
        for route in apis:
            response = client.get(route)
            assert response.status_code == 200, route
            assert response.is_json, route


def test_migration_metadata_has_high_end_tables(app):
    assert db.CaseRecord.__tablename__ in db.Base.metadata.tables
    assert db.EvidenceCapture.__tablename__ in db.Base.metadata.tables
    assert db.ResponsibleUseScope.__tablename__ in db.Base.metadata.tables

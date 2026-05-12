import pytest

from src.socmint import database as db
from src.socmint.dashboard import create_app
from src.socmint.high_end_workflows import build_export_bundle
from src.socmint.high_end_workflows import capture_browser_snapshot
from src.socmint.high_end_workflows import capture_snapshot
from src.socmint.high_end_workflows import case_payload
from src.socmint.high_end_workflows import create_case
from src.socmint.high_end_workflows import gate_action
from src.socmint.high_end_workflows import load_scope
from src.socmint.high_end_workflows import save_scope
from src.socmint.high_end_workflows import verify_capture
from src.socmint.high_end_workflows import verify_export_bundle
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
        session["_csrf_token"] = "test-csrf-token"


def csrf_headers() -> dict[str, str]:
    return {"X-CSRF-Token": "test-csrf-token"}


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


def test_browser_capture_writes_snapshot_pdf_archive_and_manifest(app):
    case = create_case("Browser Case", case_key="browser-case", actor="tester")
    save_scope({"allowed_targets": ["example.com"]}, actor="tester")

    capture = capture_browser_snapshot(
        "https://example.com/browser",
        html="<html><body>browser</body></html>",
        case_key=case["case_key"],
        actor="tester",
        use_playwright=False,
    )
    types = {item["artifact_type"] for item in capture["captures"]}
    manifest = next(
        item for item in capture["captures"] if item["artifact_type"] == "manifest"
    )

    assert {"html", "screenshot", "pdf", "mhtml", "manifest"} <= types
    assert verify_capture(manifest["capture_id"])["valid"] is True
    assert capture["manifest_capture_id"] == manifest["capture_id"]


def test_high_end_export_bundle_builds_and_verifies(app):
    subject_id = create_subject(
        "Bundle Subject",
        [{"type": "email", "value": "bundle@example.com"}],
    )
    create_case("Bundle Case", case_key="bundle-case", actor="tester")

    bundle = build_export_bundle(
        subject_id=subject_id,
        case_key="bundle-case",
        redaction_preset="court",
        actor="tester",
    )
    verification = verify_export_bundle(bundle["bundle"]["name"])

    assert bundle["schema"] == "socmint.high_end_export_bundle_manifest.v8_0_1"
    assert bundle["bundle"]["sha256"]
    assert bundle["redaction_preset"] == "court"
    assert verification["valid"] is True


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
        bundle = client.post(
            "/api/v1/exports/builder/bundle",
            json={"subject_id": subject_id, "case_key": "route-case"},
            headers=csrf_headers(),
        )
        assert bundle.status_code == 201
        name = bundle.get_json()["bundle"]["name"]
        verify = client.get(f"/api/v1/exports/builder/bundles/{name}/verify")
        assert verify.status_code == 200
        assert verify.get_json()["valid"] is True


def test_migration_metadata_has_high_end_tables(app):
    assert db.CaseRecord.__tablename__ in db.Base.metadata.tables
    assert db.EvidenceCapture.__tablename__ in db.Base.metadata.tables
    assert db.ResponsibleUseScope.__tablename__ in db.Base.metadata.tables

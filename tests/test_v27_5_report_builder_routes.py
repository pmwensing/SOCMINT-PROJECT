from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY", "v27-5-route-test-secret-key-with-more-than-32-characters"
    )
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v27_5_routes_require_login_csrf_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import report_builder_routes_v27_5 as routes

    monkeypatch.setattr(routes, "current_reports", lambda: [])
    monkeypatch.setattr(routes, "latest_packages", lambda: [])
    monkeypatch.setattr(
        routes,
        "create_report_definition",
        lambda **kwargs: {
            "status": "report_definition_created",
            "report_id": "report-1",
        },
    )
    monkeypatch.setattr(
        routes,
        "revise_report_definition",
        lambda *args, **kwargs: {
            "status": "report_definition_revised",
            "report_id": "report-2",
        },
    )
    monkeypatch.setattr(
        routes,
        "generate_report_package",
        lambda *args, **kwargs: {
            "status": "report_package_generated",
            "package_id": "package-1",
            "files": [],
        },
    )
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/global-search/reports").status_code == 401
    assert client.get("/global-search/reports").status_code in {302, 303}
    csrf = "v27-5-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "alice"
        sess["allowed_case_ids"] = ["case-a"]
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/global-search/reports").status_code == 200
    sections = [{"section_type": "text", "title": "Notes", "text": "Summary"}]
    created = client.post(
        "/api/v1/global-search/reports",
        json={
            "name": "Report",
            "description": "",
            "visibility": "private",
            "sections": sections,
            "export_formats": ["json"],
            "confirmed": True,
        },
        headers=headers,
    )
    revised = client.post(
        "/api/v1/global-search/reports/report-1/revise",
        json={
            "name": "Report 2",
            "description": "",
            "visibility": "shared",
            "sections": sections,
            "export_formats": ["json", "html"],
            "reason": "update",
            "confirmed": True,
        },
        headers=headers,
    )
    generated = client.post(
        "/api/v1/global-search/reports/report-2/generate",
        json={"formats": ["json", "csv", "html"], "limit": 25, "confirmed": True},
        headers=headers,
    )
    assert [created.status_code, revised.status_code, generated.status_code] == [
        200,
        200,
        200,
    ]


def test_v27_5_release_note_and_no_migration():
    note = Path("release/V27_5_REPORT_BUILDER_EXPORT_PACKAGES.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "Report Builder and Export Packages",
        "immutable report definitions",
        "JSON, CSV, and HTML",
        "source bindings",
        "file manifest",
        "package SHA-256",
        "current case access scope",
        "reports do not grant access",
        "append-only",
        "no migration",
    ):
        assert phrase in note
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v27_5*")
    ]
    assert migrations == []

from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.operator_release_console_routes_v14 import register_operator_release_console_routes_v14
from src.socmint.operator_release_console_v14 import OPERATOR_RELEASE_CONSOLE_SCHEMA
from src.socmint.operator_release_console_v14 import operator_release_console_payload


def test_operator_release_console_payload_summarizes_release_evidence():
    payload = operator_release_console_payload()

    assert payload["schema"] == OPERATOR_RELEASE_CONSOLE_SCHEMA
    assert payload["release_line"] == "v14.0"
    assert payload["decision"] == "GO_FOR_V14"
    assert payload["status"] == "pass"
    assert payload["summary"]["needs_review"] == 0
    assert payload["pr_queue"]["status"] == "clean_documented"
    assert payload["pr_queue"]["closed_superseded_prs"] == [
        "#139",
        "#140",
        "#141",
        "#142",
        "#143",
        "#144",
    ]
    assert payload["git"]["commit"]


def test_operator_release_console_payload_marks_missing_docs(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    payload = operator_release_console_payload(tmp_path)

    assert payload["decision"] == "HOLD_FOR_RELEASE_REPAIR"
    assert payload["status"] == "needs_review"
    assert payload["summary"]["needs_review"] > 0
    assert any(item["source"] == "release/V13_RELEASE_DOCUMENTATION_CLOSURE.md" for item in payload["checks"])


def test_operator_release_console_routes_require_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_operator_release_console_routes_v14(app)
    client = app.test_client()

    api_response = client.get("/api/v1/operator/release-console")
    ui_response = client.get("/operator/release-console")

    assert api_response.status_code == 401
    assert ui_response.status_code == 302
    assert "/login" in ui_response.headers["Location"]


def test_operator_release_console_routes_render_for_logged_in_user(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_operator_release_console_routes_v14(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["is_admin"] = False

    api_response = client.get("/api/v1/operator/release-console")
    ui_response = client.get("/operator/release-console")
    alias_response = client.get("/release/console")

    assert api_response.status_code == 200
    assert api_response.get_json()["schema"] == OPERATOR_RELEASE_CONSOLE_SCHEMA
    assert ui_response.status_code == 200
    assert b"Operator Release Console" in ui_response.data
    assert b"GO_FOR_V14" in ui_response.data
    assert alias_response.status_code == 200


def test_v14_release_note_and_changelog_are_present():
    note = Path("release/V14_0_OPERATOR_RELEASE_CONSOLE.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/operator/release-console" in note
    assert "v14.0 Operator Release Console" in changelog

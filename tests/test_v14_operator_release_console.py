from pathlib import Path
import json
from datetime import UTC, datetime

from src.socmint.dashboard import create_app
from src.socmint.operator_release_console_routes_v14 import (
    register_operator_release_console_routes_v14,
)
from src.socmint.operator_release_console_v14 import OPERATOR_RELEASE_CONSOLE_SCHEMA
from src.socmint.operator_release_console_v14 import _operator_release_evaluation
from src.socmint.operator_release_console_v14 import _snapshot_freshness
from src.socmint.operator_release_console_v14 import operator_release_console_payload
from scripts.refresh_operator_release_health_v14_1 import (
    SCHEMA as RELEASE_HEALTH_SCHEMA,
)
from scripts.refresh_operator_release_health_v14_1 import build_release_health_snapshot


def test_operator_release_console_payload_summarizes_release_evidence():
    payload = operator_release_console_payload()

    assert payload["schema"] == OPERATOR_RELEASE_CONSOLE_SCHEMA
    assert payload["release_line"] == "v14.0"
    assert payload["decision"] == "GO_FOR_V14"
    assert payload["status"] == "pass"
    assert payload["summary"]["needs_review"] == 0
    assert payload["pr_queue"]["status"] == "clean_documented"
    assert payload["release_health"]["status"] in {"pass", "needs_review"}
    assert payload["release_health"]["open_pr_count"] == 0
    expected_evaluation = (
        "EVALUATION_POINT_REACHED"
        if payload["release_health"]["status"] == "pass"
        and payload["release_health"].get("freshness", {}).get("ok")
        else "REFRESH_RELEASE_HEALTH"
    )
    assert payload["evaluation"]["decision"] == expected_evaluation
    assert payload["evaluation"]["blocker_count"] == 0
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
    assert any(
        item["source"] == "release/V13_RELEASE_DOCUMENTATION_CLOSURE.md"
        for item in payload["checks"]
    )


def test_operator_release_console_payload_marks_missing_release_health_snapshot(
    tmp_path,
):
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    for source in [
        "V13_RELEASE_DOCUMENTATION_CLOSURE.md",
        "V13_RELEASE_SEQUENCE_AUDIT.md",
        "V13_35_FINAL_CORRELATION_SCOPE_CLOSURE.md",
        "V13_36_TO_44_EXPORT_BLOCKER_INDEX.md",
        "V13_45_TO_48_EXPORT_BLOCKER_WORKFLOW_INDEX.md",
        "V13_25_RESERVED_GAP.md",
        "V10_32_TO_37_OPEN_PR_TRIAGE.md",
    ]:
        (release_dir / source).write_text("# present\n", encoding="utf-8")
    (release_dir / "OPEN_PR_QUEUE_CLOSURE.md").write_text(
        "\n".join(f"PR #{number} closed" for number in range(139, 145)),
        encoding="utf-8",
    )
    (tmp_path / "CHANGELOG.md").write_text(
        "v14.0 Operator Release Console\n", encoding="utf-8"
    )

    payload = operator_release_console_payload(tmp_path)

    assert payload["release_health"]["status"] == "missing"
    assert payload["decision"] == "HOLD_FOR_RELEASE_REPAIR"
    assert any(item["key"] == "release_health_snapshot" for item in payload["checks"])


def test_operator_release_console_payload_loads_release_health_snapshot(tmp_path):
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    for source in [
        "V13_RELEASE_DOCUMENTATION_CLOSURE.md",
        "V13_RELEASE_SEQUENCE_AUDIT.md",
        "V13_35_FINAL_CORRELATION_SCOPE_CLOSURE.md",
        "V13_36_TO_44_EXPORT_BLOCKER_INDEX.md",
        "V13_45_TO_48_EXPORT_BLOCKER_WORKFLOW_INDEX.md",
        "V13_25_RESERVED_GAP.md",
        "V10_32_TO_37_OPEN_PR_TRIAGE.md",
    ]:
        (release_dir / source).write_text("# present\n", encoding="utf-8")
    (release_dir / "OPEN_PR_QUEUE_CLOSURE.md").write_text(
        "\n".join(f"PR #{number} closed" for number in range(139, 145)),
        encoding="utf-8",
    )
    (release_dir / "OPERATOR_RELEASE_HEALTH.json").write_text(
        json.dumps(
            {
                "schema": RELEASE_HEALTH_SCHEMA,
                "generated_at": "2026-06-10T04:40:00+00:00",
                "open_pr_count": 0,
                "latest_master": {"headSha": "abc123"},
                "checks": [
                    {
                        "workflowName": "CI",
                        "status": "completed",
                        "conclusion": "success",
                        "url": "https://example.test/ci",
                    }
                ],
                "note": "test snapshot",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "CHANGELOG.md").write_text(
        "v14.0 Operator Release Console\n", encoding="utf-8"
    )

    payload = operator_release_console_payload(tmp_path)

    assert payload["release_health"]["status"] in {"pass", "needs_review"}
    assert payload["release_health"]["schema"] == RELEASE_HEALTH_SCHEMA
    assert payload["release_health"]["latest_master"]["headSha"] == "abc123"
    assert next(
        item for item in payload["checks"] if item["key"] == "release_health_snapshot"
    )["status"] in {"pass", "needs_review"}


def test_release_health_snapshot_freshness_marks_fresh_snapshot(monkeypatch):
    monkeypatch.delenv("SOCMINT_RELEASE_HEALTH_MAX_AGE_HOURS", raising=False)

    freshness = _snapshot_freshness(
        "2026-06-10T04:40:00+00:00",
        now=datetime(2026, 6, 10, 6, 10, tzinfo=UTC),
    )

    assert freshness["status"] == "fresh"
    assert freshness["ok"] is True
    assert freshness["age_hours"] == 1.5
    assert freshness["max_age_hours"] == 24


def test_release_health_snapshot_freshness_marks_stale_snapshot(monkeypatch):
    monkeypatch.setenv("SOCMINT_RELEASE_HEALTH_MAX_AGE_HOURS", "2")

    freshness = _snapshot_freshness(
        "2026-06-10T04:00:00+00:00",
        now=datetime(2026, 6, 10, 7, 30, tzinfo=UTC),
    )

    assert freshness["status"] == "stale"
    assert freshness["ok"] is False
    assert freshness["age_hours"] == 3.5
    assert freshness["max_age_hours"] == 2


def test_release_health_snapshot_freshness_handles_missing_and_invalid_timestamp(
    monkeypatch,
):
    monkeypatch.delenv("SOCMINT_RELEASE_HEALTH_MAX_AGE_HOURS", raising=False)

    missing = _snapshot_freshness(None)
    invalid = _snapshot_freshness("not-a-date")

    assert missing["status"] == "missing_timestamp"
    assert missing["ok"] is False
    assert invalid["status"] == "invalid_timestamp"
    assert invalid["ok"] is False


def test_operator_release_evaluation_reaches_evaluation_point():
    checks = [
        {
            "key": "docs",
            "label": "Docs",
            "ok": True,
            "source": "release",
            "detail": "present",
        },
        {"key": "git", "label": "Git", "ok": True, "source": "git", "detail": "clean"},
    ]
    release_health = {"status": "pass", "freshness": {"ok": True}}

    evaluation = _operator_release_evaluation(checks, release_health)

    assert evaluation["decision"] == "EVALUATION_POINT_REACHED"
    assert evaluation["status"] == "pass"
    assert evaluation["blocker_count"] == 0
    assert "release health snapshot fresh" in evaluation["criteria"]


def test_operator_release_evaluation_pauses_on_blockers():
    checks = [
        {
            "key": "docs",
            "label": "Docs",
            "ok": True,
            "source": "release",
            "detail": "present",
        },
        {
            "key": "snapshot",
            "label": "Snapshot",
            "ok": False,
            "source": "release/OPERATOR_RELEASE_HEALTH.json",
            "detail": "stale",
        },
    ]
    release_health = {"status": "needs_review", "freshness": {"ok": False}}

    evaluation = _operator_release_evaluation(checks, release_health)

    assert evaluation["decision"] == "PAUSE_FOR_REPAIR"
    assert evaluation["status"] == "needs_review"
    assert evaluation["blocker_count"] == 1
    assert evaluation["blockers"][0]["key"] == "snapshot"


def test_refresh_release_health_snapshot_builds_from_gh_payload(monkeypatch):
    def fake_gh_json(args):
        if args[:3] == ["pr", "list", "--state"]:
            return []
        return [
            {
                "databaseId": 1,
                "workflowName": "CI",
                "status": "completed",
                "conclusion": "success",
                "headSha": "abc123",
                "url": "https://example.test/ci",
                "createdAt": "2026-06-10T04:40:00Z",
            },
            {
                "databaseId": 2,
                "workflowName": "SOCMINT v12.10.19 Verify",
                "status": "completed",
                "conclusion": "success",
                "headSha": "abc123",
                "url": "https://example.test/verify",
                "createdAt": "2026-06-10T04:40:00Z",
            },
        ]

    monkeypatch.setattr(
        "scripts.refresh_operator_release_health_v14_1._gh_json", fake_gh_json
    )

    snapshot = build_release_health_snapshot()

    assert snapshot["schema"] == RELEASE_HEALTH_SCHEMA
    assert snapshot["status"] == "pass"
    assert snapshot["open_pr_count"] == 0
    assert [check["workflowName"] for check in snapshot["checks"]] == [
        "CI",
        "SOCMINT v12.10.19 Verify",
    ]


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


def test_operator_release_console_routes_render_for_logged_in_user(
    tmp_path, monkeypatch
):
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
    v14_1_note = Path("release/V14_1_RELEASE_HEALTH_SNAPSHOT.md").read_text(
        encoding="utf-8"
    )
    v14_2_note = Path("release/V14_2_RELEASE_HEALTH_FRESHNESS.md").read_text(
        encoding="utf-8"
    )
    v14_3_note = Path("release/V14_3_OPERATOR_RELEASE_EVALUATION_POINT.md").read_text(
        encoding="utf-8"
    )
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/operator/release-console" in note
    assert "OPERATOR_RELEASE_HEALTH.json" in v14_1_note
    assert "SOCMINT_RELEASE_HEALTH_MAX_AGE_HOURS" in v14_2_note
    assert "EVALUATION_POINT_REACHED" in v14_3_note
    assert "v14.0 Operator Release Console" in changelog
    assert "v14.1 release-health snapshot" in changelog
    assert "v14.2 release-health freshness" in changelog
    assert "v14.3 Operator Release Console evaluation point" in changelog

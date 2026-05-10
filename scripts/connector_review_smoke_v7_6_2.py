from __future__ import annotations

import os
import tempfile

from socmint import database as db
from socmint.command_center_routes import register_command_center_routes
from socmint.connector_review import connector_run_detail_payload
from socmint.connector_review import finding_queue_payload
from socmint.connector_review import review_finding
from socmint.connector_review_routes import register_connector_review_routes
from socmint.connector_runtime_routes import register_connector_runtime_routes
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow
from socmint.full_report_history import register_full_report_history_routes
from socmint.full_report_retention import register_full_report_retention_routes
from socmint.spine import create_subject


def _record_run(target_id: int, target_value: str, value: str) -> tuple[int, int]:
    raw_result = {
        "connector": "sherlock",
        "target": target_value,
        "target_type": "username",
        "status": "completed",
        "command": ["sherlock", target_value],
        "stdout": f"Found: {value}",
        "stderr": "",
        "findings": [
            {
                "type": "profile_url",
                "value": value,
                "source": "sherlock",
                "confidence": 0.78,
                "context": {"site": "example"},
            }
        ],
    }
    run_id = db.record_connector_run(
        target_value=target_value,
        target_type="username",
        connector="sherlock",
        raw_result=raw_result,
        target_id=target_id,
    )
    detail = connector_run_detail_payload(run_id)
    assert detail["findings"]
    return run_id, detail["findings"][0]["id"]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="socmint-v762-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        db.configure_database(os.environ["DATABASE_URL"])

        subject_id = create_subject(
            "Connector Review QA v7.6.2",
            [{"type": "username", "value": "review-target"}],
        )
        target = db.Target(type="username", value="review-target")
        session_db = db.Session()
        session_db.add(target)
        session_db.commit()
        session_db.refresh(target)
        target_id = target.id
        session_db.close()

        promote_run_id, promote_finding_id = _record_run(
            target_id,
            "review-target",
            "https://example.com/promote-target",
        )
        reject_run_id, reject_finding_id = _record_run(
            target_id,
            "reject-target",
            "https://example.com/reject-target",
        )
        uncertain_run_id, uncertain_finding_id = _record_run(
            target_id,
            "uncertain-target",
            "https://example.com/uncertain-target",
        )

        detail = connector_run_detail_payload(promote_run_id)
        assert detail["schema"] == "socmint.connector_review.v7_6_2_1"
        assert detail["run"]["stdout"].startswith("Found:")
        assert detail["findings"][0]["review_state"] == "unreviewed"

        queue = finding_queue_payload()
        assert queue["status_filter"] == "unreviewed"
        assert queue["count"] == 3
        assert queue["counts"]["unreviewed"] == 3

        try:
            review_finding(promote_finding_id, "promote", actor="connector-review-smoke")
            raise AssertionError("promote without subject should fail")
        except ValueError:
            pass

        promoted = review_finding(
            promote_finding_id,
            "promote",
            actor="connector-review-smoke",
            subject_id=subject_id,
            note="smoke promotion",
        )
        assert promoted["assertion_id"]
        assert promoted["review_state"] == "promote"
        assertions = db.list_spine_assertions(subject_id)
        assert any(item.normalized_value == "https://example.com/promote-target" for item in assertions)

        rejected = review_finding(reject_finding_id, "reject", actor="connector-review-smoke")
        assert rejected["validation_state"] == "rejected"
        uncertain = review_finding(uncertain_finding_id, "uncertain", actor="connector-review-smoke")
        assert uncertain["validation_state"] == "uncertain"

        assert finding_queue_payload()["count"] == 0
        assert finding_queue_payload(status="promote")["count"] == 1
        assert finding_queue_payload(status="rejected")["count"] == 1
        assert finding_queue_payload(status="uncertain")["count"] == 1
        assert finding_queue_payload(status="all")["count"] == 3

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="connector-review-smoke")
        register_full_report_aliases(app)
        register_full_report_browser_flow(app)
        register_full_report_history_routes(app)
        register_full_report_retention_routes(app)
        register_command_center_routes(app)
        register_connector_runtime_routes(app)
        register_connector_review_routes(app)

        with app.test_client() as client:
            csrf = "connector-review-csrf"
            with client.session_transaction() as session:
                session["user"] = "connector-review-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = csrf

            runs_page = client.get("/connectors/runs")
            assert runs_page.status_code == 200
            assert "Connector Runs" in runs_page.get_data(as_text=True)
            assert "review-target" in runs_page.get_data(as_text=True)

            detail_page = client.get(f"/connectors/runs/{promote_run_id}")
            assert detail_page.status_code == 200
            detail_text = detail_page.get_data(as_text=True)
            assert "Raw stdout" in detail_text
            assert "Raw stderr" in detail_text
            assert "Raw JSON" in detail_text
            assert "https://example.com/promote-target" in detail_text

            queue_page = client.get("/connectors/findings")
            assert queue_page.status_code == 200
            queue_text = queue_page.get_data(as_text=True)
            assert "Finding Promotion Queue" in queue_text
            assert "No connector findings match this filter" in queue_text
            assert "Unreviewed" in queue_text and "Promoted" in queue_text

            promoted_page = client.get("/connectors/findings?status=promote")
            assert promoted_page.status_code == 200
            assert "https://example.com/promote-target" in promoted_page.get_data(as_text=True)

            api_runs = client.get("/api/v1/connectors/runs")
            assert api_runs.status_code == 200
            assert api_runs.get_json()["schema"] == "socmint.connector_review.v7_6_2_1"

            api_detail = client.get(f"/api/v1/connectors/runs/{promote_run_id}")
            assert api_detail.status_code == 200
            assert api_detail.get_json()["findings"][0]["id"] == promote_finding_id

            api_queue = client.get("/api/v1/connectors/findings")
            assert api_queue.status_code == 200
            assert api_queue.get_json()["count"] == 0
            api_all = client.get("/api/v1/connectors/findings?status=all")
            assert api_all.status_code == 200
            assert api_all.get_json()["count"] == 3

            form_review = client.post(
                f"/connectors/findings/{promote_finding_id}/review",
                data={"csrf_token": csrf, "action": "uncertain", "note": "form review"},
                follow_redirects=True,
            )
            assert form_review.status_code == 200
            assert "Finding marked uncertain" in form_review.get_data(as_text=True)

            command_center = client.get("/")
            assert command_center.status_code == 200
            center_text = command_center.get_data(as_text=True)
            assert "Connector Runs" in center_text
            assert "Finding Queue" in center_text
            assert "Connector Runtime" in center_text

        print("v7.6.2 connector review smoke passed")


if __name__ == "__main__":
    main()

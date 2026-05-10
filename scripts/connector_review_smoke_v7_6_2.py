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

        raw_result = {
            "connector": "sherlock",
            "target": "review-target",
            "target_type": "username",
            "status": "completed",
            "command": ["sherlock", "review-target"],
            "stdout": "Found: https://example.com/review-target",
            "stderr": "",
            "findings": [
                {
                    "type": "profile_url",
                    "value": "https://example.com/review-target",
                    "source": "sherlock",
                    "confidence": 0.78,
                    "context": {"site": "example"},
                }
            ],
        }
        run_id = db.record_connector_run(
            target_value="review-target",
            target_type="username",
            connector="sherlock",
            raw_result=raw_result,
            target_id=target_id,
        )

        detail = connector_run_detail_payload(run_id)
        assert detail["schema"] == "socmint.connector_review.v7_6_2"
        assert detail["run"]["stdout"].startswith("Found:")
        assert detail["findings"]
        finding_id = detail["findings"][0]["id"]

        queue = finding_queue_payload()
        assert queue["count"] == 1
        assert queue["findings"][0]["value"] == "https://example.com/review-target"

        promoted = review_finding(
            finding_id,
            "promote",
            actor="connector-review-smoke",
            subject_id=subject_id,
            note="smoke promotion",
        )
        assert promoted["assertion_id"]
        assertions = db.list_spine_assertions(subject_id)
        assert any(item.normalized_value == "https://example.com/review-target" for item in assertions)

        rejected = review_finding(finding_id, "reject", actor="connector-review-smoke")
        assert rejected["validation_state"] == "rejected"
        uncertain = review_finding(finding_id, "uncertain", actor="connector-review-smoke")
        assert uncertain["validation_state"] == "uncertain"

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

            detail_page = client.get(f"/connectors/runs/{run_id}")
            assert detail_page.status_code == 200
            detail_text = detail_page.get_data(as_text=True)
            assert "Raw stdout" in detail_text
            assert "Raw stderr" in detail_text
            assert "Raw JSON" in detail_text
            assert "https://example.com/review-target" in detail_text

            queue_page = client.get("/connectors/findings")
            assert queue_page.status_code == 200
            assert "Finding Promotion Queue" in queue_page.get_data(as_text=True)

            api_runs = client.get("/api/v1/connectors/runs")
            assert api_runs.status_code == 200
            assert api_runs.get_json()["schema"] == "socmint.connector_review.v7_6_2"

            api_detail = client.get(f"/api/v1/connectors/runs/{run_id}")
            assert api_detail.status_code == 200
            assert api_detail.get_json()["findings"][0]["id"] == finding_id

            api_queue = client.get("/api/v1/connectors/findings")
            assert api_queue.status_code == 200
            assert api_queue.get_json()["count"] == 1

            api_review = client.post(
                f"/api/v1/connectors/findings/{finding_id}/review",
                json={"action": "promote", "subject_id": subject_id, "note": "api promotion"},
                headers={"X-CSRF-Token": csrf},
            )
            assert api_review.status_code == 202, api_review.get_data(as_text=True)
            assert api_review.get_json()["assertion_id"]

            form_review = client.post(
                f"/connectors/findings/{finding_id}/review",
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

        print("v7.6.2 connector review smoke passed")


if __name__ == "__main__":
    main()

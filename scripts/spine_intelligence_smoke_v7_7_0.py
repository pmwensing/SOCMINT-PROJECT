from __future__ import annotations

import os
import tempfile

from socmint import database as db
from socmint.command_center_routes import register_command_center_routes
from socmint.connector_runtime_routes import register_connector_runtime_routes
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow
from socmint.full_report_history import register_full_report_history_routes
from socmint.full_report_retention import register_full_report_retention_routes
from socmint.spine import create_subject
from socmint.spine import run_spine_for_subject
from socmint.spine_intelligence import promote_observation_to_assertion
from socmint.spine_intelligence import review_spine_assertion
from socmint.spine_intelligence import spine_intelligence_payload
from socmint.spine_intelligence_routes import register_spine_intelligence_routes


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="socmint-v770-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        subject_id = create_subject(
            "Spine Native QA v7.7.0",
            [
                {"type": "username", "value": "spineqa"},
                {"type": "email", "value": "spineqa@example.com"},
                {"type": "phone", "value": "+15555550123"},
                {"type": "url", "value": "https://example.com/spineqa"},
            ],
        )

        empty_payload = spine_intelligence_payload(subject_id)
        assert empty_payload["schema"] == "socmint.spine_intelligence.v7_7_0"
        assert empty_payload["summary"]["seed_count"] == 4
        assert empty_payload["summary"]["connector_run_count"] == 0
        assert any(item["key"] == "sherlock" and item["enabled"] for item in empty_payload["connector_options"])
        assert any(item["key"] == "phoneinfoga" and item["enabled"] for item in empty_payload["connector_options"])

        run_result = run_spine_for_subject(subject_id, ["sherlock", "socialscan", "phoneinfoga", "archivebox"])
        assert run_result["run_ids"]

        payload = spine_intelligence_payload(subject_id)
        assert payload["summary"]["connector_run_count"] >= 4
        assert payload["summary"]["artifact_count"] >= 4
        assert payload["summary"]["observation_count"] >= 4
        assert payload["summary"]["assertion_count"] >= 1
        assert payload["summary"]["dossier_ready"] is True
        assert payload["runs"][0]["raw_result"]
        assert "stdout" in payload["runs"][0]
        assert payload["observations"]
        assert payload["assertions"]

        observation_id = payload["observations"][0]["id"]
        promoted = promote_observation_to_assertion(
            observation_id,
            actor="spine-intelligence-smoke",
            note="promote observation smoke",
        )
        assert promoted["assertion_id"]

        reviewed = review_spine_assertion(
            promoted["assertion_id"],
            "rejected",
            actor="spine-intelligence-smoke",
            note="review smoke",
        )
        assert reviewed["validation_state"] == "rejected"
        reviewed = review_spine_assertion(
            promoted["assertion_id"],
            "confirmed",
            actor="spine-intelligence-smoke",
            note="confirm smoke",
        )
        assert reviewed["validation_state"] == "confirmed"

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="spine-intelligence-smoke")
        register_full_report_aliases(app)
        register_full_report_browser_flow(app)
        register_full_report_history_routes(app)
        register_full_report_retention_routes(app)
        register_command_center_routes(app)
        register_connector_runtime_routes(app)
        register_spine_intelligence_routes(app)

        with app.test_client() as client:
            csrf = "spine-intelligence-csrf"
            with client.session_transaction() as session:
                session["user"] = "spine-intelligence-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = csrf

            page = client.get(f"/spine/subjects/{subject_id}/intelligence")
            assert page.status_code == 200
            text = page.get_data(as_text=True)
            assert "Spine-Native Subject Intelligence" in text
            assert "Dossier Assertions" in text
            assert "Spine Connector Runs + Raw Output" in text
            assert "Open Full Dossier v2" in text
            assert "Run selected connectors into Spine" in text

            api = client.get(f"/api/v1/spine/subjects/{subject_id}/intelligence")
            assert api.status_code == 200
            api_payload = api.get_json()
            assert api_payload["schema"] == "socmint.spine_intelligence.v7_7_0"
            assert api_payload["summary"]["connector_run_count"] >= 4

            api_run = client.post(
                f"/api/v1/spine/subjects/{subject_id}/intelligence/run",
                json={"connectors": ["sherlock"]},
                headers={"X-CSRF-Token": csrf},
            )
            assert api_run.status_code == 202, api_run.get_data(as_text=True)
            assert api_run.get_json()["run_ids"]

            observation_id = api_payload["observations"][0]["id"]
            api_promote = client.post(
                f"/api/v1/spine/observations/{observation_id}/promote",
                json={"note": "api promote"},
                headers={"X-CSRF-Token": csrf},
            )
            assert api_promote.status_code == 202, api_promote.get_data(as_text=True)
            assert api_promote.get_json()["assertion_id"]

            assertion_id = api_promote.get_json()["assertion_id"]
            api_review = client.post(
                f"/api/v1/spine/intelligence/assertions/{assertion_id}/review",
                json={"action": "confirmed", "note": "api confirm"},
                headers={"X-CSRF-Token": csrf},
            )
            assert api_review.status_code == 202, api_review.get_data(as_text=True)
            assert api_review.get_json()["validation_state"] == "confirmed"

            spine_list = client.get("/spine")
            assert spine_list.status_code == 200
            spine_text = spine_list.get_data(as_text=True)
            assert "Intelligence Console" in spine_text
            assert "Full Dossier v2" in spine_text

        print("v7.7.0 Spine intelligence smoke passed")


if __name__ == "__main__":
    main()

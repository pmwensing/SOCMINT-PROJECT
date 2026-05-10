from __future__ import annotations

import os
import tempfile

from socmint import database as db
from socmint.command_center import command_center_payload
from socmint.command_center import tool_compatibility
from socmint.command_center_routes import register_command_center_routes
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow
from socmint.full_report_history import register_full_report_history_routes
from socmint.full_report_retention import register_full_report_retention_routes
from socmint.spine import create_subject


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="socmint-command-v758-") as tmp:
        os.chdir(tmp)
        db.configure_database(f"sqlite:///{tmp}/socmint.db")

        subject_id = create_subject(
            "Command Center QA v7.5.8",
            [{"type": "username", "value": "test-v758"}],
        )
        job = db.create_scan_job(
            "analyst@example.com",
            "email",
            tools={"sherlock", "maigret"},
            enrich=True,
            requested_by="command-center-smoke",
        )

        compatibility = tool_compatibility("email", ["sherlock", "maigret"])
        assert compatibility["compatible"] is False
        assert compatibility["warnings"]
        assert "Email targets" in compatibility["warnings"][0]

        payload = command_center_payload()
        assert payload["schema"] == "socmint.command_center.v7_5_8"
        assert payload["summary"]["queued_jobs"] == 1
        assert payload["summary"]["subject_count"] >= 1
        assert payload["compatibility_warnings"]
        assert payload["compatibility_warnings"][0]["id"] == job.id
        assert payload["subjects"][0]["id"] == subject_id

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="command-center-smoke")
        register_full_report_aliases(app)
        register_full_report_browser_flow(app)
        register_full_report_history_routes(app)
        register_full_report_retention_routes(app)
        register_command_center_routes(app)

        with app.test_client() as client:
            csrf = "command-center-csrf-token"
            with client.session_transaction() as session:
                session["user"] = "command-center-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = csrf

            page = client.get("/")
            assert page.status_code == 200
            text = page.get_data(as_text=True)
            assert "SOCMINT Command Center" in text
            assert "Create / Open Subject" in text
            assert "Process queued jobs now" in text
            assert "Enrichment compatibility warnings" in text
            assert "Email targets do not work well" in text
            assert "Full Dossier v2" in text
            assert "Legacy local target scan" in text

            api = client.get("/api/v1/command-center")
            assert api.status_code == 200
            api_payload = api.get_json()
            assert api_payload["schema"] == "socmint.command_center.v7_5_8"
            assert api_payload["summary"]["queued_jobs"] == 1

            process = client.post(
                "/command-center/process-jobs",
                data={"csrf_token": csrf},
                follow_redirects=True,
            )
            assert process.status_code == 200
            process_text = process.get_data(as_text=True)
            assert "Processed 1 queued job" in process_text

            after = command_center_payload()
            assert after["summary"]["queued_jobs"] == 0
            assert after["summary"]["completed_jobs"] + after["summary"]["failed_jobs"] >= 1

        print("v7.5.8 command center UX smoke passed")


if __name__ == "__main__":
    main()

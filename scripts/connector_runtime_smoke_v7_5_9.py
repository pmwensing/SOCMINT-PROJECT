from __future__ import annotations

import os
import tempfile

from socmint import database as db
from socmint.command_center_routes import register_command_center_routes
from socmint.connector_runtime import connector_runtime_health
from socmint.connector_runtime import normalize_connector_output
from socmint.connector_runtime_routes import register_connector_runtime_routes
from socmint.connectors import CONNECTORS
from socmint.connectors import run_connector
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow
from socmint.full_report_history import register_full_report_history_routes
from socmint.full_report_retention import register_full_report_retention_routes

EXPECTED = {"sherlock", "maigret", "socialscan", "holehe", "h8mail", "phoneinfoga"}
VALID_SCHEMAS = {"socmint.connector_runtime.v7_5_9", "socmint.connector_runtime.v7_6_0"}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="socmint-runtime-v759-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        assert EXPECTED.issubset(set(CONNECTORS))

        health = connector_runtime_health()
        assert health["schema"] in VALID_SCHEMAS
        names = {item["name"] for item in health["connectors"]}
        assert EXPECTED.issubset(names)
        assert "archivebox" in names
        for item in health["connectors"]:
            assert item["status"] in {"ready", "missing", "disabled"}
            assert item["sample_command"]
            assert item["target_types"]

        payload = {
            "connector": "sherlock",
            "stdout": "Found: https://example.com/testuser\ncontact test@example.com",
            "stderr": "",
        }
        findings = normalize_connector_output("sherlock", payload)
        assert any(item["type"] in {"url", "profile_url"} for item in findings)
        assert any(item["type"] == "email" for item in findings)

        dry = run_connector("holehe", "test@example.com", "email", allow_dry_run=True)
        assert dry["status"] == "dry_run"
        assert dry["connector"] == "holehe"
        assert "findings" in dry

        skipped = run_connector(
            "phoneinfoga", "test@example.com", "email", allow_dry_run=True
        )
        assert skipped["status"] == "skipped"
        assert skipped["findings"] == []

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="connector-runtime-smoke")
        register_full_report_aliases(app)
        register_full_report_browser_flow(app)
        register_full_report_history_routes(app)
        register_full_report_retention_routes(app)
        register_command_center_routes(app)
        register_connector_runtime_routes(app)

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "connector-runtime-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "connector-runtime-csrf"

            page = client.get("/connectors/runtime")
            assert page.status_code == 200
            text = page.get_data(as_text=True)
            assert "Connector Runtime" in text
            assert "Tool install health" in text
            for name in EXPECTED:
                assert name in text
            assert "archivebox" in text

            api = client.get("/api/v1/connectors/runtime")
            assert api.status_code == 200
            assert api.get_json()["schema"] in VALID_SCHEMAS

            command_center = client.get("/")
            assert command_center.status_code == 200
            assert "Connector Runtime" in command_center.get_data(as_text=True)

        print("v7.5.9 connector runtime smoke passed")


if __name__ == "__main__":
    main()

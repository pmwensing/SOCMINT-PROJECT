from __future__ import annotations

import os
import tempfile
from pathlib import Path

from socmint import database as db
from socmint.command_center_routes import register_command_center_routes
from socmint.connector_runtime import connector_runtime_health
from socmint.connector_runtime import install_hint
from socmint.connector_runtime_routes import register_connector_runtime_routes
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow
from socmint.full_report_history import register_full_report_history_routes
from socmint.full_report_retention import register_full_report_retention_routes

EXPECTED = {"sherlock", "maigret", "socialscan", "holehe", "h8mail", "phoneinfoga", "archivebox"}
VALID_SCHEMAS = {"socmint.connector_runtime.v7_6_0", "socmint.connector_runtime.v7_6_1"}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="socmint-v760-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        installer = Path("scripts/install_connector_runtime_v7_6_0.sh")
        compose = Path("docker-compose.scanners.yml")
        assert installer.exists()
        assert compose.exists()
        installer_text = installer.read_text()
        assert "maigret" in installer_text
        assert "sherlock-project" in installer_text
        assert "socialscan" in installer_text
        assert "holehe" in installer_text
        assert "h8mail" in installer_text
        assert "phoneinfoga_INSTALL.txt" in installer_text
        assert "archivebox_INSTALL.txt" in installer_text

        for name in EXPECTED:
            hint = install_hint(name)
            assert hint["install_command"]
            assert hint["check_command"]
            assert hint["runtime_note"]

        health = connector_runtime_health()
        assert health["schema"] in VALID_SCHEMAS
        assert health["installer"]["script"] == "scripts/install_connector_runtime_v7_6_0.sh"
        assert health["installer"]["scanner_compose"] == "docker-compose.scanners.yml"
        names = {item["name"] for item in health["connectors"]}
        assert EXPECTED.issubset(names)
        for item in health["connectors"]:
            assert item["install_command"]
            assert item["check_command"]
            assert item["install_hint"]["runtime_note"]

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="connector-installer-smoke")
        register_full_report_aliases(app)
        register_full_report_browser_flow(app)
        register_full_report_history_routes(app)
        register_full_report_retention_routes(app)
        register_command_center_routes(app)
        register_connector_runtime_routes(app)

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "connector-installer-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "connector-installer-csrf"

            page = client.get("/connectors/runtime")
            assert page.status_code == 200
            text = page.get_data(as_text=True)
            assert "Install/activate connector toolchain" in text or "Missing connector repair" in text
            assert "bash scripts/install_connector_runtime_v7_6_0.sh" in text
            assert "docker-compose.scanners.yml" in text
            assert "sherlock-project" in text
            assert "PhoneInfoga" in text or "phoneinfoga" in text

            api = client.get("/api/v1/connectors/runtime")
            assert api.status_code == 200
            assert api.get_json()["schema"] in VALID_SCHEMAS

        print("v7.6.0 connector runtime installer smoke passed")


if __name__ == "__main__":
    main()

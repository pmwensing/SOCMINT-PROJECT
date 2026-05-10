from __future__ import annotations

import os
import subprocess
import tempfile

from socmint import database as db
from socmint.connector_runtime import connector_runtime_health
from socmint.connector_runtime import native_dependency_status
from socmint.connector_runtime_routes import register_connector_runtime_routes
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow
from socmint.full_report_history import register_full_report_history_routes
from socmint.full_report_retention import register_full_report_retention_routes


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="socmint-v761-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        native = native_dependency_status()
        assert "install_command" in native
        assert "pkg-config" in native["install_command"]
        assert "libcairo2-dev" in native["install_command"]
        assert any(item["name"] == "cairo" for item in native["items"])

        payload = connector_runtime_health()
        assert payload["schema"] == "socmint.connector_runtime.v7_6_1"
        assert "native_dependencies" in payload
        assert payload["native_dependencies"]["install_command"]
        for item in payload["connectors"]:
            assert item["install_command"]
            assert item["check_command"]
            if item["name"] in {"maigret", "archivebox"}:
                assert item["install_hint"].get("native_dependency_hint")
            if item["name"] == "phoneinfoga":
                assert item["install_hint"].get("manual_steps")

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="connector-repair-smoke")
        register_full_report_aliases(app)
        register_full_report_browser_flow(app)
        register_full_report_history_routes(app)
        register_full_report_retention_routes(app)
        register_connector_runtime_routes(app)

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "connector-repair-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "connector-repair-csrf"

            page = client.get("/connectors/runtime")
            assert page.status_code == 200
            text = page.get_data(as_text=True)
            assert "Missing connector repair" in text or payload["summary"]["missing"] == 0
            assert "Native dependency diagnostics" in text or payload["native_dependencies"]["ready"]
            assert "pkg-config cmake build-essential" in text or payload["native_dependencies"]["ready"]
            assert "PhoneInfoga" in text or "phoneinfoga" in text

        result = subprocess.run(
            ["python3", "-m", "socmint.connector_runtime_health_cli"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={**os.environ, "PYTHONPATH": os.getcwd() + "/src"},
        )
        assert result.returncode == 0
        assert "SOCMINT Connector Runtime Health" in result.stdout
        assert "Summary:" in result.stdout
        assert "Repair quick-start" in result.stdout or "MISSING" not in result.stdout

        result_json = subprocess.run(
            ["python3", "-m", "socmint.connector_runtime_health_cli", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={**os.environ, "PYTHONPATH": os.getcwd() + "/src"},
        )
        assert result_json.returncode == 0
        assert "socmint.connector_runtime.v7_6_1" in result_json.stdout

        print("v7.6.1 connector runtime repair smoke passed")


if __name__ == "__main__":
    main()

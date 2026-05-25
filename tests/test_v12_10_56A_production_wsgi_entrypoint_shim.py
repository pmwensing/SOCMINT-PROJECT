from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_wsgi_entrypoint_exposes_guard_routes():
    from src.socmint.wsgi import app

    client = app.test_client()

    required = {
        "/api/version",
        "/api/schema/status",
        "/api/schema/upgrade-guard",
        "/api/release/archive-integrity",
        "/api/schema/rollback/0018",
    }

    routes = {str(rule) for rule in app.url_map.iter_rules()}
    assert required.issubset(routes)

    assert client.get("/api/version").get_json()["version"] == "12.10.54"
    assert client.get("/api/schema/status").get_json()["real_db_upgrade_default_blocked"] is True
    assert client.get("/api/schema/upgrade-guard").get_json()["allowed"] is False


def test_production_entrypoint_status_now_selects_wsgi_spec():
    from src.socmint.v12_10_56_production_entrypoint import production_entrypoint_status

    result = production_entrypoint_status()

    assert result["status"] == "GO"
    assert result["verification_mode"] == "production_entrypoint"
    assert result["selected_spec"] in {
        "src.socmint.wsgi:app",
        "src.socmint.wsgi:application",
        "src.socmint.wsgi:create_app",
    }
    assert result["production_db_touched"] is False
    assert result["real_config_upgrade_run"] is False


def test_production_entrypoint_report_passes_after_wsgi_shim():
    result = subprocess.run(
        [sys.executable, "scripts/production_entrypoint_route_lock_report_v12_10_56.py"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/v12_10_56/PRODUCTION_ENTRYPOINT_ROUTE_LOCK_V12_10_56.json")
    data = json.loads(report.read_text())

    assert data["status"] == "GO"
    assert data["selected_spec"] in {
        "src.socmint.wsgi:app",
        "src.socmint.wsgi:application",
        "src.socmint.wsgi:create_app",
    }
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False

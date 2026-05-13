from pathlib import Path

from src.socmint.production_installer import installer_file_status
from src.socmint.production_installer import installer_plan
from src.socmint.production_installer import installer_readiness_report
from src.socmint.production_installer import installer_readiness_summary
from src.socmint.wsgi import app


def test_v10_2_installer_plan_shape():
    plan = installer_plan()

    assert plan["schema"] == "socmint.production_installer.v10_2_0"
    assert "run database migrations" in plan["steps"]
    assert "backup restore smoke result" in plan["outputs"]


def test_v10_2_installer_files_present_in_repo():
    status = installer_file_status()

    assert status["schema"] == "socmint.production_installer.v10_2_0"
    assert status["status"] == "ready"
    assert status["missing"] == []
    assert Path("scripts/install_production.sh").exists()
    assert Path(".env.production.example").exists()


def test_v10_2_installer_readiness_summary_ready():
    summary = installer_readiness_summary()

    assert summary["schema"] == "socmint.production_installer.v10_2_0"
    assert summary["status"] == "ready"
    assert summary["passed_checks"] == summary["total_checks"]


def test_v10_2_installer_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/admin/installer/plan" in routes
    assert "/api/v1/admin/installer/readiness" in routes
    assert "/api/v1/admin/installer/readiness/summary" in routes


def test_v10_2_full_report_ready():
    report = installer_readiness_report()

    assert report["schema"] == "socmint.production_installer.v10_2_0"
    assert report["status"] == "ready"
    assert report["checks"]["installer_files"] is True

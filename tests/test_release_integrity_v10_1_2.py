from pathlib import Path

import socmint

from src.socmint.release_integrity import EXPECTED_VERSION
from src.socmint.release_integrity import release_integrity_report
from src.socmint.release_integrity import release_integrity_summary
from src.socmint.release_integrity import release_note_report
from src.socmint.release_integrity import route_registration_report
from src.socmint.release_integrity import version_integrity_report
from src.socmint.wsgi import app


def test_v10_1_2_version_integrity():
    report = version_integrity_report()

    assert EXPECTED_VERSION == socmint.__version__
    assert report["schema"] == "socmint.release_integrity.v10_1_2"
    assert report["status"] == "pass"
    assert report["versions"]["package"] == EXPECTED_VERSION
    assert report["versions"]["pyproject"] == EXPECTED_VERSION


def test_v10_1_2_required_routes_are_registered():
    report = route_registration_report(app)

    assert report["schema"] == "socmint.release_integrity.v10_1_2"
    assert report["status"] == "pass"
    assert report["missing"] == []
    assert "/api/v1/admin/certification/summary" in report["registered_required_routes"]
    assert "/api/v1/admin/operator-smoke/summary" in report["registered_required_routes"]


def test_v10_1_2_release_notes_exist():
    report = release_note_report()

    assert report["schema"] == "socmint.release_integrity.v10_1_2"
    assert report["status"] == "pass"
    assert report["missing"] == []
    assert Path("release/V10_1_2_RELEASE_INTEGRITY.md").exists()


def test_v10_1_2_full_integrity_report_passes():
    report = release_integrity_report(app)
    summary = release_integrity_summary(app)

    assert report["schema"] == "socmint.release_integrity.v10_1_2"
    assert report["status"] == "pass"
    assert summary["status"] == "pass"
    assert summary["passed_checks"] == summary["total_checks"]

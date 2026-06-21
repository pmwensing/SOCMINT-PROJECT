from pathlib import Path
import zipfile

from socmint.dashboard import create_app
from socmint.report_export_center import (
    build_export_zip_bundle,
    export_center_payload,
    list_export_bundles,
    safe_export_bundle_path,
)


def test_build_export_zip_bundle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = build_export_zip_bundle(
        subject_id=None,
        gate_mode="approved_and_uncertain",
        title="Test ZIP bundle",
    )

    assert result["schema"] == "socmint.export_zip_bundle.v7_3_2"
    bundle_path = Path(result["bundle"]["path"])
    assert bundle_path.exists()
    assert bundle_path.suffix == ".zip"

    with zipfile.ZipFile(bundle_path) as zf:
        names = set(zf.namelist())
        assert "README.txt" in names
        assert any(name.endswith("-MANIFEST.json") for name in names)
        assert any(name.endswith("-SUMMARY.md") for name in names)
        assert any(name.endswith("-AUDIT-SNAPSHOT.json") for name in names)


def test_bundle_listing_and_safe_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = build_export_zip_bundle(gate_mode="approved_and_uncertain")
    bundles = list_export_bundles()

    assert bundles
    assert bundles[0]["name"].endswith(".zip")

    safe_path = safe_export_bundle_path(Path(result["bundle"]["path"]).name)
    assert safe_path.exists()


def test_export_center_payload_has_bundles(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    build_export_zip_bundle(gate_mode="approved_and_uncertain")
    payload = export_center_payload()

    assert payload["schema"] == "socmint.report_export_center.v7_3_1"
    assert payload["bundles"]


def test_zip_bundle_routes_registered():
    app = create_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/reports/export-center/zip" in rules
    assert "/reports/export-center/zip/run" in rules
    assert "/reports/export-center/bundles/<path:name>/download" in rules


from pathlib import Path

from socmint.dashboard import create_app
from socmint.report_export_center import (
    build_review_gated_manifest,
    export_center_payload,
    item_allowed,
)


def test_gate_policy():
    assert item_allowed("approved", "approved_only") is True
    assert item_allowed("uncertain", "approved_only") is False
    assert item_allowed("uncertain", "approved_and_uncertain") is True
    assert item_allowed("rejected", "exclude_rejected") is False


def test_export_center_payload_shape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    payload = export_center_payload()

    assert payload["schema"] == "socmint.report_export_center.v7_3_1"
    assert "approved_and_uncertain" in payload["gate_modes"]
    assert "exports" in payload


def test_review_gated_manifest_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    manifest = build_review_gated_manifest(
        subject_id=None,
        gate_mode="approved_and_uncertain",
        title="Test gated export",
    )

    assert manifest["schema"] == "socmint.review_gated_export_manifest.v7_3"
    assert manifest["gate_mode"] == "approved_and_uncertain"
    assert Path(manifest["manifest_path"]).exists()
    assert Path(manifest["summary_path"]).exists()


def test_export_center_routes_registered():
    app = create_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/reports/export-center" in rules
    assert "/api/v1/reports/export-center" in rules
    assert "/api/v1/reports/export-center/review-gated" in rules
    assert "/reports/export-center/review-gated/run" in rules

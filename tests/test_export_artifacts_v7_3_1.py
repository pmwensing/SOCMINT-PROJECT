from pathlib import Path

import pytest

from socmint.dashboard import create_app
from socmint.report_export_center import (
    build_review_gated_manifest,
    export_center_payload,
    list_export_artifacts,
    load_manifest_view,
    safe_export_artifact_path,
)


def test_artifact_listing_and_manifest_view(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    manifest = build_review_gated_manifest(gate_mode="approved_and_uncertain")
    artifacts = list_export_artifacts()

    assert artifacts
    names = {item["name"] for item in artifacts}
    assert Path(manifest["manifest_path"]).name in names

    view = load_manifest_view(Path(manifest["manifest_path"]).name)

    assert view["schema"] == "socmint.export_artifact_view.v7_3_1"
    assert view["parsed"]["schema"] == "socmint.review_gated_export_manifest.v7_3"


def test_safe_export_artifact_path_blocks_escape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    build_review_gated_manifest(gate_mode="approved_and_uncertain")

    with pytest.raises(ValueError):
        safe_export_artifact_path("../outside.json")


def test_export_center_payload_has_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    build_review_gated_manifest(gate_mode="approved_and_uncertain")
    payload = export_center_payload()

    assert payload["schema"] == "socmint.report_export_center.v7_3_1"
    assert payload["artifacts"]


def test_manifest_viewer_routes_registered():
    app = create_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/reports/export-center/manifests/<path:name>" in rules
    assert "/api/v1/reports/export-center/artifacts/<path:name>" in rules
    assert "/reports/export-center/artifacts/<path:name>/download" in rules

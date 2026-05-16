from __future__ import annotations

import io
import json
import zipfile
from copy import deepcopy

from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle
from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle_files
from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle_from_verification_report
from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_zip
from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import safe_bundle_name
from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import sha256_bytes
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index

REQUIRED_FILES = {
    "README.md",
    "master_delivery_index.json",
    "master_delivery_index.md",
    "master_delivery_index_summary.json",
    "manifest.json",
}


def verification_report():
    return {
        "schema": "socmint.v7_5_12.dossier_finalization_closeout_export_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "required_files": ["README.md", "closeout_report.json"],
        "present_files": ["README.md", "closeout_report.json"],
        "missing_files": [],
        "unexpected_files": [],
        "manifest": {"file_count": 5, "files": []},
        "closeout_action": "closeout_ready",
        "verification_status": "verified",
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def delivery_index():
    return build_master_delivery_index(verification_report(), operator="analyst", notes="Ready.")


def test_builds_bundle_from_deliver_ready_index():
    bundle = build_master_delivery_export_bundle(delivery_index(), bundle_name="Master Delivery")

    assert bundle["schema"] == "socmint.v7_5_14.dossier_finalization_master_delivery_export_bundle"
    assert bundle["approved_line"] == "v7.5.14"
    assert bundle["bundle_name"] == "master-delivery"
    assert bundle["delivery_action"] == "deliver_ready"
    assert bundle["verification_status"] == "verified"
    assert bundle["file_count"] == 5


def test_required_files_are_present_exactly():
    bundle = build_master_delivery_export_bundle(delivery_index())
    files = build_master_delivery_export_bundle_files(bundle)

    assert set(files) == REQUIRED_FILES


def test_manifest_has_five_rows_and_correct_file_count():
    bundle = build_master_delivery_export_bundle(delivery_index())

    assert bundle["manifest"]["schema"] == "socmint.v7_5_14.dossier_finalization_master_delivery_export_manifest"
    assert bundle["manifest"]["file_count"] == 5
    assert len(bundle["manifest"]["files"]) == 5
    assert {row["path"] for row in bundle["manifest"]["files"]} == REQUIRED_FILES


def test_manifest_hashes_and_sizes_match_payload_file_bytes():
    bundle = build_master_delivery_export_bundle(delivery_index())
    files = build_master_delivery_export_bundle_files(bundle)

    for row in bundle["manifest"]["files"]:
        path = row["path"]
        if path == "manifest.json":
            assert row["self_reference"] is True
            assert row["size_bytes"] == 0
            assert row["sha256"] == ""
            continue
        assert row["size_bytes"] == len(files[path])
        assert row["sha256"] == sha256_bytes(files[path])


def test_zip_contains_required_files_exactly():
    bundle = build_master_delivery_export_bundle(delivery_index())
    zip_bytes = build_master_delivery_export_zip(bundle)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES


def test_safe_bundle_name_normalizes_unsafe_names():
    assert safe_bundle_name(" My Unsafe Bundle!!! ") == "my-unsafe-bundle"
    assert safe_bundle_name("../../") == "master-delivery-package"
    assert safe_bundle_name(None) == "master-delivery-package"


def test_readme_contains_delivery_action_and_verification_status():
    bundle = build_master_delivery_export_bundle(delivery_index(), bundle_name="Delivery")
    readme = build_master_delivery_export_bundle_files(bundle)["README.md"].decode("utf-8")

    assert "# SOCMINT v7.5.14 Master Delivery Package Export Bundle" in readme
    assert "Bundle name: delivery" in readme
    assert "Delivery action: deliver_ready" in readme
    assert "Verification status: verified" in readme
    assert "Files included: 5" in readme


def test_markdown_file_comes_from_v7513_renderer():
    bundle = build_master_delivery_export_bundle(delivery_index())
    markdown = build_master_delivery_export_bundle_files(bundle)["master_delivery_index.md"].decode("utf-8")

    assert "# SOCMINT v7.5.13 Master Dossier Delivery Index" in markdown
    assert "Delivery action: DELIVER_READY" in markdown


def test_summary_file_matches_index_summary():
    index = delivery_index()
    bundle = build_master_delivery_export_bundle(index)
    summary = json.loads(build_master_delivery_export_bundle_files(bundle)["master_delivery_index_summary.json"])

    assert summary == index["summary"]


def test_builds_bundle_from_verification_report_wrapper():
    bundle = build_master_delivery_export_bundle_from_verification_report(
        verification_report(), operator="analyst", notes="Ready.", bundle_name="Wrapped"
    )

    assert bundle["bundle_name"] == "wrapped"
    assert bundle["delivery_action"] == "deliver_ready"
    assert bundle["index"]["operator"] == "analyst"


def test_input_index_is_not_mutated():
    index = delivery_index()
    original = deepcopy(index)

    build_master_delivery_export_bundle(index)

    assert index == original

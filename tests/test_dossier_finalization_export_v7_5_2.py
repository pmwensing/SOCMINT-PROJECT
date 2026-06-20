from __future__ import annotations

import io
import json
import zipfile
from copy import deepcopy

from socmint.dossier_finalization_export_v7_5_2 import build_finalization_export_files
from socmint.dossier_finalization_export_v7_5_2 import build_finalization_export_packet
from socmint.dossier_finalization_export_v7_5_2 import build_finalization_export_zip
from socmint.dossier_finalization_export_v7_5_2 import finalization_export_manifest
from socmint.dossier_finalization_export_v7_5_2 import safe_package_name

REQUIRED_FILES = {
    "README.md",
    "finalization_packet.json",
    "finalization_packet.md",
    "finalization_summary.json",
    "manifest.json",
}


def base_payload():
    return {
        "quality_gate": {"status": "pass", "finding_count": 0},
        "export_enforcement": {
            "status": "allowed",
            "allowed": True,
            "final_export_blocked": False,
        },
        "evidence_manifest": {
            "status": "pass",
            "appendix_summary": {
                "missing_ref_count": 0,
                "missing_hash_count": 0,
                "missing_source_count": 0,
            },
        },
        "identity_confidence": {
            "status": "pass",
            "contradiction_count": 0,
            "low_confidence_count": 0,
            "needs_review_count": 0,
        },
        "connector_compliance": {"status": "pass", "finding_count": 0},
        "policy_coverage": {"status": "pass", "finding_count": 0},
    }


def test_builds_export_packet_schema():
    packet = build_finalization_export_packet(base_payload())

    assert packet["schema"] == "socmint.v7_5_2.dossier_finalization_export_packet"
    assert packet["approved_line"] == "v7.5.2"
    assert packet["package_name"] == "socmint-v7.5.2-finalization-export"


def test_includes_v751_finalization_packet_and_summary():
    packet = build_finalization_export_packet(base_payload())

    assert packet["finalization"]["schema"] == "socmint.v7_5_1.dossier_finalization"
    assert packet["summary"]["schema"] == "socmint.v7_5_1.dossier_finalization.summary"
    assert packet["summary"]["decision"] == packet["finalization"]["decision"]


def test_produces_required_files():
    packet = build_finalization_export_packet(base_payload())
    files = build_finalization_export_files(packet)

    assert set(files) == REQUIRED_FILES
    assert b"SOCMINT v7.5.2 Finalization Export Packet" in files["README.md"]
    assert (
        b"SOCMINT v7.5.1 Dossier Finalization Packet" in files["finalization_packet.md"]
    )


def test_manifest_contains_sha256_and_size_for_every_file():
    packet = build_finalization_export_packet(base_payload())
    files = build_finalization_export_files(packet)
    manifest = finalization_export_manifest(files)

    assert manifest["schema"] == "socmint.v7_5_2.dossier_finalization_export_manifest"
    assert manifest["file_count"] == len(files)
    for row in manifest["files"]:
        assert row["path"] in files
        assert row["size_bytes"] == len(files[row["path"]])
        assert len(row["sha256"]) == 64
        assert row["content_type"] in {"application/json", "text/markdown"}


def test_zip_contains_all_required_files():
    packet = build_finalization_export_packet(base_payload())
    zip_bytes = build_finalization_export_zip(packet)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["file_count"] == len(REQUIRED_FILES)


def test_safe_package_name_strips_unsafe_path_characters():
    assert (
        safe_package_name("../Bad Name/With Spaces!!.zip")
        == "bad-name-with-spaces-.zip"
    )
    assert safe_package_name("../../") == "socmint-v7.5.2-finalization-export"


def test_input_dossier_payload_is_not_mutated():
    payload = base_payload()
    original = deepcopy(payload)

    build_finalization_export_packet(payload)

    assert payload == original


def test_blocked_finalization_can_still_produce_review_export_packet():
    payload = base_payload()
    payload["quality_gate"] = {"status": "fail", "finding_count": 1}
    payload["export_enforcement"] = {
        "status": "blocked",
        "allowed": False,
        "final_export_blocked": True,
    }

    packet = build_finalization_export_packet(payload)
    files = build_finalization_export_files(packet)

    assert packet["decision"] == "blocked"
    assert packet["ready"] is False
    assert set(files) == REQUIRED_FILES


def test_ready_finalization_sets_ready_true_and_decision_ready():
    packet = build_finalization_export_packet(base_payload())

    assert packet["ready"] is True
    assert packet["decision"] == "ready"


def test_manifest_file_count_matches_file_list():
    packet = build_finalization_export_packet(base_payload())

    assert packet["manifest"]["file_count"] == len(packet["files"])
    assert packet["manifest"]["files"] == packet["files"]

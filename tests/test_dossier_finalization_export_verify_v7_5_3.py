from __future__ import annotations

import io
import json
import zipfile
from copy import deepcopy

from socmint.dossier_finalization_export_v7_5_2 import build_finalization_export_files
from socmint.dossier_finalization_export_v7_5_2 import build_finalization_export_packet
from socmint.dossier_finalization_export_v7_5_2 import build_finalization_export_zip
from socmint.dossier_finalization_export_v7_5_2 import canonical_json
from socmint.dossier_finalization_export_verify_v7_5_3 import summarize_verification
from socmint.dossier_finalization_export_verify_v7_5_3 import verify_finalization_export_files
from socmint.dossier_finalization_export_verify_v7_5_3 import verify_finalization_export_packet
from socmint.dossier_finalization_export_verify_v7_5_3 import verify_finalization_export_zip


def base_payload():
    return {
        "quality_gate": {"status": "pass", "finding_count": 0},
        "export_enforcement": {"status": "allowed", "allowed": True, "final_export_blocked": False},
        "evidence_manifest": {"status": "pass", "appendix_summary": {"missing_ref_count": 0, "missing_hash_count": 0, "missing_source_count": 0}},
        "identity_confidence": {"status": "pass", "contradiction_count": 0, "low_confidence_count": 0, "needs_review_count": 0},
        "connector_compliance": {"status": "pass", "finding_count": 0},
        "policy_coverage": {"status": "pass", "finding_count": 0},
    }


def ready_packet():
    return build_finalization_export_packet(base_payload())


def ready_files():
    return build_finalization_export_files(ready_packet())


def test_verifies_ready_v752_export_packet_as_verified():
    report = verify_finalization_export_packet(ready_packet())

    assert report["schema"] == "socmint.v7_5_3.dossier_finalization_export_verification"
    assert report["status"] == "verified"
    assert report["verified"] is True
    assert report["failure_count"] == 0
    assert report["warning_count"] == 0


def test_verifies_v752_zip_bytes_as_verified():
    report = verify_finalization_export_zip(build_finalization_export_zip(ready_packet()))

    assert report["status"] == "verified"
    assert report["verified"] is True


def test_fails_when_manifest_json_is_missing():
    files = ready_files()
    files.pop("manifest.json")

    report = verify_finalization_export_files(files)

    assert report["status"] == "failed"
    assert any(item["code"] == "missing_required_file" and item["path"] == "manifest.json" for item in report["failures"])


def test_fails_when_required_file_is_missing():
    files = ready_files()
    files.pop("README.md")

    report = verify_finalization_export_files(files)

    assert report["status"] == "failed"
    assert any(item["code"] == "missing_required_file" and item["path"] == "README.md" for item in report["failures"])


def test_fails_when_sha256_does_not_match():
    files = ready_files()
    files["README.md"] = b"tampered\n"

    report = verify_finalization_export_files(files)

    assert report["status"] == "failed"
    assert any(item["code"] == "sha256_mismatch" and item["path"] == "README.md" for item in report["failures"])


def test_fails_when_size_does_not_match():
    files = ready_files()
    manifest = json.loads(files["manifest.json"])
    for row in manifest["files"]:
        if row["path"] == "README.md":
            row["size_bytes"] += 1
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")

    report = verify_finalization_export_files(files)

    assert report["status"] == "failed"
    assert any(item["code"] == "size_mismatch" and item["path"] == "README.md" for item in report["failures"])


def test_fails_when_finalization_and_summary_decisions_differ():
    files = ready_files()
    summary = json.loads(files["finalization_summary.json"])
    summary["decision"] = "blocked"
    files["finalization_summary.json"] = canonical_json(summary).encode("utf-8")
    manifest = json.loads(files["manifest.json"])
    for row in manifest["files"]:
        if row["path"] == "finalization_summary.json":
            row["sha256"] = __import__("hashlib").sha256(files["finalization_summary.json"]).hexdigest()
            row["size_bytes"] = len(files["finalization_summary.json"])
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")

    report = verify_finalization_export_files(files)

    assert report["status"] == "failed"
    assert any(item["code"] == "decision_mismatch" for item in report["failures"])


def test_needs_human_review_when_unexpected_extra_file_exists():
    files = ready_files()
    files["extra.txt"] = b"extra\n"
    manifest = json.loads(files["manifest.json"])
    manifest["files"].append(
        {
            "path": "extra.txt",
            "content_type": "text/plain",
            "size_bytes": len(files["extra.txt"]),
            "sha256": __import__("hashlib").sha256(files["extra.txt"]).hexdigest(),
        }
    )
    manifest["file_count"] = len(files)
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")

    report = verify_finalization_export_files(files)

    assert report["status"] == "needs_human_review"
    assert any(item["code"] == "unexpected_file" for item in report["warnings"])


def test_needs_human_review_when_finalization_decision_is_blocked_but_hashes_match():
    payload = base_payload()
    payload["quality_gate"] = {"status": "fail", "finding_count": 1}
    payload["export_enforcement"] = {"status": "blocked", "allowed": False, "final_export_blocked": True}
    packet = build_finalization_export_packet(payload)

    report = verify_finalization_export_packet(packet)

    assert report["status"] == "needs_human_review"
    assert any(item["code"] == "non_ready_finalization" for item in report["warnings"])


def test_fails_on_path_traversal_zip_entry():
    files = ready_files()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, data in files.items():
            archive.writestr(path, data)
        archive.writestr("../evil.txt", b"nope")

    report = verify_finalization_export_zip(buffer.getvalue())

    assert report["status"] == "failed"
    assert any(item["code"] == "unsafe_zip_path" for item in report["failures"])


def test_summarize_verification_returns_compact_summary():
    report = verify_finalization_export_packet(ready_packet())
    summary = summarize_verification(report)

    assert summary["schema"] == "socmint.v7_5_3.dossier_finalization_export_verification.summary"
    assert summary["status"] == "verified"
    assert summary["verified"] is True
    assert "manifest" not in summary


def test_does_not_mutate_input_file_map():
    files = ready_files()
    original = deepcopy(files)

    verify_finalization_export_files(files)

    assert files == original

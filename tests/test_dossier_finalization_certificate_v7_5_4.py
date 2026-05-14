from __future__ import annotations

from copy import deepcopy

from socmint.dossier_finalization_certificate_v7_5_4 import build_certificate_from_packet
from socmint.dossier_finalization_certificate_v7_5_4 import build_certificate_from_zip_bytes
from socmint.dossier_finalization_certificate_v7_5_4 import build_verification_certificate
from socmint.dossier_finalization_certificate_v7_5_4 import certificate_digest
from socmint.dossier_finalization_certificate_v7_5_4 import render_certificate_markdown
from socmint.dossier_finalization_certificate_v7_5_4 import summarize_certificate
from socmint.dossier_finalization_export_v7_5_2 import build_finalization_export_packet
from socmint.dossier_finalization_export_v7_5_2 import build_finalization_export_zip


def base_payload():
    return {
        "quality_gate": {"status": "pass", "finding_count": 0},
        "export_enforcement": {"status": "allowed", "allowed": True, "final_export_blocked": False},
        "evidence_manifest": {"status": "pass", "appendix_summary": {"missing_ref_count": 0, "missing_hash_count": 0, "missing_source_count": 0}},
        "identity_confidence": {"status": "pass", "contradiction_count": 0, "low_confidence_count": 0, "needs_review_count": 0},
        "connector_compliance": {"status": "pass", "finding_count": 0},
        "policy_coverage": {"status": "pass", "finding_count": 0},
    }


def verified_report():
    return {
        "schema": "socmint.v7_5_3.dossier_finalization_export_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "required_files": ["manifest.json"],
        "present_files": ["manifest.json"],
        "missing_files": [],
        "unexpected_files": [],
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def review_report():
    report = verified_report()
    report.update({"status": "needs_human_review", "verified": False, "warning_count": 1})
    report["warnings"] = [
        {
            "severity": "warn",
            "code": "non_ready_finalization",
            "path": "finalization_packet.json",
            "detail": "Finalization packet is structurally intact but not ready.",
            "action": "Complete human review before archiving or disclosure.",
        }
    ]
    return report


def failed_report():
    report = verified_report()
    report.update({"status": "failed", "verified": False, "failure_count": 1})
    report["failures"] = [
        {
            "severity": "fail",
            "code": "sha256_mismatch",
            "path": "README.md",
            "detail": "Manifest SHA-256 does not match file bytes.",
            "action": "Do not archive or disclose this packet; regenerate the export.",
        }
    ]
    return report


def test_builds_valid_certificate_from_verified_report():
    cert = build_verification_certificate(verified_report(), packet_name="packet-a", reviewer="analyst")

    assert cert["schema"] == "socmint.v7_5_4.dossier_finalization_verification_certificate"
    assert cert["status"] == "valid"
    assert cert["valid"] is True
    assert cert["verification_status"] == "verified"
    assert cert["reviewer"] == "analyst"


def test_builds_needs_review_certificate_from_review_report():
    cert = build_verification_certificate(review_report())

    assert cert["status"] == "needs_human_review"
    assert cert["valid"] is False
    assert cert["warning_count"] == 1


def test_builds_failed_certificate_from_failed_report():
    cert = build_verification_certificate(failed_report())

    assert cert["status"] == "failed"
    assert cert["valid"] is False
    assert cert["failure_count"] == 1


def test_preserves_verification_failures_and_warnings_as_findings():
    cert = build_verification_certificate(failed_report())

    assert cert["findings"]
    assert cert["findings"][0]["code"] == "sha256_mismatch"


def test_certificate_summary_is_compact():
    cert = build_verification_certificate(verified_report(), packet_name="packet-a")
    summary = summarize_certificate(cert)

    assert summary["schema"] == "socmint.v7_5_4.dossier_finalization_verification_certificate.summary"
    assert summary["status"] == "valid"
    assert summary["packet_name"] == "packet-a"
    assert "findings" not in summary
    assert "verification_summary" not in summary


def test_markdown_includes_required_headings():
    markdown = render_certificate_markdown(build_verification_certificate(verified_report()))

    assert "# SOCMINT v7.5.4 Finalization Verification Certificate" in markdown
    assert "Status: VALID" in markdown
    assert "## Packet" in markdown
    assert "## Verification Summary" in markdown
    assert "## Findings" in markdown
    assert "## Certificate Digest" in markdown
    assert "## Notes" in markdown


def test_markdown_prints_none_for_empty_findings():
    markdown = render_certificate_markdown(build_verification_certificate(verified_report()))

    assert "## Findings" in markdown
    assert "None." in markdown


def test_certificate_digest_is_64_hex_characters():
    cert = build_verification_certificate(verified_report())

    assert len(cert["certificate_sha256"]) == 64
    int(cert["certificate_sha256"], 16)


def test_certificate_digest_changes_when_content_changes():
    cert = build_verification_certificate(verified_report())
    changed = dict(cert)
    changed["notes"] = "changed"

    assert certificate_digest(cert) != certificate_digest(changed)


def test_build_certificate_from_packet_verifies_and_wraps_packet():
    packet = build_finalization_export_packet(base_payload())
    cert = build_certificate_from_packet(packet, packet_name="from-packet")

    assert cert["status"] == "valid"
    assert cert["valid"] is True
    assert cert["packet_name"] == "from-packet"


def test_build_certificate_from_zip_bytes_verifies_and_wraps_zip():
    packet = build_finalization_export_packet(base_payload())
    zip_bytes = build_finalization_export_zip(packet)
    cert = build_certificate_from_zip_bytes(zip_bytes, packet_name="from-zip")

    assert cert["status"] == "valid"
    assert cert["valid"] is True
    assert cert["packet_name"] == "from-zip"


def test_input_verification_report_is_not_mutated():
    report = review_report()
    original = deepcopy(report)

    build_verification_certificate(report)

    assert report == original

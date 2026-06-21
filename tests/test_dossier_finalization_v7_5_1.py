from copy import deepcopy

from socmint.dossier_finalization_v7_5_1 import attach_dossier_finalization
from socmint.dossier_finalization_v7_5_1 import build_dossier_finalization_packet
from socmint.dossier_finalization_v7_5_1 import render_finalization_markdown
from socmint.dossier_finalization_v7_5_1 import summarize_finalization_decision


def base_reports():
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


def packet_with(**overrides):
    payload = base_reports()
    payload.update(overrides)
    return build_dossier_finalization_packet(payload, export_mode="final")


def test_ready_packet_when_all_components_pass():
    packet = packet_with()

    assert packet["schema"] == "socmint.v7_5_1.dossier_finalization"
    assert packet["decision"] == "ready"
    assert packet["ready"] is True
    assert packet["blocking_count"] == 0
    assert packet["warning_count"] == 0
    assert packet["component_status"]["export_enforcement"] == "allow"


def test_blocked_when_quality_gate_fails():
    packet = packet_with(quality_gate={"status": "fail", "finding_count": 1})

    assert packet["decision"] == "blocked"
    assert any(
        item["code"] == "quality_gate_failed" for item in packet["blocking_findings"]
    )


def test_blocked_when_final_export_blocked():
    packet = packet_with(
        export_enforcement={
            "status": "blocked",
            "allowed": False,
            "final_export_blocked": True,
        }
    )

    assert packet["decision"] == "blocked"
    assert any(item["code"] == "export_blocked" for item in packet["blocking_findings"])


def test_blocked_when_evidence_lineage_incomplete():
    packet = packet_with(
        evidence_manifest={
            "status": "pass",
            "appendix_summary": {"missing_hash_count": 1},
        }
    )

    assert packet["decision"] == "blocked"
    assert packet["component_status"]["evidence_manifest"] == "fail"
    assert any(
        item["code"] == "evidence_lineage_incomplete"
        for item in packet["blocking_findings"]
    )


def test_blocked_when_identity_contradictions_exist():
    packet = packet_with(
        identity_confidence={"status": "pass", "contradiction_count": 1}
    )

    assert packet["decision"] == "blocked"
    assert packet["component_status"]["identity_confidence"] == "fail"
    assert any(
        item["code"] == "identity_contradiction" for item in packet["blocking_findings"]
    )


def test_blocked_when_connector_compliance_fails():
    packet = packet_with(connector_compliance={"status": "fail", "finding_count": 1})

    assert packet["decision"] == "blocked"
    assert any(
        item["code"] == "connector_compliance_failed"
        for item in packet["blocking_findings"]
    )


def test_blocked_when_policy_coverage_fails():
    packet = packet_with(policy_coverage={"status": "fail", "finding_count": 1})

    assert packet["decision"] == "blocked"
    assert any(
        item["code"] == "policy_coverage_failed" for item in packet["blocking_findings"]
    )


def test_needs_human_review_when_identity_confidence_warns():
    packet = packet_with(
        identity_confidence={
            "status": "warn",
            "contradiction_count": 0,
            "low_confidence_count": 1,
        }
    )

    assert packet["decision"] == "needs_human_review"
    assert packet["ready"] is False
    assert any(item["code"] == "identity_review_needed" for item in packet["warnings"])


def test_needs_human_review_when_connector_input_missing():
    payload = base_reports()
    payload.pop("connector_compliance")
    packet = build_dossier_finalization_packet(payload, export_mode="final")

    assert packet["decision"] == "needs_human_review"
    assert any(
        item["code"] == "connector_compliance_missing" for item in packet["warnings"]
    )


def test_needs_human_review_when_policy_events_missing():
    payload = base_reports()
    payload.pop("policy_coverage")
    packet = build_dossier_finalization_packet(payload, export_mode="final")

    assert packet["decision"] == "needs_human_review"
    assert any(
        item["code"] == "policy_coverage_review_needed" for item in packet["warnings"]
    )


def test_attach_dossier_finalization_does_not_mutate_original_payload():
    payload = base_reports()
    original = deepcopy(payload)
    enriched = attach_dossier_finalization(payload, export_mode="final")

    assert payload == original
    assert "dossier_finalization" in enriched
    assert "dossier_finalization" not in payload


def test_summarize_finalization_decision_returns_compact_summary():
    packet = packet_with()
    summary = summarize_finalization_decision(packet)

    assert summary["schema"] == "socmint.v7_5_1.dossier_finalization.summary"
    assert summary["decision"] == "ready"
    assert summary["ready"] is True
    assert "component_reports" not in summary


def test_markdown_includes_required_headings():
    markdown = render_finalization_markdown(packet_with())

    assert "# SOCMINT v7.5.1 Dossier Finalization Packet" in markdown
    assert "Decision: READY" in markdown
    assert "## Component Status" in markdown
    assert "## Blocking Findings" in markdown
    assert "## Warnings" in markdown
    assert "## Human Review Checklist" in markdown
    assert "## Recommended Actions" in markdown


def test_markdown_prints_none_for_empty_findings_and_actions():
    markdown = render_finalization_markdown(packet_with())

    assert markdown.count("None.") >= 3

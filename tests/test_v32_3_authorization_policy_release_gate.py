from src.socmint import authorization_policy_release_gate_v32_3 as gate
from src.socmint.dossier_assembly_workspace_v21_0 import _sha


def _valid_package():
    source_binding = {
        "case_id": "case-1",
        "published_revision_id": "published-1",
        "published_revision_sha256": "published-sha-1",
        "published_content_sha256": "content-sha-1",
        "audience_contract_id": "audience-1",
        "audience_contract_sha256": "audience-sha-1",
        "audience_scope_sha256": "scope-sha-1",
        "recipient_inventory_sha256": "recipient-sha-1",
    }
    manifest = {
        "format": "socmint-json",
        "media_type": "application/json",
        "classification": "restricted",
        "audience_name": "Restricted Review Audience",
        "audience_type": "regulatory",
        "dissemination_purpose": "case review",
        "section_count": 1,
        "recipient_count": 1,
        "sections": [
            {
                "section_id": "key_findings",
                "title": "Key Findings",
                "position": 1,
                "section_sha256": "section-sha-1",
            }
        ],
        "recipients": [
            {
                "recipient_id": "recipient-1",
                "display_name": "Review Team",
                "organization": "Example Agency",
                "role": "reviewer",
                "recipient_type": "team",
                "dissemination_purpose": "case review",
                "max_classification": "restricted",
                "allowed_channels": ["secure_portal"],
                "authorization_state": "not_authorized",
                "delivery_endpoint_resolved": False,
            }
        ],
    }
    payload = {
        "publication_label": "Release 1",
        "published_content": {"sections": []},
        "publication_metadata": {"classification": "restricted"},
        "publication_provenance": {"draft_revision_id": "draft-1"},
    }
    integrity = {
        "source_binding_sha256": _sha(source_binding),
        "package_manifest_sha256": _sha(manifest),
        "package_payload_sha256": _sha(payload),
    }
    content = {
        "event_type": "dissemination_package_assembled",
        "case_id": "case-1",
        "package_label": "Restricted Review Package",
        "package_state": "assembled_pending_authorization",
        "reason": "operator request",
        "note": "",
        "published_revision_id": "published-1",
        "published_revision_sha256": "published-sha-1",
        "audience_contract_id": "audience-1",
        "audience_contract_sha256": "audience-sha-1",
        "source_binding": source_binding,
        "package_manifest": manifest,
        "package_payload": payload,
        "integrity": integrity,
        "authorization_state": "not_authorized",
        "authorization_granted": False,
        "delivery_endpoint_resolved": False,
        "delivery_attempt_created": False,
        "transmission_performed": False,
        "published_revision_mutated": False,
        "audience_contract_mutated": False,
        "delivery_history_mutated": False,
        "contact_secret_stored": False,
    }
    return {
        "schema": "socmint.dissemination_package.v32_2",
        "version": "v32.2.0",
        **content,
        "dissemination_package_id": "dissemination-package-1",
        "dissemination_package_sha256": _sha(content),
    }


def test_v32_3_approves_valid_package_without_creating_delivery(monkeypatch):
    package = _valid_package()
    monkeypatch.setattr(gate, "find_dissemination_package", lambda package_id: package)
    monkeypatch.setattr(gate, "authorization_decision_history", lambda: [])
    monkeypatch.setattr(
        gate,
        "_record",
        lambda reviewer, target_value, event, ip_address: {
            **event,
            "reviewer": reviewer,
        },
    )

    result = gate.record_authorization_policy_decision(
        reviewer="admin",
        dissemination_package_id="dissemination-package-1",
        decision="approve",
        reason="policy review complete",
        confirmed=True,
    )

    assert result["status"] == "approved_for_delivery_attempt"
    assert result["authorization_granted"] is True
    assert result["policy_evaluation"]["policy_status"] == "passed"
    assert result["delivery_eligibility"]["eligible"] is True
    assert result["delivery_endpoint_resolved"] is False
    assert result["delivery_attempt_created"] is False
    assert result["transmission_performed"] is False
    assert result["package_mutated"] is False
    assert result["authorization_decision_id"].startswith(
        "authorization-decision-"
    )


def test_v32_3_denial_records_human_decision_without_delivery(monkeypatch):
    package = _valid_package()
    monkeypatch.setattr(gate, "find_dissemination_package", lambda package_id: package)
    monkeypatch.setattr(gate, "authorization_decision_history", lambda: [])
    monkeypatch.setattr(
        gate,
        "_record",
        lambda reviewer, target_value, event, ip_address: event,
    )

    result = gate.record_authorization_policy_decision(
        reviewer="admin",
        dissemination_package_id="dissemination-package-1",
        decision="deny",
        reason="audience scope not approved",
        confirmed=True,
    )

    assert result["status"] == "release_denied"
    assert result["authorization_granted"] is False
    assert result["delivery_eligibility"]["eligible"] is False
    assert result["transmission_performed"] is False


def test_v32_3_blocks_tampered_package(monkeypatch):
    package = _valid_package()
    package["package_manifest"]["classification"] = "public"
    monkeypatch.setattr(gate, "find_dissemination_package", lambda package_id: package)

    result = gate.record_authorization_policy_decision(
        reviewer="admin",
        dissemination_package_id="dissemination-package-1",
        decision="approve",
        reason="policy review complete",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "package_integrity_verification_failed"
    assert result["authorization_granted"] is False


def test_v32_3_requires_explicit_human_confirmation():
    result = gate.record_authorization_policy_decision(
        reviewer="admin",
        dissemination_package_id="dissemination-package-1",
        decision="approve",
        reason="policy review complete",
        confirmed=False,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == (
        "explicit_human_authorization_confirmation_required"
    )

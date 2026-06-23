from src.socmint import dissemination_package_v32_2 as packages


PUBLICATION = {
    "published_revision_id": "published-dossier-revision-1",
    "published_revision_sha256": "published-sha-1",
    "case_id": "case-1",
    "subject_id": 7,
    "revision_state": "published",
    "immutable": True,
    "publication_label": "Release 1",
    "published_content": {
        "sections": [
            {
                "section_id": "key_findings",
                "title": "Key Findings",
                "position": 1,
                "narrative": "Reviewed finding",
            }
        ],
        "section_count": 1,
    },
    "metadata": {"classification": "restricted"},
    "provenance": {"draft_revision_id": "draft-1"},
    "integrity": {"published_content_sha256": "content-sha-1"},
}

AUDIENCE = {
    "audience_contract_id": "audience-contract-1",
    "audience_contract_sha256": "audience-sha-1",
    "audience_scope_sha256": "scope-sha-1",
    "recipient_inventory_sha256": "recipients-sha-1",
    "case_id": "case-1",
    "audience_name": "Restricted Review Audience",
    "audience_type": "regulatory",
    "dissemination_purpose": "case review",
    "classification": "restricted",
    "contract_state": "proposed",
    "authorization_state": "not_authorized",
    "recipient_inventory": {
        "recipient_count": 1,
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
            }
        ],
    },
}


def test_v32_2_assembles_deterministic_package_without_authorization(monkeypatch):
    monkeypatch.setattr(packages, "find_published_revision", lambda revision_id: PUBLICATION)
    monkeypatch.setattr(packages, "find_audience_contract", lambda contract_id: AUDIENCE)
    monkeypatch.setattr(packages, "_active_revision_ids", lambda case_id: {"published-dossier-revision-1"})
    monkeypatch.setattr(packages, "dissemination_package_history", lambda: [])
    monkeypatch.setattr(
        packages,
        "_record",
        lambda actor, target_value, event, ip_address: {**event, "assembled_by": actor},
    )

    result = packages.assemble_dissemination_package(
        actor="admin",
        published_revision_id="published-dossier-revision-1",
        audience_contract_id="audience-contract-1",
        package_label="Restricted Review Package",
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "dissemination_package_assembled"
    assert result["package_state"] == "assembled_pending_authorization"
    assert result["authorization_state"] == "not_authorized"
    assert result["authorization_granted"] is False
    assert result["delivery_endpoint_resolved"] is False
    assert result["delivery_attempt_created"] is False
    assert result["transmission_performed"] is False
    assert result["published_revision_mutated"] is False
    assert result["audience_contract_mutated"] is False
    assert result["contact_secret_stored"] is False
    assert result["package_manifest"]["section_count"] == 1
    assert result["package_manifest"]["recipient_count"] == 1
    assert result["dissemination_package_id"].startswith("dissemination-package-")


def test_v32_2_blocks_case_mismatch(monkeypatch):
    audience = {**AUDIENCE, "case_id": "case-2"}
    monkeypatch.setattr(packages, "find_published_revision", lambda revision_id: PUBLICATION)
    monkeypatch.setattr(packages, "find_audience_contract", lambda contract_id: audience)

    result = packages.assemble_dissemination_package(
        actor="admin",
        published_revision_id="published-dossier-revision-1",
        audience_contract_id="audience-contract-1",
        package_label="Restricted Review Package",
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "publication_audience_case_mismatch"


def test_v32_2_blocks_superseded_publication(monkeypatch):
    monkeypatch.setattr(packages, "find_published_revision", lambda revision_id: PUBLICATION)
    monkeypatch.setattr(packages, "find_audience_contract", lambda contract_id: AUDIENCE)
    monkeypatch.setattr(packages, "_active_revision_ids", lambda case_id: set())

    result = packages.assemble_dissemination_package(
        actor="admin",
        published_revision_id="published-dossier-revision-1",
        audience_contract_id="audience-contract-1",
        package_label="Restricted Review Package",
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "active_published_revision_required"


def test_v32_2_requires_explicit_confirmation():
    result = packages.assemble_dissemination_package(
        actor="admin",
        published_revision_id="published-dossier-revision-1",
        audience_contract_id="audience-contract-1",
        package_label="Restricted Review Package",
        reason="operator request",
        confirmed=False,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "explicit_package_assembly_confirmation_required"

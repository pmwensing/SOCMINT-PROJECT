from __future__ import annotations

from pathlib import Path

from src.socmint import database
from src.socmint import source_registry_v36_1 as registry


def _accepted_artifact(
    *,
    case_id: str = "case-a",
    content_sha256: str = "a" * 64,
    state: str = "accepted",
):
    return {
        "artifact_id": "evidence-artifact-1",
        "artifact_state": state,
        "artifact_event_sha256": "b" * 64,
        "content_sha256": content_sha256,
        "acquisition_sha256": "c" * 64,
        "collection_job_id": "collection-job-1",
        "contract_binding": {
            "case_id": case_id,
            "entity_id": "entity-a",
        },
        "state_history": [],
    }


def _register(monkeypatch, tmp_path, **overrides):
    database.configure_database(f"sqlite:///{tmp_path / 'registry.db'}")
    artifact = overrides.pop("artifact", _accepted_artifact())
    monkeypatch.setattr(registry, "find_artifact", lambda artifact_id: artifact)
    values = {
        "actor": "admin",
        "case_id": "case-a",
        "source_type": "primary_record",
        "publisher_or_operator": "Example Registry",
        "canonical_url": "HTTPS://Example.COM/records/1/",
        "retrieved_url": "https://example.com/records/1?view=current#fragment",
        "published_at": "2026-07-01T10:00:00+00:00",
        "captured_at": "2026-07-20T02:00:00+00:00",
        "jurisdiction": "CA-ON",
        "access_method": "public_web",
        "authentication_required": False,
        "authorization_reference": None,
        "original_or_derived": "original",
        "terms_and_collection_notes": (
            "Public registry record captured within case scope."
        ),
        "content_sha256": "a" * 64,
        "capture_artifact_id": "evidence-artifact-1",
        "adapter_name": "registry-json-adapter",
        "adapter_version": "1.0.0",
        "reason": "Register source origin and capture integrity.",
        "confirmed": True,
    }
    values.update(overrides)
    return registry.register_source(**values)


def test_v36_1_registers_source_against_accepted_artifact(monkeypatch, tmp_path):
    result = _register(monkeypatch, tmp_path)
    assert result["status"] == "source_record_registered"
    assert result["source_id"].startswith("source-record-")
    assert result["capture_integrity_verified"] is True
    assert result["capture"]["canonical_url"] == (
        "https://example.com/records/1"
    )
    assert result["capture"]["retrieved_url"] == (
        "https://example.com/records/1?view=current"
    )
    assert result["capture"]["artifact_binding"]["case_id"] == "case-a"
    assert result["capture"]["artifact_binding"]["content_sha256"] == "a" * 64
    assert result["independence_group_id"] is None
    assert result["independence_assessed"] is False
    assert result["truth_assigned"] is False
    assert result["claim_approved"] is False
    assert result["artifact_mutated"] is False
    assert result["dossier_mutated"] is False

    sources = registry.current_sources()
    assert len(sources) == 1
    assert sources[0]["source_id"] == result["source_id"]
    assert sources[0]["source_reliability_profile"] == []


def test_v36_1_blocks_duplicate_source_record(monkeypatch, tmp_path):
    first = _register(monkeypatch, tmp_path)
    second = registry.register_source(
        actor="admin",
        case_id="case-a",
        source_type="primary_record",
        publisher_or_operator="Example Registry",
        canonical_url="https://example.com/records/1",
        retrieved_url="https://example.com/records/1?view=current",
        published_at="2026-07-01T10:00:00+00:00",
        captured_at="2026-07-20T02:00:00+00:00",
        jurisdiction="CA-ON",
        access_method="public_web",
        authentication_required=False,
        authorization_reference=None,
        original_or_derived="original",
        terms_and_collection_notes=(
            "Public registry record captured within case scope."
        ),
        content_sha256="a" * 64,
        capture_artifact_id="evidence-artifact-1",
        adapter_name="registry-json-adapter",
        adapter_version="1.0.0",
        reason="Duplicate attempt.",
        confirmed=True,
    )
    assert first["status"] == "source_record_registered"
    assert second["status"] == "blocked"
    assert second["blockers"] == [{"key": "source_record_already_exists"}]


def test_v36_1_blocks_unaccepted_case_mismatch_and_hash_mismatch(
    monkeypatch,
    tmp_path,
):
    unaccepted = _register(
        monkeypatch,
        tmp_path,
        artifact=_accepted_artifact(state="registered"),
    )
    assert unaccepted["blockers"] == [
        {"key": "accepted_evidence_artifact_required"}
    ]

    case_mismatch = _register(
        monkeypatch,
        tmp_path,
        artifact=_accepted_artifact(case_id="case-other"),
    )
    assert case_mismatch["blockers"] == [
        {"key": "source_case_artifact_binding_mismatch"}
    ]

    hash_mismatch = _register(
        monkeypatch,
        tmp_path,
        artifact=_accepted_artifact(content_sha256="d" * 64),
    )
    assert hash_mismatch["blockers"] == [
        {"key": "source_content_artifact_hash_mismatch"}
    ]


def test_v36_1_requires_authorization_reference_for_authenticated_access(
    monkeypatch,
    tmp_path,
):
    result = _register(
        monkeypatch,
        tmp_path,
        access_method="authorized_account",
        authentication_required=True,
        authorization_reference=None,
    )
    assert result["status"] == "blocked"
    assert result["blockers"] == [
        {"key": "authenticated_access_authorization_reference_required"}
    ]


def test_v36_1_reliability_is_claim_type_specific_and_append_only(
    monkeypatch,
    tmp_path,
):
    source = _register(monkeypatch, tmp_path)
    common = {
        "actor": "admin",
        "source_id": source["source_id"],
        "components": {
            "authority": 92,
            "directness": 95,
            "authenticity": 90,
            "capture_integrity": 100,
            "temporal_relevance": 80,
        },
        "reasons": ["Official registry for the assessed record type."],
        "limitations": ["Registry does not prove present-day control."],
        "reason": "Assess source for a defined claim type.",
        "confirmed": True,
    }
    ownership = registry.assess_source_reliability(
        claim_type="registered_ownership",
        reliability_band="A",
        **common,
    )
    control = registry.assess_source_reliability(
        claim_type="present_operational_control",
        reliability_band="C",
        **common,
    )
    assert ownership["status"] == "source_reliability_assessed"
    assert control["status"] == "source_reliability_assessed"
    assert ownership["truth_assigned"] is False
    assert ownership["claim_approved"] is False
    assert ownership["reliability_score"] == 91.4

    profiles = registry.current_reliability_profiles(source["source_id"])
    assert [item["claim_type"] for item in profiles] == [
        "present_operational_control",
        "registered_ownership",
    ]
    current = registry.find_source(source["source_id"])
    assert current is not None
    assert current["reliability_assessed"] is True
    assert len(current["source_reliability_profile"]) == 2


def test_v36_1_blocks_incomplete_or_duplicate_reliability_assessment(
    monkeypatch,
    tmp_path,
):
    source = _register(monkeypatch, tmp_path)
    values = {
        "actor": "admin",
        "source_id": source["source_id"],
        "claim_type": "registered_ownership",
        "reliability_band": "A",
        "components": {
            "authority": 92,
            "directness": 95,
            "authenticity": 90,
            "capture_integrity": 100,
            "temporal_relevance": 80,
        },
        "reasons": ["Official registry."],
        "limitations": [],
        "reason": "Assess.",
        "confirmed": True,
    }
    first = registry.assess_source_reliability(**values)
    duplicate = registry.assess_source_reliability(**values)
    incomplete = registry.assess_source_reliability(
        **{
            **values,
            "claim_type": "employment",
            "components": {"authority": 50},
        }
    )
    assert first["status"] == "source_reliability_assessed"
    assert duplicate["blockers"] == [
        {"key": "source_reliability_assessment_already_exists"}
    ]
    assert incomplete["blockers"] == [
        {"key": "source_reliability_component_invalid"}
    ]


def test_v36_1_rejects_url_credentials_and_uses_no_domain_allowlist(
    monkeypatch,
    tmp_path,
):
    result = _register(
        monkeypatch,
        tmp_path,
        canonical_url="https://user:secret@example.com/record",
    )
    assert result["blockers"] == [{"key": "source_url_invalid"}]
    source = (
        Path(__file__).resolve().parents[1]
        / "src/socmint/source_registry_v36_1.py"
    ).read_text(encoding="utf-8")
    assert "DOMAIN_ALLOWLIST" not in source
    assert "automatic_truth" not in source

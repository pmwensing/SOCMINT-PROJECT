from socmint.dossier_quality_v7_5 import evaluate_dossier_quality
from socmint.entity_profile_intelligence import build_entity_profile_intelligence
from socmint.entity_profile_intelligence import entity_profile_intelligence_summary


def test_quality_gate_passes_with_source_evidence_confidence():
    payload = {
        "accounts": [
            {
                "platform": "example",
                "handle": "user1",
                "confidence": 0.91,
                "evidence_refs": ["ev-1"],
            }
        ],
        "evidence_backed_attributes": [
            {
                "name": "location",
                "value": "Kingston",
                "source": "public_profile",
                "confidence": 0.86,
                "evidence_refs": ["ev-2"],
            }
        ],
    }

    result = evaluate_dossier_quality(payload)

    assert result["schema"] == "socmint.v7_5.dossier_quality_gate"
    assert result["status"] == "pass"
    assert result["finding_count"] == 0


def test_quality_gate_fails_missing_context():
    payload = {
        "evidence_backed_attributes": [
            {
                "name": "location",
                "value": "Unknown",
            }
        ]
    }

    result = evaluate_dossier_quality(payload)

    assert result["status"] == "fail"
    assert result["finding_count"] == 1
    assert set(result["findings"][0]["missing"]) == {
        "evidence_refs",
        "source",
        "confidence",
    }


def test_entity_profile_intelligence_attaches_quality_gate():
    subject = {
        "subject_id": "sub-1",
        "case_id": "case-1",
        "display_name": "Subject One",
    }
    evidence = [
        {
            "evidence_id": "ev-1",
            "source": "public_profile",
            "platform": "example",
            "handle": "subjectone",
            "confidence": 0.91,
        },
        {
            "evidence_id": "ev-2",
            "source": "registry",
            "attribute": "location",
            "value": "Kingston",
            "confidence": 0.86,
        },
    ]

    payload = build_entity_profile_intelligence(
        subject, evidence=evidence, analyst_reviewed=True
    )
    summary = entity_profile_intelligence_summary(payload)

    assert payload["quality_gate"]["status"] == "pass"
    assert payload["export_ready"] is True
    assert summary["quality_status"] == "pass"
    assert summary["quality_finding_count"] == 0


def test_entity_profile_intelligence_blocks_unsubstantiated_subject_claims():
    subject = {
        "subject_id": "sub-2",
        "case_id": "case-1",
        "display_name": "Subject Two",
        "attributes": [
            {
                "name": "location",
                "value": "Unbacked",
            }
        ],
    }

    payload = build_entity_profile_intelligence(
        subject, evidence=[], analyst_reviewed=False
    )

    assert payload["quality_gate"]["status"] == "fail"
    assert payload["export_ready"] is False
    assert payload["quality_gate"]["missing_context_counts"]["evidence_refs"] == 1

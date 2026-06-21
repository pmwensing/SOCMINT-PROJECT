from socmint.identity_confidence_v7_5 import attach_identity_confidence
from socmint.identity_confidence_v7_5 import build_identity_confidence_report
from socmint.identity_confidence_v7_5 import confidence_bucket
from socmint.identity_confidence_v7_5 import find_contradictions


def sample_payload():
    return {
        "accounts": [
            {
                "platform": "example",
                "handle": "subjectone",
                "source": "public_profile",
                "confidence": 0.82,
                "evidence_refs": ["ev-1"],
            }
        ],
        "evidence_backed_attributes": [
            {
                "name": "location",
                "value": "Kingston",
                "source": "registry",
                "confidence": 0.86,
                "evidence_refs": ["ev-2"],
            }
        ],
        "relationships": [
            {
                "target": "Org One",
                "relationship": "mentions",
                "source": "public_page",
                "confidence": 0.66,
                "evidence_refs": ["ev-3"],
            }
        ],
    }


def test_confidence_bucket_boundaries():
    assert confidence_bucket(0.95) == "strong"
    assert confidence_bucket(0.75) == "high"
    assert confidence_bucket(0.5) == "medium"
    assert confidence_bucket(0.2) == "low"


def test_identity_confidence_report_builds_explanations():
    report = build_identity_confidence_report(sample_payload())

    assert report["schema"] == "socmint.v7_5.identity_confidence"
    assert report["claim_count"] == 3
    assert report["contradiction_count"] == 0
    assert report["confidence_explanations"]
    assert report["bucket_counts"]


def test_identity_confidence_detects_contradictions():
    payload = sample_payload()
    payload["evidence_backed_attributes"].append(
        {
            "name": "location",
            "value": "Toronto",
            "source": "secondary",
            "confidence": 0.72,
            "evidence_refs": ["ev-4"],
        }
    )

    conflicts = find_contradictions(payload)
    report = build_identity_confidence_report(payload)

    assert len(conflicts) == 1
    assert conflicts[0]["claim"] == "location"
    assert report["status"] == "fail"
    assert report["contradiction_count"] == 1


def test_identity_confidence_marks_low_claims_for_review():
    payload = sample_payload()
    payload["accounts"][0]["confidence"] = 0.1
    report = build_identity_confidence_report(payload)

    assert report["low_confidence_count"] >= 1
    assert report["needs_review_count"] >= 1
    assert report["status"] == "warn"


def test_attach_identity_confidence_adds_report():
    enriched = attach_identity_confidence(sample_payload())

    assert (
        enriched["identity_confidence"]["schema"] == "socmint.v7_5.identity_confidence"
    )
    assert enriched["identity_confidence"]["claim_count"] == 3

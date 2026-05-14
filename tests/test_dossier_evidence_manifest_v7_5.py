from socmint.dossier_evidence_manifest_v7_5 import attach_evidence_appendix
from socmint.dossier_evidence_manifest_v7_5 import build_evidence_appendix
from socmint.dossier_evidence_manifest_v7_5 import build_evidence_manifest
from socmint.dossier_evidence_manifest_v7_5 import evidence_manifest_csv
from socmint.entity_profile_intelligence import build_entity_profile_intelligence


def _subject():
    return {
        "subject_id": "sub-1",
        "case_id": "case-1",
        "display_name": "Subject One",
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-1",
            "label": "Example public profile",
            "source": "public_profile",
            "source_url": "https://example.invalid/profile/subjectone",
            "platform": "example",
            "handle": "subjectone",
            "confidence": 0.91,
            "sha256": "a" * 64,
            "mime_type": "text/html",
            "size_bytes": 1234,
        },
        {
            "evidence_id": "ev-2",
            "label": "Registry observation",
            "source": "registry",
            "attribute": "location",
            "value": "Kingston",
            "confidence": 0.86,
            "sha256": "b" * 64,
            "mime_type": "application/json",
            "size_bytes": 456,
        },
    ]


def test_build_evidence_appendix_links_claims_to_evidence():
    payload = build_entity_profile_intelligence(_subject(), evidence=_evidence(), analyst_reviewed=True)
    appendix = build_evidence_appendix(payload, raw_evidence=_evidence())

    assert appendix["schema"] == "socmint.v7_5.dossier_evidence_appendix"
    assert appendix["entry_count"] == 2
    assert appendix["missing_ref_count"] == 0
    assert appendix["missing_hash_count"] == 0
    assert appendix["missing_source_count"] == 0
    refs = {entry["evidence_id"]: entry for entry in appendix["entries"]}
    assert refs["ev-1"]["claim_refs"]
    assert refs["ev-2"]["claim_refs"]


def test_build_evidence_manifest_has_stable_hash_and_rows():
    payload = build_entity_profile_intelligence(_subject(), evidence=_evidence(), analyst_reviewed=True)
    manifest = build_evidence_manifest(payload, raw_evidence=_evidence())

    assert manifest["schema"] == "socmint.v7_5.dossier_evidence_manifest"
    assert manifest["row_count"] == 2
    assert len(manifest["sha256"]) == 64
    assert manifest["appendix_summary"]["entry_count"] == 2


def test_evidence_manifest_csv_exports_header_and_rows():
    payload = build_entity_profile_intelligence(_subject(), evidence=_evidence(), analyst_reviewed=True)
    manifest = build_evidence_manifest(payload, raw_evidence=_evidence())
    csv_text = evidence_manifest_csv(manifest)

    assert csv_text.startswith("evidence_id,label,source,source_url,artifact_id,sha256")
    assert "ev-1" in csv_text
    assert "ev-2" in csv_text


def test_attach_evidence_appendix_adds_appendix_and_manifest():
    payload = build_entity_profile_intelligence(_subject(), evidence=_evidence(), analyst_reviewed=True)
    enriched = attach_evidence_appendix(payload, raw_evidence=_evidence())

    assert enriched["evidence_appendix"]["entry_count"] == 2
    assert enriched["evidence_manifest"]["row_count"] == 2


def test_appendix_reports_missing_refs_for_unsubstantiated_claims():
    payload = {
        "evidence_backed_attributes": [
            {"name": "location", "value": "Unknown", "source": "manual", "confidence": 0.5}
        ]
    }
    appendix = build_evidence_appendix(payload, raw_evidence=[])

    assert appendix["missing_ref_count"] == 1
    assert appendix["missing_refs"][0]["claim"] == "location"

from src.socmint.dossier_builder_v3 import build_dossier_payload
from src.socmint.dossier_builder_v3 import confidence_score
from src.socmint.dossier_builder_v3 import dossier_builder_capabilities
from src.socmint.dossier_builder_v3 import dossier_builder_summary
from src.socmint.wsgi import app


def _sample_subject():
    return {
        "subject_id": "sub-001",
        "display_name": "Example Subject",
        "aliases": ["example", "subject-one"],
        "case_id": "case-123",
    }


def _sample_evidence():
    return [
        {
            "evidence_id": "ev-1",
            "label": "profile page",
            "source": "public_profile",
            "confidence": 0.9,
            "artifact_id": "art-1",
        },
        {
            "evidence_id": "ev-2",
            "label": "domain record",
            "source": "public_dns",
            "confidence": 0.8,
        },
    ]


def test_v10_3_confidence_score_shape():
    score = confidence_score(_sample_evidence(), analyst_reviewed=True)

    assert score["schema"] == "socmint.dossier_builder.v10_3_0"
    assert 0 <= score["score"] <= 1
    assert score["components"]["direct_evidence"] == 1.0
    assert score["components"]["analyst_review"] == 1.0


def test_v10_3_build_dossier_payload_sections_and_preflight():
    payload = build_dossier_payload(
        _sample_subject(), _sample_evidence(), analyst_reviewed=True
    )

    assert payload["schema"] == "socmint.dossier_builder.v10_3_0"
    assert payload["subject"]["case_id"] == "case-123"
    assert "source_traceability" in payload["sections"]
    assert "export_preflight" in payload["sections"]
    assert payload["export_preflight"]["ready"] is True
    assert len(payload["source_traceability"]) == 2


def test_v10_3_dossier_summary_counts_review_queue():
    payload = build_dossier_payload(
        _sample_subject(), _sample_evidence(), analyst_reviewed=False
    )
    summary = dossier_builder_summary(payload)

    assert summary["schema"] == "socmint.dossier_builder.v10_3_0"
    assert summary["subject_id"] == "sub-001"
    assert summary["case_id"] == "case-123"
    assert summary["evidence_count"] == 2
    assert summary["export_ready"] is False
    assert summary["review_queue_count"] >= 1


def test_v10_3_capabilities_include_required_controls():
    capabilities = dossier_builder_capabilities()

    assert capabilities["schema"] == "socmint.dossier_builder.v10_3_0"
    assert "case-scoped subject" in capabilities["controls"]
    assert "export preflight" in capabilities["controls"]
    assert "json" in capabilities["outputs"]


def test_v10_3_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/capabilities" in routes
    assert "/api/v1/dossier-builder/v3/build" in routes
    assert "/api/v1/dossier-builder/v3/summary" in routes

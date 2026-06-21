from src.socmint.entity_profile_intelligence import build_entity_profile_intelligence
from src.socmint.entity_profile_intelligence import entity_profile_intelligence_markdown
from src.socmint.entity_profile_intelligence import entity_profile_intelligence_summary
from src.socmint.wsgi import app


def _subject():
    return {
        "subject_id": "subject-intel-1020",
        "display_name": "Entity Intel Subject",
        "case_id": "case-intel-1020",
        "aliases": ["EIS"],
        "handles": ["@entityintel"],
        "accounts": [
            {
                "platform": "github",
                "handle": "entityintel",
                "url": "https://example.invalid/entityintel",
                "evidence_refs": ["ev-account-1"],
            }
        ],
        "relationships": [
            {
                "target": "related-org",
                "relationship": "member",
                "evidence_refs": ["ev-rel-1"],
            }
        ],
        "analyst_notes": [{"note": "review identity cluster", "author": "analyst"}],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-account-1",
            "label": "GitHub profile",
            "source": "github",
            "platform": "github",
            "handle": "entityintel",
            "url": "https://example.invalid/entityintel",
            "confidence": 0.96,
            "artifact_id": "art-profile-1",
            "date": "2026-01-01",
            "event": "profile observed",
        },
        {
            "evidence_id": "ev-attr-1",
            "label": "Kingston",
            "source": "registry",
            "attribute": "location",
            "value": "Kingston",
            "confidence": 0.88,
            "artifact_id": "art-registry-1",
        },
        {
            "evidence_id": "ev-attr-2",
            "label": "Toronto",
            "source": "social",
            "attribute": "location",
            "value": "Toronto",
            "confidence": 0.62,
        },
        {
            "evidence_id": "ev-rel-1",
            "label": "relationship mention",
            "source": "public_profile",
            "related_entity": "related-org",
            "relationship": "member",
            "confidence": 0.74,
        },
    ]


def test_v10_20_builds_full_entity_profile_intelligence_sections():
    payload = build_entity_profile_intelligence(
        _subject(), _evidence(), analyst_reviewed=True
    )

    assert payload["schema"] == "socmint.entity_profile_intelligence.v10_20_0"
    assert "identity_summary" in payload["sections"]
    assert "accounts" in payload["sections"]
    assert "evidence_backed_attributes" in payload["sections"]
    assert "timeline" in payload["sections"]
    assert "relationships" in payload["sections"]
    assert "contradictions" in payload["sections"]
    assert payload["identity_summary"]["primary_name"] == "Entity Intel Subject"
    assert "EIS" in payload["identity_summary"]["aliases"]
    assert "@entityintel" in payload["identity_summary"]["handles"]
    assert payload["accounts"][0]["platform"] == "github"
    assert payload["relationships"][0]["target"] == "related-org"


def test_v10_20_detects_contradictions_and_risk():
    payload = build_entity_profile_intelligence(
        _subject(), _evidence(), analyst_reviewed=True
    )

    assert len(payload["contradictions"]) == 1
    contradiction = payload["contradictions"][0]
    assert contradiction["claim"] == "location"
    assert sorted(contradiction["values"]) == ["Kingston", "Toronto"]
    assert payload["risk_scoring"]["contradiction_count"] == 1
    assert payload["risk_scoring"]["risk_level"] in {"low", "medium", "high"}


def test_v10_20_timeline_is_sorted_and_evidence_backed():
    evidence = _evidence() + [
        {
            "evidence_id": "ev-timeline-early",
            "label": "early event",
            "source": "archive",
            "date": "2025-12-01",
            "confidence": 0.9,
        }
    ]
    payload = build_entity_profile_intelligence(
        _subject(), evidence, analyst_reviewed=True
    )

    assert payload["timeline"][0]["date"] == "2025-12-01"
    assert payload["timeline"][1]["date"] == "2026-01-01"
    assert payload["timeline"][0]["evidence_refs"] == ["ev-timeline-early"]


def test_v10_20_summary_counts_core_dossier_sections():
    payload = build_entity_profile_intelligence(
        _subject(), _evidence(), analyst_reviewed=True
    )
    summary = entity_profile_intelligence_summary(payload)

    assert summary["schema"] == "socmint.entity_profile_intelligence.v10_20_0"
    assert summary["subject_id"] == "subject-intel-1020"
    assert summary["case_id"] == "case-intel-1020"
    assert summary["account_count"] >= 1
    assert summary["attribute_count"] == 2
    assert summary["timeline_event_count"] == 1
    assert summary["relationship_count"] >= 1
    assert summary["contradiction_count"] == 1


def test_v10_20_markdown_exports_entity_profile_sections():
    payload = build_entity_profile_intelligence(
        _subject(), _evidence(), analyst_reviewed=True
    )
    markdown = entity_profile_intelligence_markdown(payload)

    assert "# Entity Profile Dossier" in markdown
    assert "## Aliases / Handles" in markdown
    assert "## Accounts" in markdown
    assert "## Evidence-backed Attributes" in markdown
    assert "## Timeline" in markdown
    assert "## Relationships" in markdown
    assert "## Contradictions" in markdown
    assert "Entity Intel Subject" in markdown
    assert "location" in markdown


def test_v10_20_intelligence_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/intelligence/build" in routes
    assert "/api/v1/dossier-builder/v3/intelligence/summary" in routes
    assert "/api/v1/dossier-builder/v3/intelligence/markdown" in routes


def test_v10_20_route_methods_are_post_only():
    routes = {rule.rule: rule.methods for rule in app.url_map.iter_rules()}

    assert "POST" in routes["/api/v1/dossier-builder/v3/intelligence/build"]
    assert "POST" in routes["/api/v1/dossier-builder/v3/intelligence/summary"]
    assert "POST" in routes["/api/v1/dossier-builder/v3/intelligence/markdown"]


def test_v10_20_direct_summary_builds_authenticated_payload_equivalent():
    payload = build_entity_profile_intelligence(
        _subject(), _evidence(), analyst_reviewed=True
    )
    summary = entity_profile_intelligence_summary(payload)

    assert summary["subject_id"] == "subject-intel-1020"
    assert summary["case_id"] == "case-intel-1020"
    assert summary["export_ready"] is True

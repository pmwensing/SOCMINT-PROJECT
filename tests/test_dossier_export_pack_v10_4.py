from src.socmint.dossier_export_pack import build_export_pack
from src.socmint.dossier_export_pack import export_pack_summary
from src.socmint.dossier_export_pack import export_preflight
from src.socmint.dossier_export_pack import render_dossier_html
from src.socmint.dossier_builder_v3 import build_dossier_payload
from src.socmint.wsgi import app


def _subject():
    return {
        "subject_id": "sub-104",
        "display_name": "Export Subject",
        "case_id": "case-104",
        "aliases": ["export-subject"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-104-1",
            "label": "profile artifact",
            "source": "public_profile",
            "confidence": 0.92,
            "artifact_id": "art-104-1",
        },
        {
            "evidence_id": "ev-104-2",
            "label": "registry artifact",
            "source": "public_registry",
            "confidence": 0.88,
            "artifact_id": "art-104-2",
        },
    ]


def test_v10_4_export_preflight_ready_for_reviewed_dossier():
    dossier = build_dossier_payload(_subject(), _evidence(), analyst_reviewed=True)
    preflight = export_preflight(dossier)

    assert preflight["schema"] == "socmint.dossier_export.v10_4_0"
    assert preflight["ready"] is True
    assert preflight["missing"] == []


def test_v10_4_export_pack_contains_json_html_and_manifest_hashes():
    pack = build_export_pack(_subject(), _evidence(), analyst_reviewed=True)

    assert pack["schema"] == "socmint.dossier_export.v10_4_0"
    assert pack["status"] == "ready"
    assert pack["manifest"]["artifact_count"] == 2
    assert set(pack["manifest"]["formats"]) == {"json", "html"}
    assert pack["artifacts"]["json"]["sha256"]
    assert pack["artifacts"]["html"]["sha256"]
    assert "Export Subject" in pack["artifacts"]["html"]["content"]


def test_v10_4_export_summary_shape():
    pack = build_export_pack(_subject(), _evidence(), analyst_reviewed=True)
    summary = export_pack_summary(pack)

    assert summary["schema"] == "socmint.dossier_export.v10_4_0"
    assert summary["ready"] is True
    assert summary["blocker_count"] == 0
    assert summary["blockers"] == []
    assert summary["artifact_count"] == 2
    assert summary["subject_id"] == "sub-104"
    assert summary["case_id"] == "case-104"


def test_v10_4_html_renderer_escapes_subject_content():
    dossier = build_dossier_payload(
        {"subject_id": "sub-x", "display_name": "<script>x</script>", "case_id": "case-x"},
        _evidence(),
        analyst_reviewed=True,
    )
    html = render_dossier_html(dossier)

    assert "<script>x</script>" not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html


def test_v10_4_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/export-pack" in routes
    assert "/api/v1/dossier-builder/v3/export-pack/summary" in routes

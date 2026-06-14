from src.socmint import database
from src.socmint import dossier_release_preview_v22_2 as service


def _export(restricted=False):
    text = "Contains private key material." if restricted else "Approved account attribution."
    return {
        "export_package_id": "dossier-export-1",
        "export_package_sha256": "a" * 64,
        "dossier_content": {
            "sections": [{
                "section_id": "key_findings",
                "title": "Key Findings",
                "position": 1,
                "citation_ready_narrative": text,
                "findings": [{"citation_ready_text": "Finding [C1]"}],
            }]
        },
        "citation_catalog": [{
            "claim_id": "claim-1",
            "artifact_links": [{
                "artifact_id": "artifact-1",
                "path": "evidence/report.pdf",
                "sha256": "b" * 64,
                "media_type": "application/pdf",
            }],
        }],
    }


def _authorization():
    return {
        "authorization_id": "release-auth-1",
        "authorization_sha256": "c" * 64,
        "export_package_id": "dossier-export-1",
        "export_package_sha256": "a" * 64,
        "recipient_id": "recipient-1",
        "delivery_channel": "secure_portal",
    }


def _setup(tmp_path, monkeypatch, restricted=False):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(service, "_latest_export", lambda case_id: _export(restricted))
    monkeypatch.setattr(service, "latest_release_authorization", lambda case_id: _authorization())


def test_v22_2_shows_exact_material_and_classification(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = service.build_release_package_preview("case-alpha")
    assert result["status"] == "ready_for_acknowledgement"
    assert result["release_ready"] is True
    assert result["section_count"] == 1
    assert result["attachment_count"] == 1
    assert result["included_sections"][0]["classification"] == "internal"
    assert result["included_sections"][0]["narrative"] == "Approved account attribution."
    assert result["included_attachments"][0]["attachment_id"] == "artifact-1"
    assert result["operator_acknowledgement_required"] is True
    assert result["transmission_performed"] is False


def test_v22_2_exposes_redaction_blockers_and_records_acknowledgement(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, restricted=True)
    preview = service.build_release_package_preview("case-alpha")
    assert preview["status"] == "review_required"
    assert preview["restricted_section_count"] == 1
    assert "section_redaction_required" in {item["key"] for item in preview["blockers"]}

    blocked = service.acknowledge_release_package_preview(
        "case-alpha", acknowledged=False, operator="operator"
    )
    assert blocked["blockers"][0]["key"] == "operator_acknowledgement_required"

    saved = service.acknowledge_release_package_preview(
        "case-alpha",
        acknowledged=True,
        operator="operator",
        note="Reviewed; redaction remains required.",
    )
    latest = service.latest_release_preview("case-alpha")
    assert saved["status"] == "acknowledged_with_blockers"
    assert saved["operator_acknowledged"] is True
    assert saved["release_ready"] is False
    assert saved["transmission_performed"] is False
    assert saved["source_export_mutated"] is False
    assert latest["preview_record_id"] == saved["preview_record_id"]

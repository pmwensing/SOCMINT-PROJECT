from src.socmint import dossier_release_workspace_v22_0 as service


def _export():
    return {
        "export_package_id": "dossier-export-1",
        "export_package_sha256": "a" * 64,
        "export_record_id": 21,
        "approval_record": {
            "approval_id": "approval-1",
            "approval_record_id": 11,
            "reviewer": "supervisor",
        },
        "integrity": {
            "content_sha256": "1" * 64,
            "dossier_sha256": "2" * 64,
            "citation_catalog_sha256": "3" * 64,
            "source_manifest_sha256": "4" * 64,
            "approval_record_sha256": "5" * 64,
            "quality_review_sha256": "6" * 64,
        },
    }


def _recipients():
    return [
        {
            "recipient_id": "recipient-1",
            "display_name": "Authorized Recipient",
            "organization": "Example Agency",
            "role": "case officer",
            "authorized": True,
            "allowed_channels": ["secure_portal", "encrypted_email"],
        }
    ]


def test_v22_0_loads_export_and_previews_ready_selection(monkeypatch):
    monkeypatch.setattr(service, "_latest_export", lambda case_id: _export())
    result = service.build_dossier_release_workspace(
        "case-alpha",
        selected_recipient_id="recipient-1",
        selected_channel="secure_portal",
        recipients=_recipients(),
    )
    assert result["status"] == "ready_for_delivery_workspace"
    assert result["release_ready"] is True
    assert result["package_ready"] is True
    assert result["selection_ready"] is True
    assert result["approval_state"]["approval_id"] == "approval-1"
    assert len(result["integrity_state"]) == 6
    assert result["transmission_performed"] is False
    assert (
        result["case_delivery_workspace"]["href"] == "/case-delivery?case_id=case-alpha"
    )
    assert result["case_delivery_workspace"]["handoff_context"] == {
        "export_package_id": "dossier-export-1",
        "export_package_sha256": "a" * 64,
        "recipient_id": "recipient-1",
        "delivery_channel": "secure_portal",
    }


def test_v22_0_exposes_release_blockers(monkeypatch):
    monkeypatch.setattr(service, "_latest_export", lambda case_id: None)
    missing = service.build_dossier_release_workspace("case-alpha", recipients=[])
    keys = {item["key"] for item in missing["blockers"]}
    assert keys == {
        "generated_v21_export_required",
        "authorized_recipient_catalog_empty",
    }
    assert missing["release_ready"] is False

    monkeypatch.setattr(service, "_latest_export", lambda case_id: _export())
    invalid = service.build_dossier_release_workspace(
        "case-alpha",
        selected_recipient_id="recipient-1",
        selected_channel="managed_download",
        recipients=_recipients(),
    )
    assert invalid["release_ready"] is False
    assert "delivery_channel_not_authorized" in {
        item["key"] for item in invalid["blockers"]
    }
    assert invalid["transmission_performed"] is False

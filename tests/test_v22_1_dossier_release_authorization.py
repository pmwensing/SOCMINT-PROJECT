from src.socmint import database
from src.socmint import dossier_release_authorization_v22_1 as service


def _preview(ready=True):
    return {
        "release_ready": ready,
        "blockers": [] if ready else [{"key": "delivery_channel_not_authorized"}],
        "selected_recipient": {
            "recipient_id": "recipient-1",
            "display_name": "Authorized Recipient",
            "organization": "Example Agency",
            "role": "case officer",
        },
        "export_package": {
            "export_package_id": "dossier-export-1",
            "export_package_sha256": "a" * 64,
            "export_record_id": 21,
        },
    }


def _setup(tmp_path, monkeypatch, ready=True):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(
        service,
        "build_dossier_release_workspace",
        lambda *args, **kwargs: _preview(ready),
    )


def test_v22_1_requires_explicit_confirmation_and_valid_selection(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    unconfirmed = service.authorize_dossier_release(
        "case-alpha",
        recipient_id="recipient-1",
        delivery_channel="secure_portal",
        confirmed=False,
        authorizer="operator",
    )
    assert unconfirmed["status"] == "blocked"
    assert unconfirmed["blockers"][0]["key"] == "explicit_operator_confirmation_required"

    monkeypatch.setattr(
        service,
        "build_dossier_release_workspace",
        lambda *args, **kwargs: _preview(False),
    )
    invalid = service.authorize_dossier_release(
        "case-alpha",
        recipient_id="recipient-1",
        delivery_channel="managed_download",
        confirmed=True,
        authorizer="operator",
    )
    assert invalid["status"] == "blocked"
    assert invalid["transmission_performed"] is False


def test_v22_1_records_immutable_authorization_for_delivery_workspace(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = service.authorize_dossier_release(
        "case-alpha",
        recipient_id="recipient-1",
        delivery_channel="secure_portal",
        confirmed=True,
        authorizer="operator",
        note="Authorized for secure portal handoff.",
    )
    latest = service.latest_release_authorization("case-alpha")
    assert result["status"] == "authorized"
    assert result["authorizer"] == "operator"
    assert result["operator_confirmed"] is True
    assert result["note"] == "Authorized for secure portal handoff."
    assert result["transmission_performed"] is False
    assert result["source_export_mutated"] is False
    assert result["case_delivery_authorization"]["authorized"] is True
    assert result["case_delivery_authorization"]["recipient_id"] == "recipient-1"
    assert result["case_delivery_authorization"]["delivery_channel"] == "secure_portal"
    assert latest["authorization_record_id"] == result["authorization_record_id"]

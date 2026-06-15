from src.socmint import database
from src.socmint import dossier_secure_distribution_v22_3 as service


def _authorization():
    return {
        "authorization_id": "release-auth-1",
        "authorization_sha256": "a" * 64,
        "export_package_id": "dossier-export-1",
        "export_package_sha256": "b" * 64,
        "recipient_id": "recipient-1",
        "delivery_channel": "secure_portal",
        "case_delivery_authorization": {"authorized": True},
    }


def _preview(ready=True):
    return {
        "preview_id": "release-preview-1",
        "preview_sha256": "c" * 64,
        "authorization_id": "release-auth-1",
        "export_package_id": "dossier-export-1",
        "recipient_id": "recipient-1",
        "delivery_channel": "secure_portal",
        "operator_acknowledged": True,
        "release_ready": ready,
        "included_attachments": [{"attachment_id": "artifact-1"}],
    }


def _setup(tmp_path, monkeypatch, preview=None):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(service, "latest_release_authorization", lambda case_id: _authorization())
    monkeypatch.setattr(service, "latest_release_preview", lambda case_id: preview or _preview())


def test_v22_3_requires_final_confirmation_and_ready_preview(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    unconfirmed = service.dispatch_secure_distribution(
        "case-alpha", confirmed=False, operator="operator"
    )
    assert unconfirmed["status"] == "blocked"
    assert unconfirmed["blockers"][0]["key"] == "explicit_final_operator_confirmation_required"
    assert unconfirmed["transport_invoked"] is False

    monkeypatch.setattr(service, "latest_release_preview", lambda case_id: _preview(False))
    blocked = service.dispatch_secure_distribution(
        "case-alpha", confirmed=True, operator="operator"
    )
    assert blocked["status"] == "blocked"
    assert "acknowledged_ready_preview_required" in {
        item["key"] for item in blocked["blockers"]
    }
    assert blocked["transport_invoked"] is False


def test_v22_3_invokes_existing_operations_and_records_result(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    calls = []

    def operations(case_id, payload):
        calls.append((case_id, payload))
        assert payload["execution_envelope_result"]["executable"] is True
        assert payload["events"][0]["type"] == "dispatch_confirmed"
        return {
            "schema": "socmint.case_delivery_operations.v16_0",
            "case_id": case_id,
            "state": "dispatched",
            "dispatchable": True,
            "operation_id": "operation-1",
            "events": payload["events"],
            "blockers": [],
        }

    result = service.dispatch_secure_distribution(
        "case-alpha",
        confirmed=True,
        operator="operator",
        note="Final dispatch confirmed.",
        operations_builder=operations,
    )
    latest = service.latest_secure_distribution("case-alpha")
    assert len(calls) == 1
    assert result["status"] == "dispatch_recorded"
    assert result["dispatch_result"] == "accepted"
    assert result["transport_invoked"] is True
    assert result["transport_engine"] == "existing_case_delivery_operations_v16_0"
    assert result["dispatch_request"]["operator_confirmed"] is True
    assert result["dispatch_request"]["note"] == "Final dispatch confirmed."
    assert result["source_export_mutated"] is False
    assert result["authorization_mutated"] is False
    assert result["preview_mutated"] is False
    assert latest["distribution_record_id"] == result["distribution_record_id"]
    assert latest["status"] == "dispatch_recorded"

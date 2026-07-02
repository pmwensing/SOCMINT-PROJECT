from __future__ import annotations

import json
from pathlib import Path

import pytest
from flask import Blueprint, Flask

from src.socmint import database
from src.socmint.durable_execution_ledger_v35_1 import (
    create_execution,
    execution_snapshot,
    transition_execution,
)
from src.socmint.execution_reconciliation_contract_v35_4 import (
    validate_reconciliation_request,
)
from src.socmint.execution_reconciliation_read_v35_4 import (
    execution_reconciliation_detail,
    list_uncertain_executions,
)
from src.socmint.execution_reconciliation_routes_v35_4 import (
    register_execution_reconciliation_routes_v35_4,
)
from src.socmint.execution_reconciliation_service_v35_4 import (
    reconcile_execution,
)
from src.socmint.governance_execution_result_store_v35_3 import (
    ExecutionResultConflict,
)
from src.socmint.human_confirmation_framework_v34_2 import (
    confirmation_identity,
    record_issued_confirmation,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64


def _setup_uncertain(tmp_path, name="control"):
    database.configure_database(
        f"sqlite:///{tmp_path / f'{name}.db'}",
        create_schema=True,
    )
    service = "recall_retention_lifecycle_v32_6.record_retention_decision"
    contract = {
        "status": "confirmation_required",
        "case_id": f"case-{name}",
        "action": "record_retention_decision",
        "delegate_service": service,
        "eligibility_resolution_sha256": DIGEST_C,
        "targets": {},
        "inputs": {
            "disposition": "retain",
            "policy_id": "policy-1",
            "reason": "retention policy applies",
        },
        "impact_summary": "Confirm retention decision",
    }
    identity = confirmation_identity(contract)
    assert identity is not None
    contract.update(identity)
    issuance = record_issued_confirmation(contract, "admin")
    assert issuance["issued"] is True
    created = create_execution(
        confirmation_sha256=contract["confirmation_sha256"],
        actor="admin",
        case_id=contract["case_id"],
        governance_action=contract["action"],
        delegate_service=service,
    )
    running = transition_execution(
        execution_id=created["execution_id"],
        expected_state="pending",
        expected_version=created["state_version"],
        new_state="running",
        actor="admin",
        reason="authoritative_delegate_invocation_started",
        metadata={
            "confirmation_issue_audit_id": issuance["audit_record_id"],
            "contract_validation_sha256": DIGEST_A,
        },
    )
    uncertain = transition_execution(
        execution_id=created["execution_id"],
        expected_state="running",
        expected_version=running["state_version"],
        new_state="uncertain",
        actor="admin",
        reason="delegate_result_atomic_commit_failed",
        metadata={
            "result_reference_sha256": DIGEST_B,
            "authoritative_record_ids": {"decision_id": "decision-1"},
            "exception_type": "ConnectionError",
        },
    )
    return {
        "execution_id": created["execution_id"],
        "version": uncertain["state_version"],
        "issuance": issuance,
    }


def _request(setup, reason="Verified from authoritative audit"):
    return {
        "expected_state": "uncertain",
        "expected_version": setup["version"],
        "authoritative_record_ids": {"decision_id": "decision-1"},
        "result_reference_sha256": DIGEST_B,
        "workspace_sha256": DIGEST_C,
        "reconciliation_reason": reason,
        "evidence_references": [
            {
                "reference_type": "audit",
                "reference_id": "audit-91",
                "description": "Authoritative service audit",
            }
        ],
    }


def _app(monkeypatch):
    template_folder = (
        Path(__file__).resolve().parents[1] / "src" / "socmint" / "templates"
    )
    app = Flask(__name__, template_folder=str(template_folder))
    app.secret_key = "v35-4-test-secret"
    dashboard = Blueprint("dashboard", __name__)

    @dashboard.get("/")
    def index():
        return "index"

    @dashboard.get("/login")
    def login():
        return "login"

    @dashboard.get("/logout")
    def logout():
        return "logout"

    app.register_blueprint(dashboard)
    monkeypatch.setattr(
        "src.socmint.execution_reconciliation_routes_v35_4."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    register_execution_reconciliation_routes_v35_4(app)
    return app


def test_v35_4_contract_rejects_overrides_without_value_disclosure():
    payload = _request({"version": 2})
    payload["actor"] = "private-operator-value"
    payload["delegate_service"] = "private-service-value"
    payload["result_reference_sha256"] = "not-a-digest"

    result = validate_reconciliation_request(payload)

    assert result["valid"] is False
    assert {item["key"] for item in result["errors"]} >= {
        "unsupported_field",
        "invalid_sha256",
    }
    rendered = json.dumps(result)
    assert "private-operator-value" not in rendered
    assert "private-service-value" not in rendered


def test_v35_4_read_model_lists_only_uncertain_and_exposes_bindings(tmp_path):
    setup = _setup_uncertain(tmp_path, "read")

    queue = list_uncertain_executions()
    detail = execution_reconciliation_detail(setup["execution_id"])

    assert queue["count"] == queue["total"] == 1
    assert queue["executions"][0]["execution_id"] == setup["execution_id"]
    assert detail is not None
    assert detail["state"] == "uncertain"
    assert detail["invocation_binding"]["confirmation_issue_audit_id"] == setup[
        "issuance"
    ]["audit_record_id"]
    assert detail["invocation_binding"]["contract_validation_sha256"] == DIGEST_A
    assert detail["automatic_retry"] is False
    assert detail["delegate_invocation_available"] is False


def test_v35_4_reconciles_without_delegate_and_persists_evidence(tmp_path):
    setup = _setup_uncertain(tmp_path, "service")
    calls = []

    result = reconcile_execution(
        setup["execution_id"],
        _request(setup),
        actor="admin",
    )

    assert calls == []
    assert result["status"] == "reconciled"
    assert result["delegate_invoked"] is False
    assert result["automatic_retry"] is False
    assert result["reconciliation"]["execution"]["state"] == "reconciled"
    metadata = result["reconciliation"]["execution_audit"]["operator_metadata"]
    assert metadata["reconciliation_reason"] == "Verified from authoritative audit"
    assert metadata["evidence_references"][0]["reference_id"] == "audit-91"
    snapshot = execution_snapshot(setup["execution_id"])
    assert snapshot is not None and snapshot["state"] == "reconciled"


def test_v35_4_identical_replay_and_conflicting_evidence(tmp_path):
    setup = _setup_uncertain(tmp_path, "replay")
    payload = _request(setup)
    first = reconcile_execution(setup["execution_id"], payload, actor="admin")
    second = reconcile_execution(setup["execution_id"], payload, actor="admin")

    assert first["reconciliation"]["created"] is True
    assert second["reconciliation"]["created"] is False
    assert second["reconciliation"]["replay_detected"] is True

    with pytest.raises(ExecutionResultConflict):
        reconcile_execution(
            setup["execution_id"],
            _request(setup, reason="Different evidence interpretation"),
            actor="admin",
        )


def test_v35_4_api_authorization_validation_and_page_controls(monkeypatch, tmp_path):
    setup = _setup_uncertain(tmp_path, "routes")
    app = _app(monkeypatch)
    client = app.test_client()

    assert client.get(
        "/api/v1/dissemination-governance/executions/uncertain"
    ).status_code == 401

    with client.session_transaction() as current_session:
        current_session["user"] = "viewer"
    assert client.get(
        "/api/v1/dissemination-governance/executions/uncertain"
    ).status_code == 403

    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
        current_session["is_admin"] = True

    queue = client.get(
        "/api/v1/dissemination-governance/executions/uncertain"
    )
    assert queue.status_code == 200
    assert queue.get_json()["count"] == 1

    page = client.get("/dissemination-governance/execution-reconciliation")
    source = page.get_data(as_text=True)
    assert page.status_code == 200
    assert 'data-execution-reconciliation="v35.4"' in source
    assert 'data-reconciliation-form="true"' in source
    assert 'name="retry"' not in source
    assert 'name="automatic_retry"' not in source
    assert 'name="delegate_service"' not in source

    invalid = _request(setup)
    invalid["actor"] = "forged-admin"
    response = client.post(
        f"/api/v1/dissemination-governance/executions/{setup['execution_id']}/reconcile",
        json=invalid,
    )
    assert response.status_code == 422
    assert "forged-admin" not in response.get_data(as_text=True)

    reconciled = client.post(
        f"/api/v1/dissemination-governance/executions/{setup['execution_id']}/reconcile",
        json=_request(setup),
    )
    assert reconciled.status_code == 200
    assert reconciled.get_json()["delegate_invoked"] is False
    assert client.get(
        "/api/v1/dissemination-governance/executions/uncertain"
    ).get_json()["count"] == 0

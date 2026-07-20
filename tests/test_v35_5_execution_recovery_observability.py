from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask

from src.socmint import execution_recovery_observability_routes_v35_5 as routes
from src.socmint import execution_recovery_observability_v35_5 as observability


def _payload(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "execution_id": "execution-1",
        "case_id": "case-1",
        "governance_action": "record_retention_decision",
        "delegate_service": "service.method",
        "state": "pending",
        "state_version": 0,
        "last_reason": "confirmed_action_accepted",
        "updated_at": now.isoformat(),
        "ledger_consistent": True,
        "result_envelope_exists": False,
        "invocation_binding": {},
    }
    payload.update(overrides)
    return payload


def test_classification_is_deterministic_and_age_is_diagnostic_only():
    now = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    payload = _payload(updated_at=(now - timedelta(hours=2)).isoformat())
    result = observability.classify_execution(payload, now=now)
    assert result["classification"] == "attention"
    assert result["findings"] == ["pending_threshold_exceeded"]
    assert result["age_bucket"] == "1h_to_24h"
    assert result["age_is_diagnostic_only"] is True
    assert result["automatic_retry"] is False


def test_uncertain_execution_requires_reconciliation_without_retry():
    payload = _payload(
        state="uncertain",
        state_version=2,
        invocation_binding={
            "confirmation_issue_audit_id": 41,
            "contract_validation_sha256": "a" * 64,
        },
    )
    result = observability.classify_execution(payload)
    assert result["classification"] == "reconciliation_pending"
    assert "authoritative_outcome_requires_reconciliation" in result["findings"]
    assert result["delegate_invocation_available"] is False


def test_integrity_alert_precedes_age_attention():
    payload = _payload(
        state="running",
        ledger_consistent=False,
        updated_at=(datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        invocation_binding={},
    )
    result = observability.classify_execution(payload)
    assert result["classification"] == "integrity_alert"
    assert "ledger_state_mismatch" in result["findings"]
    assert "missing_confirmation_issuance_binding" in result["findings"]
    assert "missing_contract_validation_binding" in result["findings"]


def test_summary_counts_independent_read_model_dimensions(monkeypatch):
    now = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(
        observability,
        "_execution_payloads",
        lambda: [
            _payload(execution_id="pending", updated_at=now.isoformat()),
            _payload(
                execution_id="uncertain",
                state="uncertain",
                state_version=2,
                invocation_binding={
                    "confirmation_issue_audit_id": 1,
                    "contract_validation_sha256": "b" * 64,
                },
                updated_at=now.isoformat(),
            ),
        ],
    )
    result = observability.recovery_summary(now=now)
    assert result["total"] == 2
    assert result["by_state"] == {"pending": 1, "uncertain": 1}
    assert result["by_action_family"] == {"record": 2}
    assert result["attention_count"] == 1
    assert result["read_only"] is True


def test_attention_queue_omits_operator_inputs(monkeypatch):
    monkeypatch.setattr(
        observability,
        "_execution_payloads",
        lambda: [
            _payload(
                execution_id="uncertain",
                state="uncertain",
                invocation_binding={
                    "confirmation_issue_audit_id": 1,
                    "contract_validation_sha256": "c" * 64,
                },
                history=[{"metadata": {"secret": "must-not-leak"}}],
            )
        ],
    )
    result = observability.attention_queue()
    assert result["count"] == 1
    assert "history" not in result["executions"][0]
    assert "confirmation_sha256" not in result["executions"][0]
    assert "secret" not in str(result)


def test_routes_are_administrator_only_and_get_only(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v35-5-route-test-secret"
    app.add_url_rule("/login", endpoint="dashboard.login", view_func=lambda: "login")
    routes.register_execution_recovery_observability_routes_v35_5(app)
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(
        routes,
        "recovery_summary",
        lambda: {"status": "ready", "read_only": True},
    )
    monkeypatch.setattr(
        routes,
        "attention_queue",
        lambda limit=200: {"status": "ready", "limit": limit, "executions": []},
    )
    monkeypatch.setattr(
        routes,
        "reconciled_executions",
        lambda limit=200: {"status": "ready", "limit": limit, "executions": []},
    )

    client = app.test_client()
    assert client.get(
        "/api/v1/dissemination-governance/executions/recovery-summary"
    ).status_code == 401
    with client.session_transaction() as state:
        state["user"] = "viewer"
    assert client.get(
        "/api/v1/dissemination-governance/executions/recovery-summary"
    ).status_code == 403
    with client.session_transaction() as state:
        state["user"] = "admin"
    response = client.get(
        "/api/v1/dissemination-governance/executions/recovery-summary"
    )
    assert response.status_code == 200
    assert response.get_json()["read_only"] is True
    assert client.post(
        "/api/v1/dissemination-governance/executions/recovery-summary"
    ).status_code == 405


def test_source_and_template_expose_no_write_controls():
    root = Path(__file__).resolve().parents[1]
    service = (root / "src/socmint/execution_recovery_observability_v35_5.py").read_text()
    route_source = (
        root / "src/socmint/execution_recovery_observability_routes_v35_5.py"
    ).read_text()
    template = (
        root / "src/socmint/templates/execution_recovery_observability_v35_5.html"
    ).read_text()
    forbidden_service_imports = (
        "transition_execution",
        "reconcile_execution",
        "resolve_delegate",
        "commit_execution_result",
    )
    assert all(value not in service for value in forbidden_service_imports)
    assert "@app.post" not in route_source
    assert "<form" not in template
    assert 'data-read-only="true"' in template
    assert 'data-automatic-retry="false"' in template

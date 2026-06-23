from flask import Flask

from src.socmint.governance_action_execution_v34_3_6 import (
    execute_confirmed_action,
    reset_confirmation_consumption_for_tests,
)
from src.socmint.governance_execution_product_review_v34_7 import (
    REQUIRED_ROUTES,
    build_governance_execution_product_review,
)
from src.socmint.human_confirmation_framework_v34_2 import (
    build_confirmation_contract,
)


def _eligible_resolution(case_id="case-1", action="record_retention_decision"):
    return {
        "status": "ready_for_confirmation",
        "resolutions": [
            {
                "case_id": case_id,
                "action": action,
                "eligible": True,
                "delegate_service": (
                    "recall_retention_lifecycle_v32_6."
                    "record_retention_decision"
                ),
                "eligibility_resolution_sha256": "eligibility-sha",
                "targets": {},
            }
        ],
    }


def test_v34_2_builds_deterministic_confirmation(monkeypatch):
    monkeypatch.setattr(
        "src.socmint.human_confirmation_framework_v34_2."
        "build_action_eligibility_delegate_resolution",
        lambda case_id: _eligible_resolution(case_id),
    )
    first = build_confirmation_contract(
        "case-1", "record_retention_decision", {"disposition": "retain"}
    )
    second = build_confirmation_contract(
        "case-1", "record_retention_decision", {"disposition": "retain"}
    )
    assert first["status"] == "confirmation_required"
    assert first["confirmation_id"] == second["confirmation_id"]
    assert first["confirmation_sha256"] == second["confirmation_sha256"]
    assert first["execution_performed"] is False


def test_v34_3_to_v34_6_execute_only_confirmed_allowlisted_delegate(monkeypatch):
    reset_confirmation_consumption_for_tests()
    monkeypatch.setattr(
        "src.socmint.human_confirmation_framework_v34_2."
        "build_action_eligibility_delegate_resolution",
        lambda case_id: _eligible_resolution(case_id),
    )
    contract = build_confirmation_contract(
        "case-1", "record_retention_decision", {"disposition": "retain"}
    )
    calls = []
    service = contract["delegate_service"]
    delegates = {service: lambda **kwargs: calls.append(kwargs) or {"id": "r-1"}}

    denied = execute_confirmed_action(
        contract, contract["confirmation_id"], False, "admin", delegates
    )
    assert denied["execution_performed"] is False
    assert calls == []

    result = execute_confirmed_action(
        contract, contract["confirmation_id"], True, "admin", delegates
    )
    assert result["status"] == "executed"
    assert result["action_family"] == "recall_retention"
    assert result["automatic_execution"] is False
    assert calls == [
        {
            "disposition": "retain",
            "case_id": "case-1",
            "confirmed": True,
        }
    ]

    duplicate = execute_confirmed_action(
        contract, contract["confirmation_id"], True, "admin", delegates
    )
    assert duplicate["status"] == "duplicate_rejected"
    assert len(calls) == 1


def test_v34_7_product_review_requires_complete_route_set():
    blocked = build_governance_execution_product_review([])
    assert blocked["ready"] is False
    assert blocked["missing_route_count"] == len(REQUIRED_ROUTES)

    class Route:
        def __init__(self, rule):
            self.rule = rule

    ready = build_governance_execution_product_review(
        [Route(rule) for rule in REQUIRED_ROUTES]
    )
    assert ready["ready"] is True
    assert ready["action_family_count"] == 4
    assert ready["action_count"] == 8
    assert ready["automatic_execution_allowed"] is False


def test_v34_product_review_page_has_all_sections(monkeypatch):
    from src.socmint.governance_execution_product_review_routes_v34_7 import (
        register_governance_execution_product_review_routes_v34_7,
    )

    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.governance_execution_product_review_routes_v34_7."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    register_governance_execution_product_review_routes_v34_7(app)
    client = app.test_client()
    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.get("/dissemination-governance/v34-product-review")
    source = response.get_data(as_text=True)
    for section in (
        "action-eligibility",
        "human-confirmation",
        "audience-package-authorization",
        "delivery-retry",
        "feedback-correction",
        "recall-retention",
        "release-closure",
    ):
        assert f'id="{section}"' in source

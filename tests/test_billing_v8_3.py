import hashlib
import hmac
import json

from src.socmint import database as db
from src.socmint.billing import billing_status
from src.socmint.billing import create_checkout_session
from src.socmint.billing import process_subscription_event
from src.socmint.billing import verify_webhook_signature
from src.socmint.membership import ensure_default_membership


def test_checkout_session_requires_paid_plan_and_records_session(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("buyer", "StrongPass123!", role="viewer")

    checkout = create_checkout_session(
        "buyer", "pro", success_url="https://example/success"
    )
    status = billing_status("buyer")

    assert checkout["schema"] == "socmint.billing.v8_3_0"
    assert checkout["plan"] == "pro"
    assert checkout["checkout_id"].startswith("cs_test_")
    assert status["checkout_sessions"][0]["plan_key"] == "pro"


def test_paid_webhook_activates_membership_and_is_idempotent(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("buyer", "StrongPass123!", role="viewer")
    ensure_default_membership("buyer")

    event = {
        "id": "evt_paid_1",
        "type": "checkout.session.completed",
        "data": {"username": "buyer", "plan": "pro", "price_id": "price_socmint_pro"},
    }
    first = process_subscription_event(event)
    second = process_subscription_event(event)
    status = billing_status("buyer")

    assert first["action"] == "membership_activated"
    assert second["action"] == "ignored_duplicate"
    assert status["membership"]["plan"] == "pro"
    assert status["membership"]["status"] == "active"
    assert len(status["events"]) == 1


def test_payment_failed_marks_grace_but_keeps_plan(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("buyer", "StrongPass123!", role="viewer")
    process_subscription_event(
        {
            "id": "evt_paid_1",
            "type": "invoice.paid",
            "data": {"username": "buyer", "plan": "starter"},
        }
    )

    result = process_subscription_event(
        {
            "id": "evt_failed_1",
            "type": "invoice.payment_failed",
            "data": {"username": "buyer", "plan": "starter"},
        }
    )

    assert result["action"] == "membership_past_due"
    assert result["membership"]["plan"] == "starter"
    assert result["membership"]["status"] == "past_due_grace"


def test_subscription_cancel_downgrades_to_free(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("buyer", "StrongPass123!", role="viewer")
    process_subscription_event(
        {
            "id": "evt_paid_1",
            "type": "invoice.paid",
            "data": {"username": "buyer", "plan": "team"},
        }
    )
    result = process_subscription_event(
        {
            "id": "evt_cancel_1",
            "type": "customer.subscription.deleted",
            "data": {"username": "buyer", "plan": "team"},
        }
    )

    assert result["action"] == "membership_downgraded"
    assert result["membership"]["plan"] == "free"
    assert result["membership"]["usage"]["signed_exports_per_month"]["limit"] == 0


def test_webhook_signature_verification():
    payload = json.dumps({"id": "evt_1"}, sort_keys=True)
    secret = "whsec_test"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    assert verify_webhook_signature(payload, signature, secret) is True
    assert verify_webhook_signature(payload, "bad", secret) is False

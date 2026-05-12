from src.socmint import database as db
from src.socmint.billing_integration import billing_link_status
from src.socmint.billing_integration import billing_provider_config
from src.socmint.billing_integration import link_customer
from src.socmint.billing_integration import normalize_provider_event
from src.socmint.billing_integration import process_provider_event


def test_customer_link_activates_plan(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("buyer", "StrongPass123!", role="viewer")

    status = link_customer(
        "buyer",
        "cus_test_123",
        subscription_id="sub_test_123",
        plan_key="pro",
        status="active",
    )

    assert status["schema"] == "socmint.billing_integration.v9_1_0"
    assert status["linked"] is True
    assert status["membership"]["plan"] == "pro"
    assert status["link"]["customer_id"] == "cus_test_123"


def test_provider_event_normalizes_nested_stripe_shape():
    event = {
        "id": "evt_123",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_123",
                "customer": "cus_123",
                "client_reference_id": "buyer",
                "status": "active",
                "items": {"data": [{"price": {"id": "price_socmint_pro"}}]},
            }
        },
    }

    normalized = normalize_provider_event(event)

    assert normalized["event_id"] == "evt_123"
    assert normalized["username"] == "buyer"
    assert normalized["customer_id"] == "cus_123"
    assert normalized["subscription_id"] == "sub_123"
    assert normalized["plan_key"] == "pro"


def test_provider_event_processes_and_links_customer(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    db.create_user("buyer", "StrongPass123!", role="viewer")
    event = {
        "id": "evt_paid_123",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "sub_123",
                "customer": "cus_123",
                "client_reference_id": "buyer",
                "status": "active",
                "items": {"data": [{"price": {"id": "price_socmint_team"}}]},
            }
        },
    }

    result = process_provider_event(event)
    status = billing_link_status("buyer")

    assert result["schema"] == "socmint.billing_integration.v9_1_0"
    assert result["billing_result"]["action"] == "membership_activated"
    assert status["linked"] is True
    assert status["membership"]["plan"] == "team"


def test_billing_provider_config_documents_requirements():
    config = billing_provider_config()

    assert config["schema"] == "socmint.billing_integration.v9_1_0"
    assert "STRIPE_SECRET_KEY" in config["requires"]
    assert "pro" in config["configured_price_ids"]

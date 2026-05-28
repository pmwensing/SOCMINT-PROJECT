from socmint.dashboard import create_app
from socmint.normalization_review_queue_routes_v13 import register_normalization_review_queue_routes
from socmint.normalization_review_queue_v13 import account_item
from socmint.normalization_review_queue_v13 import loads_dict


class DummyAccount:
    id = 1
    subject_id = 2
    discovery_type = "profile"
    account_value = "example"
    confidence = "0.8"
    platform = "manual"
    profile_url = "https://example.test/profile"
    review_state = "unreviewed"
    created_at = None


def test_loads_dict_handles_bad_json():
    assert loads_dict("{bad json") == {}
    assert loads_dict("[]") == {}
    assert loads_dict('{"review_state":"confirmed"}') == {"review_state": "confirmed"}


def test_account_item_shape():
    item = account_item(DummyAccount())

    assert item["kind"] == "account_discovery"
    assert item["subject_id"] == 2
    assert item["review_state"] == "unreviewed"
    assert item["evidence_ref"] == "https://example.test/profile"


def test_normalization_review_queue_route_registers_once():
    app = create_app()
    register_normalization_review_queue_routes(app)
    register_normalization_review_queue_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/review/normalization-queue" in rules

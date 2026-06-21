from socmint.normalization_review_queue_routes_v13 import parse_min_confidence
from socmint.normalization_review_queue_v13 import confidence_float
from socmint.normalization_review_queue_v13 import filter_queue_items


def test_parse_min_confidence_optional():
    assert parse_min_confidence(None) is None
    assert parse_min_confidence("") is None
    assert parse_min_confidence("0.75") == 0.75


def test_confidence_float_handles_bad_values():
    assert confidence_float("0.8") == 0.8
    assert confidence_float(None) == 0.0
    assert confidence_float("bad") == 0.0


def test_filter_queue_items_by_kind_state_and_confidence():
    items = [
        {"kind": "observation", "review_state": "unreviewed", "confidence": "0.8"},
        {
            "kind": "account_discovery",
            "review_state": "unreviewed",
            "confidence": "0.4",
        },
        {"kind": "observation", "review_state": "confirmed", "confidence": "0.9"},
    ]

    result = filter_queue_items(
        items,
        review_state="unreviewed",
        kind="observation",
        min_confidence=0.5,
    )

    assert result == [
        {"kind": "observation", "review_state": "unreviewed", "confidence": "0.8"}
    ]

from socmint.dashboard import create_app
from socmint.normalization_review_update_routes_v13 import (
    normalization_update_return_target,
)
from socmint.normalization_review_update_routes_v13 import (
    normalization_update_wants_json,
)


def test_normalization_update_wants_json_for_json_request():
    app = create_app()
    with app.test_request_context(
        "/api/v1/review/normalization-update",
        method="POST",
        json={"kind": "observation"},
    ):
        assert normalization_update_wants_json() is True


def test_normalization_update_return_target_defaults_to_queue():
    app = create_app()
    with app.test_request_context(
        "/api/v1/review/normalization-update",
        method="POST",
        data={"kind": "observation"},
    ):
        assert normalization_update_return_target() == "/review/normalization-queue"


def test_normalization_update_return_target_uses_referer():
    app = create_app()
    with app.test_request_context(
        "/api/v1/review/normalization-update",
        method="POST",
        data={"kind": "observation"},
        headers={"Referer": "/review/normalization-queue?review_state=confirmed"},
    ):
        assert (
            normalization_update_return_target()
            == "/review/normalization-queue?review_state=confirmed"
        )

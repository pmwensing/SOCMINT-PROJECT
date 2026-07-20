from pathlib import Path

from flask import Flask

from src.socmint import import_observation_promotion_routes_v37_4 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v37-4-route-secret"
    routes.register_import_observation_promotion_routes_v37_4(app)
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(
        routes,
        "current_promotions",
        lambda: [{"staged_record_id": "record-1", "promotion_id": "promotion-1"}],
    )
    monkeypatch.setattr(
        routes,
        "find_promotion",
        lambda record_id: {"staged_record_id": record_id} if record_id == "record-1" else None,
    )
    monkeypatch.setattr(
        routes,
        "promote_reviewed_record",
        lambda **kwargs: {
            "status": "reviewed_import_record_promoted",
            "staged_record_id": kwargs["staged_record_id"],
            "bulk_promotion_performed": False,
            "automatic_promotion_performed": False,
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v37_4_routes_require_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    path = "/api/v1/import-observation-promotions"
    assert client.get(path).status_code == 401
    _login(client, "viewer")
    assert client.get(path).status_code == 403
    _login(client, "admin")
    payload = client.get(path).get_json()
    assert payload["count"] == 1
    assert payload["bulk_promotion_available"] is False
    assert payload["automatic_promotion_available"] is False


def test_v37_4_single_record_promotion_and_detail_routes(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    promoted = client.post(
        "/api/v1/import-records/record-1/promote",
        json={
            "derivation_method": "reviewed_operator_import",
            "reason": "Promote.",
            "confirmed": True,
        },
    )
    assert promoted.status_code == 200
    assert promoted.get_json()["bulk_promotion_performed"] is False
    assert client.get(
        "/api/v1/import-records/record-1/promotion"
    ).status_code == 200
    assert client.get(
        "/api/v1/import-records/missing/promotion"
    ).status_code == 404


def test_v37_4_has_no_bulk_or_automatic_promotion_route():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    route_source = (
        root / "src/socmint/import_observation_promotion_routes_v37_4.py"
    ).read_text(encoding="utf-8")
    service_source = (
        root / "src/socmint/import_observation_promotion_v37_4.py"
    ).read_text(encoding="utf-8")
    assert "register_import_observation_promotion_routes_v37_4" in chain
    assert "register_import_observation_promotion_routes_v37_4(app)" in chain
    assert "/bulk" not in route_source
    assert "/automatic" not in route_source
    assert "derive_observation" in service_source
    assert "bulk_promotion_performed" in service_source

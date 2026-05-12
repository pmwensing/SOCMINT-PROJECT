from flask import Flask

from src.socmint.operator_smoke import OPERATOR_SMOKE_SCHEMA
from src.socmint.operator_smoke import operator_smoke_matrix
from src.socmint.operator_smoke import operator_smoke_summary
from src.socmint.operator_smoke import validate_smoke_routes
from src.socmint.production_release_routes import register_production_release_routes


def test_operator_smoke_matrix_shape():
    matrix = operator_smoke_matrix()

    assert matrix["schema"] == OPERATOR_SMOKE_SCHEMA
    assert matrix["route_count"] == len(matrix["routes"])
    assert matrix["route_count"] >= 15
    assert "api" in matrix["surfaces"]
    assert "browser" in matrix["surfaces"]


def test_operator_smoke_summary_counts():
    summary = operator_smoke_summary()

    assert summary["schema"] == OPERATOR_SMOKE_SCHEMA
    assert summary["route_count"] >= summary["auth_required"]
    assert summary["auth_required"] >= summary["admin_required"]
    assert summary["public_routes"] > 0


def test_operator_smoke_routes_register_and_require_admin():
    app = Flask(__name__)
    app.secret_key = "test"
    register_production_release_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/admin/operator-smoke/matrix" in rules
    assert "/api/v1/admin/operator-smoke/summary" in rules
    assert "/api/v1/admin/operator-smoke/validate" in rules

    client = app.test_client()
    response = client.get("/api/v1/admin/operator-smoke/summary")
    assert response.status_code == 403


def test_operator_smoke_validation_flags_missing_routes_on_minimal_app():
    app = Flask(__name__)
    result = validate_smoke_routes(app)

    assert result["schema"] == OPERATOR_SMOKE_SCHEMA
    assert result["status"] == "missing_routes"
    assert result["missing_count"] > 0

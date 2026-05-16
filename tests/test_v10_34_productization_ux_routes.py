import pytest
from flask import Flask
from src.socmint.v10_34_productization_ux_layer import ProductizationUXV1034
from src.socmint.v10_34_productization_ux_routes import register_v10_34_productization_ux_routes

@pytest.fixture
def app():
    app = Flask(__name__)
    register_v10_34_productization_ux_routes(app)
    return app.test_client()


def test_summary_endpoint_returns_200(app):
    response = app.post('/api/v10.34/productization/cases/case1/summary', json={'registry': {}})
    assert response.status_code == 200
    data = response.get_json()
    assert 'case_id' in data
    assert 'status' in data
    assert 'delivery_count' in data
    assert 'operator_hints' in data


def test_ui_endpoint_returns_200(app):
    response = app.post('/api/v10.34/productization/cases/case1/ui', json={'registry': {}})
    assert response.status_code == 200
    data = response.get_json()
    assert 'highlighted_actions' in data
    assert 'summary_card_color' in data
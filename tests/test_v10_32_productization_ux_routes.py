from flask import Flask
import pytest

from src.socmint.v10_32_productization_ux_routes import register_v10_32_productization_ux_routes

@pytest.fixture
def app_client():
    app = Flask(__name__)
    register_v10_32_productization_ux_routes(app)
    return app.test_client()

@pytest.fixture
def sample_registry():
    return {
        'latest_delivery_id': 'delivery-123',
        'latest_readiness': 'ready',
        'deliveries': [{'delivery_id': 'delivery-123', 'readiness': 'ready', 'bundle_name': 'Test Bundle'}]
    }

def test_summary_endpoint_returns_expected_fields(app_client, sample_registry):
    client = app_client
    response = client.post('/api/v1/v10/productization/cases/case-123/summary', json={'registry': sample_registry})
    data = response.get_json()

    assert data['case_id'] == 'case-123'
    assert data['latest_delivery_id'] == 'delivery-123'
    assert 'navigation_hints' in data


def test_ui_endpoint_returns_expected_fields(app_client, sample_registry):
    client = app_client
    response = client.post('/api/v1/v10/productization/cases/case-123/ui', json={'registry': sample_registry})
    data = response.get_json()

    assert 'highlighted_actions' in data
    assert 'summary_card_color' in data
    assert data['summary_card_color'] == 'green'

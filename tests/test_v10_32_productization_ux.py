import pytest
from src.socmint.v10_32_productization_ux_layer import ProductizationUX


@pytest.fixture
def sample_registry():
    return {
        'latest_delivery_id': 'delivery-123',
        'latest_readiness': 'ready',
        'deliveries': [
            {'delivery_id': 'delivery-123', 'readiness': 'ready', 'bundle_name': 'Test Bundle'}
        ]
    }


def test_enhanced_summary_contains_expected_fields(sample_registry):
    ux = ProductizationUX('case-123', sample_registry)
    summary = ux.enhanced_summary()

    assert summary['case_id'] == 'case-123'
    assert summary['delivery_count'] == 1
    assert summary['latest_delivery_id'] == 'delivery-123'
    assert summary['latest_readiness'] == 'ready'
    assert 'navigation_hints' in summary


def test_navigation_hints_ready(sample_registry):
    ux = ProductizationUX('case-123', sample_registry)
    hints = ux._navigation_hints()

    assert isinstance(hints, list)
    assert 'Proceed to human approval' in hints


def test_ui_polish_returns_expected_fields(sample_registry):
    ux = ProductizationUX('case-123', sample_registry)
    ui = ux.ui_polish()

    assert 'highlighted_actions' in ui
    assert 'summary_card_color' in ui
    assert ui['summary_card_color'] == 'green'

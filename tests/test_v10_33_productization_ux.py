import pytest
from src.socmint.v10_33_productization_ux_layer import ProductizationUXV1033

@pytest.fixture
def sample_registry():
    return {
        'case1': {'status': 'open', 'deliveries': [{'id': 'd1'}, {'id': 'd2'}]},
        'case2': {'status': 'pending', 'deliveries': []}
    }


def test_enhanced_summary_returns_expected_fields(sample_registry):
    ux = ProductizationUXV1033(sample_registry)
    summary = ux.enhanced_summary('case1')

    assert summary['case_id'] == 'case1'
    assert summary['status'] == 'open'
    assert summary['delivery_count'] == 2
    assert 'operator_hints' in summary


def test_operator_hints_returns_list(sample_registry):
    ux = ProductizationUXV1033(sample_registry)
    hints = ux._operator_hints('case2')

    assert isinstance(hints, list)
    assert 'Review flagged deliveries' in hints


def test_ui_polish_returns_expected_fields(sample_registry):
    ux = ProductizationUXV1033(sample_registry)
    ui = ux.ui_polish('case1')

    assert 'highlighted_actions' in ui
    assert 'summary_card_color' in ui
    assert ui['summary_card_color'] == 'blue'
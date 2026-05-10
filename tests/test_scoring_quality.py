from src.socmint.scoring import score_observation


def test_connector_quality_delta_adjusts_score():
    assert score_observation(base=0.7, connector_quality_delta=-0.1) == 0.6
    assert score_observation(base=0.7, connector_quality_delta=0.05) == 0.75

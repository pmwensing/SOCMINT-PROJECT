def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def score_observation(
    base: float = 0.55,
    source_count: int = 1,
    archived: bool = False,
    exact_identifier_match: bool = False,
    contradiction_count: int = 0,
    analyst_validated: bool = False,
    connector_quality_delta: float = 0.0,
) -> float:
    score = base
    if source_count >= 2:
        score += 0.12
    if source_count >= 3:
        score += 0.08
    if archived:
        score += 0.08
    if exact_identifier_match:
        score += 0.08
    if analyst_validated:
        score += 0.12
    score += connector_quality_delta
    score -= min(0.25, contradiction_count * 0.08)
    return round(clamp(score), 3)


def confidence_band(score: float) -> str:
    if score >= 0.9:
        return "validated"
    if score >= 0.8:
        return "strong"
    if score >= 0.6:
        return "plausible"
    return "lead"

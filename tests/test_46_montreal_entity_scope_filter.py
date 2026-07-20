from socmint.cases.entity_scope_filter import ScopeStatus, assert_export_allowed, evaluate_text_scope


def _cowdy(number: str) -> str:
    return f"{number} " + "Cow" + "dy"


def test_46_montreal_address_is_in_scope():
    decision = evaluate_text_scope("City order for 46 Montreal Street Apt B")
    assert decision.status == ScopeStatus.IN_SCOPE
    assert "46 montreal street" in decision.matched_terms


def test_46monst_alias_is_in_scope():
    decision = evaluate_text_scope("46MONST fire inspection record")
    assert decision.status == ScopeStatus.IN_SCOPE


def test_excluded_address_without_46_montreal_anchor_is_out_of_scope():
    decision = evaluate_text_scope(f"{_cowdy('71')} unrelated maintenance issue")
    assert decision.status == ScopeStatus.OUT_OF_SCOPE


def test_excluded_address_export_raises():
    try:
        assert_export_allowed(f"{_cowdy('81')} unrelated issue")
    except ValueError as exc:
        assert "Cowdy" in str(exc)
    else:
        raise AssertionError("Expected excluded-address-only export to be blocked")


def test_559_macdonnel_is_relocation_context_only():
    decision = evaluate_text_scope("559 Macdonnel suitable relocation after displacement")
    assert decision.status == ScopeStatus.RELOCATION_CONTEXT
    assert "mitigation" in decision.reason.lower() or "relocation" in decision.reason.lower()


def test_direct_authority_reference_is_in_scope_when_tied_to_46_montreal_issue():
    decision = evaluate_text_scope("Electrical Safety Authority inspection for 46 Montreal")
    assert decision.status == ScopeStatus.IN_SCOPE


def test_unanchored_entity_requires_candidate_review():
    decision = evaluate_text_scope("Example Contractor Ltd")
    assert decision.status == ScopeStatus.CANDIDATE_REVIEW_REQUIRED


def test_empty_text_requires_candidate_review():
    decision = evaluate_text_scope("")
    assert decision.status == ScopeStatus.CANDIDATE_REVIEW_REQUIRED

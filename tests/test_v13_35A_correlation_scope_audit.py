from pathlib import Path


def test_v13_35A_audit_routes_registered():
    wsgi = Path("src/socmint/wsgi.py").read_text()

    assert "register_correlation_scope_audit_routes_v13_35" in wsgi
    assert "/api/v1/audit/correlation-scope/v13.35" in Path(
        "src/socmint/correlation_scope_audit_v13_35.py"
    ).read_text()
    assert "/audit/correlation-scope/v13.35" in Path(
        "src/socmint/correlation_scope_audit_v13_35.py"
    ).read_text()


def test_scope_gate_quarantines_ambiguous_cross_scope_match():
    from src.socmint.correlation_scope_audit_v13_35 import scope_gate_decision

    decision = scope_gate_decision(
        same_scope=False,
        same_target=False,
        analyst_merge=False,
        ambiguous=True,
    )

    assert decision["state"] == "quarantine"
    assert decision["reason"] == "ambiguous_cross_scope_match"


def test_scope_gate_allows_only_safe_paths():
    from src.socmint.correlation_scope_audit_v13_35 import scope_gate_decision

    assert scope_gate_decision(same_scope=True)["state"] == "allowed"
    assert scope_gate_decision(analyst_merge=True)["state"] == "allowed"
    assert scope_gate_decision(same_target=True)["state"] == "allowed"
    assert scope_gate_decision()["state"] == "needs_review"


def test_schema_scope_coverage_is_audit_only_and_reports_missing_columns():
    from src.socmint.correlation_scope_audit_v13_35 import schema_scope_coverage

    coverage = schema_scope_coverage()

    assert coverage["mode"] == "audit_only_no_schema_migration"
    assert "spine_seeds" in coverage["required"]
    assert "spine_connector_runs" in coverage["required"]
    assert "spine_observations" in coverage["required"]
    assert "spine_dossier_assertions" in coverage["required"]
    assert isinstance(coverage["missing"], list)


def test_payload_records_safe_decision_and_policy_gate():
    from src.socmint.correlation_scope_audit_v13_35 import correlation_scope_audit_payload

    payload = correlation_scope_audit_payload()

    assert payload["schema"] == "socmint.correlation_scope_audit.v13_35A"
    assert payload["version"] == "v13.35A"
    assert payload["safe_decision"]["correlation_correctness_proven"] is False
    assert payload["safe_decision"]["expand_enrichment_features"] is False
    assert payload["safe_decision"]["quarantine_ambiguous_matches"] is True
    assert payload["policy_gate"]["audit_first_no_schema_migration"] is True
    assert "same_scope" in payload["policy_gate"]["promotion_requires"]
    assert "deterministic_same_target" in payload["policy_gate"]["promotion_requires"]

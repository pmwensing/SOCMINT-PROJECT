from socmint.claim_evidence_ledger_routes_v13 import register_claim_evidence_ledger_routes
from socmint.claim_evidence_ledger_v13 import build_claim_evidence_ledger
from socmint.dashboard import create_app


def test_claim_evidence_ledger_missing_subject_shape(monkeypatch, tmp_path):
    from socmint import database as db

    db_path = tmp_path / "ledger_missing.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    db.configure_database(f"sqlite:///{db_path}")

    payload = build_claim_evidence_ledger(999)

    assert payload["schema"] == "socmint.claim_evidence_ledger.v13_5"
    assert payload["subject_exists"] is False
    assert payload["summary"]["claim_count"] == 0
    assert payload["summary"]["missing_evidence"] == 0


def test_claim_evidence_ledger_route_registers_once():
    app = create_app()
    register_claim_evidence_ledger_routes(app)
    register_claim_evidence_ledger_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/subjects/<int:subject_id>/claim-evidence-ledger" in rules

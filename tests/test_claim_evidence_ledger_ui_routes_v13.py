from socmint.claim_evidence_ledger_ui_routes_v13 import register_claim_evidence_ledger_ui_routes
from socmint.dashboard import create_app


def test_claim_evidence_ledger_ui_route_registers_once():
    app = create_app()
    register_claim_evidence_ledger_ui_routes(app)
    register_claim_evidence_ledger_ui_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/subjects/<int:subject_id>/claim-evidence-ledger" in rules

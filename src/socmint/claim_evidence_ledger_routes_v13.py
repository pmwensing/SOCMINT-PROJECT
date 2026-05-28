from __future__ import annotations

from flask import jsonify

from .claim_evidence_ledger_v13 import build_claim_evidence_ledger


def register_claim_evidence_ledger_routes(app) -> None:
    if "api_subject_claim_evidence_ledger_v13" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_subject_claim_evidence_ledger_v13(subject_id: int):
        return jsonify(build_claim_evidence_ledger(subject_id))

    app.add_url_rule(
        "/api/v1/subjects/<int:subject_id>/claim-evidence-ledger",
        endpoint="api_subject_claim_evidence_ledger_v13",
        view_func=api_subject_claim_evidence_ledger_v13,
        methods=["GET"],
    )

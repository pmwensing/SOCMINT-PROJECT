from __future__ import annotations

from flask import render_template

from .claim_evidence_ledger_v13 import build_claim_evidence_ledger


def register_claim_evidence_ledger_ui_routes(app) -> None:
    if "claim_evidence_ledger_view_v13" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def claim_evidence_ledger_view_v13(subject_id: int):
        payload = build_claim_evidence_ledger(subject_id)
        return render_template(
            "claim_evidence_ledger.html",
            payload=payload,
            subject_id=subject_id,
        )

    app.add_url_rule(
        "/subjects/<int:subject_id>/claim-evidence-ledger",
        endpoint="claim_evidence_ledger_view_v13",
        view_func=claim_evidence_ledger_view_v13,
        methods=["GET"],
    )

from __future__ import annotations

from flask import jsonify, render_template, request

from .assertion_trust_gate_v12_8_1 import assertion_command_center_card
from .assertion_trust_gate_v12_8_1 import assertion_release_gate
from .assertion_trust_gate_v12_8_1 import assertion_trust_dashboard_plus
from .assertion_trust_gate_v12_8_1 import assertion_trust_summary
from .assertion_trust_gate_v12_8_1 import write_assertion_trust_report


def _subject_id() -> int | None:
    raw = request.args.get("subject_id")
    return int(raw) if raw and raw.isdigit() else None


def register_assertion_trust_gate_routes(app) -> None:
    if "assertion_trust_gate_dashboard" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def assertion_trust_gate_dashboard():
        payload = assertion_trust_dashboard_plus(subject_id=_subject_id())
        card = assertion_command_center_card(subject_id=_subject_id())
        return render_template("assertion_trust_gate_dashboard.html", payload=payload, card=card)

    @login_required
    def api_assertion_trust_gate():
        return jsonify(assertion_release_gate(subject_id=_subject_id()))

    @login_required
    def api_assertion_trust_summary():
        return jsonify(assertion_trust_summary(subject_id=_subject_id()))

    @login_required
    def api_assertion_trust_report():
        return jsonify(write_assertion_trust_report(subject_id=_subject_id()))

    app.add_url_rule("/assertions/trust/gate", endpoint="assertion_trust_gate_dashboard", view_func=assertion_trust_gate_dashboard, methods=["GET"])
    app.add_url_rule("/api/v1/assertions/trust/gate", endpoint="api_assertion_trust_gate", view_func=api_assertion_trust_gate, methods=["GET"])
    app.add_url_rule("/api/v1/assertions/trust/summary", endpoint="api_assertion_trust_summary", view_func=api_assertion_trust_summary, methods=["GET"])
    app.add_url_rule("/api/v1/assertions/trust/report", endpoint="api_assertion_trust_report", view_func=api_assertion_trust_report, methods=["GET"])

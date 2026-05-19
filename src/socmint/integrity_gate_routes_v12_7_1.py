from __future__ import annotations

from flask import jsonify, render_template

from .integrity_gate_v12_7_1 import evidence_integrity_summary, integrity_release_gate, write_integrity_report


def integrity_command_center_card() -> dict:
    gate = integrity_release_gate()
    summary = gate.get("summary", {})
    return {
        "schema": "socmint.command_center_integrity_card.v12_7_1",
        "status": gate.get("status"),
        "decision": gate.get("release_gate_decision"),
        "item_count": summary.get("item_count", 0),
        "usable": summary.get("usable_count", 0),
        "review": summary.get("review_count", 0),
        "hold": summary.get("hold_count", 0),
        "avg_score": summary.get("avg_composite_score", 0),
        "href": "/evidence/integrity/gate",
    }


def register_integrity_gate_routes(app) -> None:
    if "integrity_gate_dashboard" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def integrity_gate_dashboard():
        return render_template("integrity_gate_dashboard.html", payload=integrity_release_gate(), card=integrity_command_center_card())

    @login_required
    def api_integrity_gate():
        return jsonify(integrity_release_gate())

    @login_required
    def api_integrity_summary():
        return jsonify(evidence_integrity_summary())

    @login_required
    def api_integrity_report_export():
        return jsonify(write_integrity_report())

    app.add_url_rule("/evidence/integrity/gate", endpoint="integrity_gate_dashboard", view_func=integrity_gate_dashboard, methods=["GET"])
    app.add_url_rule("/api/v1/evidence/integrity/gate", endpoint="api_integrity_gate", view_func=api_integrity_gate, methods=["GET"])
    app.add_url_rule("/api/v1/evidence/integrity/summary", endpoint="api_integrity_summary", view_func=api_integrity_summary, methods=["GET"])
    app.add_url_rule("/api/v1/evidence/integrity/report", endpoint="api_integrity_report_export", view_func=api_integrity_report_export, methods=["GET"])

from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .case_findings_v20 import (
    build_dossier_promotion_package,
    build_v20_product_checkpoint,
    decide_finding,
    list_findings,
    propose_finding,
    revise_finding,
)


def _login_required() -> bool:
    return bool(session.get("user"))


def _actor() -> str:
    return str(session.get("user") or "unknown")


def _payload() -> dict:
    value = request.get_json(silent=True)
    if isinstance(value, dict):
        return value
    return request.form.to_dict() if request.form else {}


def register_case_findings_routes_v20(app):
    @app.get("/case-findings/<case_id>")
    def case_findings_workspace_get_v20(case_id: str):
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        return render_template(
            "case_findings_workspace_v20.html",
            title="Case Findings Workspace",
            payload=list_findings(case_id),
        )

    @app.get("/api/v1/case-findings/<case_id>")
    def api_case_findings_get_v20(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(list_findings(case_id))

    @app.post("/api/v1/case-findings/<case_id>/proposals")
    def api_case_finding_proposal_post_v20_1(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = propose_finding(
            case_id,
            _payload(),
            actor=_actor(),
            ip_address=request.remote_addr,
        )
        result["workspace"] = list_findings(case_id)
        return jsonify(result), 200 if result.get("status") == "proposed" else 422

    @app.post("/api/v1/case-findings/<case_id>/<finding_id>/revisions")
    def api_case_finding_revision_post_v20_4(case_id: str, finding_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = revise_finding(
            case_id,
            finding_id,
            _payload(),
            actor=_actor(),
            ip_address=request.remote_addr,
        )
        result["workspace"] = list_findings(case_id)
        return jsonify(result), 200 if result.get("status") == "proposed" else 422

    @app.post("/api/v1/case-findings/<case_id>/<finding_id>/decision")
    def api_case_finding_decision_post_v20_3(case_id: str, finding_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = _payload()
        result = decide_finding(
            case_id,
            finding_id,
            str(payload.get("action") or ""),
            actor=_actor(),
            note=str(payload.get("note") or ""),
            ip_address=request.remote_addr,
        )
        result["workspace"] = list_findings(case_id)
        return jsonify(result), 200 if result.get("status") in {
            "approved",
            "rejected",
            "revision_required",
        } else 422

    @app.get("/api/v1/case-findings/<case_id>/dossier-package")
    def api_case_findings_dossier_package_get_v20_5(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_dossier_promotion_package(case_id, actor=_actor())
        return jsonify(result), 200 if result.get("status") == "ready" else 409

    @app.post("/api/v1/case-findings/<case_id>/dossier-package")
    def api_case_findings_dossier_package_post_v20_5(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_dossier_promotion_package(
            case_id,
            actor=_actor(),
            promote=True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "promoted" else 409

    @app.get("/api/v1/case-findings/product-review-checkpoint")
    def api_case_findings_product_checkpoint_get_v20_7():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_v20_product_checkpoint(routes=list(app.url_map.iter_rules()))
        return jsonify(result), 200 if result.get("ready") else 409

    return app

from __future__ import annotations

from flask import Response, jsonify, redirect, render_template, request, session, url_for

from .case_delivery_attempt_ledger_v16_1 import build_case_delivery_attempt_ledger_from_request
from .case_delivery_authorization_record_v15_5 import build_case_delivery_authorization_record_from_request
from .case_delivery_exception_review_v16_2 import build_case_delivery_exception_review_from_request
from .case_delivery_execution_envelope_v15_6 import build_case_delivery_execution_envelope_from_request
from .case_delivery_operations_reentry_envelope_v16_16 import build_case_delivery_operations_reentry_envelope_from_request
from .case_delivery_operations_reentry_envelope_verification_v16_17 import (
    verify_case_delivery_operations_reentry_envelope_from_request,
)
from .case_delivery_operations_v16_0 import build_case_delivery_operations_from_request
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request
from .case_delivery_recovery_action_receipt_v16_4 import build_case_delivery_recovery_action_receipt_from_request
from .case_delivery_recovery_action_receipt_verification_v16_5 import (
    verify_case_delivery_recovery_action_receipt_from_request,
)
from .case_delivery_recovery_closure_audit_package_v16_8 import (
    build_case_delivery_recovery_closure_audit_package_from_request,
)
from .case_delivery_recovery_closure_audit_package_verification_v16_9 import (
    verify_case_delivery_recovery_closure_audit_package_from_request,
)
from .case_delivery_recovery_closure_record_v16_6 import build_case_delivery_recovery_closure_record_from_request
from .case_delivery_recovery_closure_record_verification_v16_7 import (
    verify_case_delivery_recovery_closure_record_from_request,
)
from .case_delivery_recovery_continuation_gate_v16_12 import build_case_delivery_recovery_continuation_gate_from_request
from .case_delivery_recovery_continuation_gate_verification_v16_13 import (
    verify_case_delivery_recovery_continuation_gate_from_request,
)
from .case_delivery_recovery_finalization_record_v16_10 import build_case_delivery_recovery_finalization_record_from_request
from .case_delivery_recovery_finalization_record_verification_v16_11 import (
    verify_case_delivery_recovery_finalization_record_from_request,
)
from .case_delivery_recovery_resume_operations_snapshot_v16_14 import (
    build_case_delivery_recovery_resume_operations_snapshot_from_request,
)
from .case_delivery_recovery_resume_operations_snapshot_verification_v16_15 import (
    verify_case_delivery_recovery_resume_operations_snapshot_from_request,
)
from .case_delivery_handoff_package_v15_1 import build_case_delivery_handoff_package_from_request
from .case_delivery_handoff_package_v15_1 import case_delivery_handoff_markdown
from .case_delivery_handoff_verification_v15_2 import verify_case_delivery_handoff_package_from_request
from .case_delivery_readiness_receipt_v15_3 import build_case_delivery_readiness_receipt_from_request
from .case_delivery_readiness_receipt_verification_v15_4 import (
    verify_case_delivery_readiness_receipt_from_request,
)
from .case_delivery_workspace_v15 import build_case_delivery_workspace_from_request


def _login_required() -> bool:
    return bool(session.get("user"))


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def register_case_delivery_workspace_routes_v15(app):
    @app.get("/case-delivery")
    def case_delivery_workspace_v15():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        case_id = request.args.get("case_id", "case-delivery-preview")
        payload = build_case_delivery_workspace_from_request(case_id, {})
        return render_template(
            "case_delivery_workspace.html",
            title="Case Delivery Workspace",
            payload=payload,
        )

    @app.get("/api/v1/case-delivery/<case_id>")
    def api_case_delivery_workspace_get_v15(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(build_case_delivery_workspace_from_request(case_id, {}))

    @app.post("/api/v1/case-delivery/<case_id>")
    def api_case_delivery_workspace_post_v15(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(build_case_delivery_workspace_from_request(case_id, _request_payload()))

    @app.post("/api/v1/case-delivery/<case_id>/handoff-package")
    def api_case_delivery_handoff_package_post_v15_1(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(build_case_delivery_handoff_package_from_request(case_id, _request_payload()))

    @app.post("/api/v1/case-delivery/<case_id>/handoff-package/markdown")
    def api_case_delivery_handoff_markdown_post_v15_1(case_id: str):
        if not _login_required():
            return Response("login required\n", status=401, mimetype="text/plain")
        package = build_case_delivery_handoff_package_from_request(case_id, _request_payload())
        return Response(case_delivery_handoff_markdown(package), mimetype="text/markdown")

    @app.post("/api/v1/case-delivery/<case_id>/handoff-package/verify")
    def api_case_delivery_handoff_verification_post_v15_2(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(verify_case_delivery_handoff_package_from_request(case_id, _request_payload()))

    @app.post("/api/v1/case-delivery/<case_id>/readiness-receipt")
    def api_case_delivery_readiness_receipt_post_v15_3(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_readiness_receipt_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "issued" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/readiness-receipt/verify")
    def api_case_delivery_readiness_receipt_verify_post_v15_4(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = verify_case_delivery_readiness_receipt_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "verified" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/authorization-record")
    def api_case_delivery_authorization_record_post_v15_5(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_authorization_record_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "authorized" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/execution-envelope")
    def api_case_delivery_execution_envelope_post_v15_6(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_execution_envelope_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "ready_to_execute" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/operations")
    def api_case_delivery_operations_post_v16_0(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_operations_from_request(case_id, _request_payload())
        status_code = 200 if result.get("dispatchable") else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/attempt-ledger")
    def api_case_delivery_attempt_ledger_post_v16_1(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_attempt_ledger_from_request(case_id, _request_payload())
        status_code = 200 if result.get("state") != "blocked" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/exception-review")
    def api_case_delivery_exception_review_post_v16_2(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_exception_review_from_request(case_id, _request_payload())
        status_code = 200 if result.get("state") != "blocked" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery")
    def api_case_delivery_recovery_post_v16_3(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_recovery_from_request(case_id, _request_payload())
        status_code = 200 if result.get("state") != "blocked" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery-action-receipt")
    def api_case_delivery_recovery_action_receipt_post_v16_4(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_recovery_action_receipt_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "issued" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery-action-receipt/verify")
    def api_case_delivery_recovery_action_receipt_verify_post_v16_5(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = verify_case_delivery_recovery_action_receipt_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "verified" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery-closure-record")
    def api_case_delivery_recovery_closure_record_post_v16_6(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_recovery_closure_record_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "closed" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery-closure-record/verify")
    def api_case_delivery_recovery_closure_record_verify_post_v16_7(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = verify_case_delivery_recovery_closure_record_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "verified" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery-closure-audit-package")
    def api_case_delivery_recovery_closure_audit_package_post_v16_8(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_recovery_closure_audit_package_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "packaged" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery-closure-audit-package/verify")
    def api_case_delivery_recovery_closure_audit_package_verify_post_v16_9(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = verify_case_delivery_recovery_closure_audit_package_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "verified" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery-finalization-record")
    def api_case_delivery_recovery_finalization_record_post_v16_10(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_recovery_finalization_record_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "finalized" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery-finalization-record/verify")
    def api_case_delivery_recovery_finalization_record_verify_post_v16_11(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = verify_case_delivery_recovery_finalization_record_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "verified" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery-continuation-gate")
    def api_case_delivery_recovery_continuation_gate_post_v16_12(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_recovery_continuation_gate_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "open" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery-continuation-gate/verify")
    def api_case_delivery_recovery_continuation_gate_verify_post_v16_13(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = verify_case_delivery_recovery_continuation_gate_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "verified" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery-resume-operations-snapshot")
    def api_case_delivery_recovery_resume_operations_snapshot_post_v16_14(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_recovery_resume_operations_snapshot_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "ready" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/recovery-resume-operations-snapshot/verify")
    def api_case_delivery_recovery_resume_operations_snapshot_verify_post_v16_15(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = verify_case_delivery_recovery_resume_operations_snapshot_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "verified" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/operations-reentry-envelope")
    def api_case_delivery_operations_reentry_envelope_post_v16_16(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_case_delivery_operations_reentry_envelope_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "ready_to_dispatch" else 409
        return jsonify(result), status_code

    @app.post("/api/v1/case-delivery/<case_id>/operations-reentry-envelope/verify")
    def api_case_delivery_operations_reentry_envelope_verify_post_v16_17(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = verify_case_delivery_operations_reentry_envelope_from_request(case_id, _request_payload())
        status_code = 200 if result.get("status") == "verified" else 409
        return jsonify(result), status_code

    return app

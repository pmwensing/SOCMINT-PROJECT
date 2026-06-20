from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flask import (
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .case_delivery_attempt_ledger_v16_1 import (
    build_case_delivery_attempt_ledger_from_request,
)
from .case_delivery_authorization_record_v15_5 import (
    build_case_delivery_authorization_record_from_request,
)
from .case_delivery_exception_review_v16_2 import (
    build_case_delivery_exception_review_from_request,
)
from .case_delivery_execution_envelope_v15_6 import (
    build_case_delivery_execution_envelope_from_request,
)
from .case_delivery_handoff_package_v15_1 import (
    build_case_delivery_handoff_package_from_request,
)
from .case_delivery_handoff_package_v15_1 import case_delivery_handoff_markdown
from .case_delivery_handoff_verification_v15_2 import (
    verify_case_delivery_handoff_package_from_request,
)
from .case_delivery_operations_reentry_envelope_v16_16 import (
    build_case_delivery_operations_reentry_envelope_from_request,
)
from .case_delivery_operations_reentry_envelope_verification_v16_17 import (
    verify_case_delivery_operations_reentry_envelope_from_request,
)
from .case_delivery_operations_v16_0 import build_case_delivery_operations_from_request
from .case_delivery_readiness_receipt_v15_3 import (
    build_case_delivery_readiness_receipt_from_request,
)
from .case_delivery_readiness_receipt_verification_v15_4 import (
    verify_case_delivery_readiness_receipt_from_request,
)
from .case_delivery_recovery_action_receipt_v16_4 import (
    build_case_delivery_recovery_action_receipt_from_request,
)
from .case_delivery_recovery_action_receipt_verification_v16_5 import (
    verify_case_delivery_recovery_action_receipt_from_request,
)
from .case_delivery_recovery_chain_closure_audit_v16_18 import (
    audit_case_delivery_recovery_chain_closure,
)
from .case_delivery_recovery_closure_audit_package_v16_8 import (
    build_case_delivery_recovery_closure_audit_package_from_request,
)
from .case_delivery_recovery_closure_audit_package_verification_v16_9 import (
    verify_case_delivery_recovery_closure_audit_package_from_request,
)
from .case_delivery_recovery_closure_record_v16_6 import (
    build_case_delivery_recovery_closure_record_from_request,
)
from .case_delivery_recovery_closure_record_verification_v16_7 import (
    verify_case_delivery_recovery_closure_record_from_request,
)
from .case_delivery_recovery_continuation_gate_v16_12 import (
    build_case_delivery_recovery_continuation_gate_from_request,
)
from .case_delivery_recovery_continuation_gate_verification_v16_13 import (
    verify_case_delivery_recovery_continuation_gate_from_request,
)
from .case_delivery_recovery_finalization_record_v16_10 import (
    build_case_delivery_recovery_finalization_record_from_request,
)
from .case_delivery_recovery_finalization_record_verification_v16_11 import (
    verify_case_delivery_recovery_finalization_record_from_request,
)
from .case_delivery_recovery_resume_operations_snapshot_v16_14 import (
    build_case_delivery_recovery_resume_operations_snapshot_from_request,
)
from .case_delivery_recovery_resume_operations_snapshot_verification_v16_15 import (
    verify_case_delivery_recovery_resume_operations_snapshot_from_request,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request
from .case_delivery_workspace_v15 import build_case_delivery_workspace_from_request
from .product_readiness_operator_workflow_v17_0 import (
    build_product_readiness_operator_workflow_snapshot,
)


def _login_required() -> bool:
    return bool(session.get("user"))


def _request_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _json_route(
    builder: Callable[..., dict[str, Any]],
    status_predicate: Callable[[dict[str, Any]], bool] | None = None,
):
    def view(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = builder(case_id, _request_payload())
        status_code = (
            200 if status_predicate is None or status_predicate(result) else 409
        )
        return jsonify(result), status_code

    return view


def register_case_delivery_workspace_routes_v15(app):
    @app.get("/case-delivery")
    def case_delivery_workspace_v15():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        case_id = request.args.get("case_id", "case-delivery-preview")
        return render_template(
            "case_delivery_workspace.html",
            title="Case Delivery Workspace",
            payload=build_case_delivery_workspace_from_request(case_id, {}),
        )

    @app.get("/api/v1/case-delivery/<case_id>")
    def api_case_delivery_workspace_get_v15(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(build_case_delivery_workspace_from_request(case_id, {}))

    @app.post("/api/v1/case-delivery/<case_id>/handoff-package/markdown")
    def api_case_delivery_handoff_markdown_post_v15_1(case_id: str):
        if not _login_required():
            return Response("login required\n", status=401, mimetype="text/plain")
        return Response(
            case_delivery_handoff_markdown(
                build_case_delivery_handoff_package_from_request(
                    case_id, _request_payload()
                )
            ),
            mimetype="text/markdown",
        )

    @app.post("/api/v1/case-delivery/<case_id>/recovery-chain-closure-audit")
    def api_case_delivery_recovery_chain_closure_audit_post_v16_18(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = audit_case_delivery_recovery_chain_closure(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(result), 200 if result.get("status") == "closed" else 409

    @app.post("/api/v1/product-readiness/operator-workflow")
    def api_product_readiness_operator_workflow_post_v17_0():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_product_readiness_operator_workflow_snapshot(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(result), 200 if result.get("status") == "ready" else 409

    routes: tuple[
        tuple[
            str,
            str,
            Callable[..., dict[str, Any]],
            Callable[[dict[str, Any]], bool] | None,
        ],
        ...,
    ] = (
        (
            "api_case_delivery_workspace_post_v15",
            "/api/v1/case-delivery/<case_id>",
            build_case_delivery_workspace_from_request,
            None,
        ),
        (
            "api_case_delivery_handoff_package_post_v15_1",
            "/api/v1/case-delivery/<case_id>/handoff-package",
            build_case_delivery_handoff_package_from_request,
            None,
        ),
        (
            "api_case_delivery_handoff_verification_post_v15_2",
            "/api/v1/case-delivery/<case_id>/handoff-package/verify",
            verify_case_delivery_handoff_package_from_request,
            None,
        ),
        (
            "api_case_delivery_readiness_receipt_post_v15_3",
            "/api/v1/case-delivery/<case_id>/readiness-receipt",
            build_case_delivery_readiness_receipt_from_request,
            lambda r: r.get("status") == "issued",
        ),
        (
            "api_case_delivery_readiness_receipt_verify_post_v15_4",
            "/api/v1/case-delivery/<case_id>/readiness-receipt/verify",
            verify_case_delivery_readiness_receipt_from_request,
            lambda r: r.get("status") == "verified",
        ),
        (
            "api_case_delivery_authorization_record_post_v15_5",
            "/api/v1/case-delivery/<case_id>/authorization-record",
            build_case_delivery_authorization_record_from_request,
            lambda r: r.get("status") == "authorized",
        ),
        (
            "api_case_delivery_execution_envelope_post_v15_6",
            "/api/v1/case-delivery/<case_id>/execution-envelope",
            build_case_delivery_execution_envelope_from_request,
            lambda r: r.get("status") == "ready_to_execute",
        ),
        (
            "api_case_delivery_operations_post_v16_0",
            "/api/v1/case-delivery/<case_id>/operations",
            build_case_delivery_operations_from_request,
            lambda r: bool(r.get("dispatchable")),
        ),
        (
            "api_case_delivery_attempt_ledger_post_v16_1",
            "/api/v1/case-delivery/<case_id>/attempt-ledger",
            build_case_delivery_attempt_ledger_from_request,
            lambda r: r.get("state") != "blocked",
        ),
        (
            "api_case_delivery_exception_review_post_v16_2",
            "/api/v1/case-delivery/<case_id>/exception-review",
            build_case_delivery_exception_review_from_request,
            lambda r: r.get("state") != "blocked",
        ),
        (
            "api_case_delivery_recovery_post_v16_3",
            "/api/v1/case-delivery/<case_id>/recovery",
            build_case_delivery_recovery_from_request,
            lambda r: r.get("state") != "blocked",
        ),
        (
            "api_case_delivery_recovery_action_receipt_post_v16_4",
            "/api/v1/case-delivery/<case_id>/recovery-action-receipt",
            build_case_delivery_recovery_action_receipt_from_request,
            lambda r: r.get("status") == "issued",
        ),
        (
            "api_case_delivery_recovery_action_receipt_verify_post_v16_5",
            "/api/v1/case-delivery/<case_id>/recovery-action-receipt/verify",
            verify_case_delivery_recovery_action_receipt_from_request,
            lambda r: r.get("status") == "verified",
        ),
        (
            "api_case_delivery_recovery_closure_record_post_v16_6",
            "/api/v1/case-delivery/<case_id>/recovery-closure-record",
            build_case_delivery_recovery_closure_record_from_request,
            lambda r: r.get("status") == "closed",
        ),
        (
            "api_case_delivery_recovery_closure_record_verify_post_v16_7",
            "/api/v1/case-delivery/<case_id>/recovery-closure-record/verify",
            verify_case_delivery_recovery_closure_record_from_request,
            lambda r: r.get("status") == "verified",
        ),
        (
            "api_case_delivery_recovery_closure_audit_package_post_v16_8",
            "/api/v1/case-delivery/<case_id>/recovery-closure-audit-package",
            build_case_delivery_recovery_closure_audit_package_from_request,
            lambda r: r.get("status") == "packaged",
        ),
        (
            "api_case_delivery_recovery_closure_audit_package_verify_post_v16_9",
            "/api/v1/case-delivery/<case_id>/recovery-closure-audit-package/verify",
            verify_case_delivery_recovery_closure_audit_package_from_request,
            lambda r: r.get("status") == "verified",
        ),
        (
            "api_case_delivery_recovery_finalization_record_post_v16_10",
            "/api/v1/case-delivery/<case_id>/recovery-finalization-record",
            build_case_delivery_recovery_finalization_record_from_request,
            lambda r: r.get("status") == "finalized",
        ),
        (
            "api_case_delivery_recovery_finalization_record_verify_post_v16_11",
            "/api/v1/case-delivery/<case_id>/recovery-finalization-record/verify",
            verify_case_delivery_recovery_finalization_record_from_request,
            lambda r: r.get("status") == "verified",
        ),
        (
            "api_case_delivery_recovery_continuation_gate_post_v16_12",
            "/api/v1/case-delivery/<case_id>/recovery-continuation-gate",
            build_case_delivery_recovery_continuation_gate_from_request,
            lambda r: r.get("status") == "open",
        ),
        (
            "api_case_delivery_recovery_continuation_gate_verify_post_v16_13",
            "/api/v1/case-delivery/<case_id>/recovery-continuation-gate/verify",
            verify_case_delivery_recovery_continuation_gate_from_request,
            lambda r: r.get("status") == "verified",
        ),
        (
            "api_case_delivery_recovery_resume_operations_snapshot_post_v16_14",
            "/api/v1/case-delivery/<case_id>/recovery-resume-operations-snapshot",
            build_case_delivery_recovery_resume_operations_snapshot_from_request,
            lambda r: r.get("status") == "ready",
        ),
        (
            "api_case_delivery_recovery_resume_operations_snapshot_verify_post_v16_15",
            "/api/v1/case-delivery/<case_id>/recovery-resume-operations-snapshot/verify",
            verify_case_delivery_recovery_resume_operations_snapshot_from_request,
            lambda r: r.get("status") == "verified",
        ),
        (
            "api_case_delivery_operations_reentry_envelope_post_v16_16",
            "/api/v1/case-delivery/<case_id>/operations-reentry-envelope",
            build_case_delivery_operations_reentry_envelope_from_request,
            lambda r: r.get("status") == "ready_to_dispatch",
        ),
        (
            "api_case_delivery_operations_reentry_envelope_verify_post_v16_17",
            "/api/v1/case-delivery/<case_id>/operations-reentry-envelope/verify",
            verify_case_delivery_operations_reentry_envelope_from_request,
            lambda r: r.get("status") == "verified",
        ),
    )
    for endpoint, rule, builder, predicate in routes:
        app.add_url_rule(
            rule, endpoint, _json_route(builder, predicate), methods=["POST"]
        )

    return app

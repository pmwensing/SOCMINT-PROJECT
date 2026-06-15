from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .dossier_assembly_import_workspace_v21_1 import (
    build_dossier_assembly_workspace_v21_1,
    save_verified_dossier_arrangement,
)
from .dossier_citation_mapping_routes_v21_3 import (
    register_dossier_citation_mapping_routes_v21_3,
)
from .dossier_final_export_routes_v21_6 import (
    register_dossier_final_export_routes_v21_6,
)
from .dossier_package_import_v21_1 import (
    import_dossier_package,
    inspect_dossier_package_import,
)
from .dossier_product_review_routes_v21_7 import (
    register_dossier_product_review_routes_v21_7,
)
from .dossier_quality_review_routes_v21_4 import (
    register_dossier_quality_review_routes_v21_4,
)
from .dossier_release_history_routes_v22_6 import (
    register_dossier_release_history_routes_v22_6,
)
from .dossier_release_product_review_routes_v22_7 import (
    register_dossier_release_product_review_routes_v22_7,
)
from .dossier_release_workspace_routes_v22_0 import (
    register_dossier_release_workspace_routes_v22_0,
)
from .dossier_section_builder_v21_2 import (
    build_dossier_section_draft,
    save_dossier_draft_snapshot,
)
from .dossier_supervisor_approval_routes_v21_5 import (
    register_dossier_supervisor_approval_routes_v21_5,
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


def _subject_id() -> int | None:
    value = request.args.get("subject_id")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def register_dossier_assembly_routes_v21_0(app):
    @app.get("/dossier-assembly/<case_id>")
    def dossier_assembly_workspace_get_v21_0(case_id: str):
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        payload = build_dossier_assembly_workspace_v21_1(
            case_id,
            subject_id=_subject_id(),
        )
        payload["draft"] = build_dossier_section_draft(
            case_id,
            subject_id=_subject_id(),
        )
        return render_template(
            "dossier_assembly_workspace_v21_0.html",
            title="Dossier Assembly Workspace",
            payload=payload,
        )

    @app.get("/api/v1/dossier-assembly/<case_id>")
    def api_dossier_assembly_workspace_get_v21_0(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = build_dossier_assembly_workspace_v21_1(
            case_id,
            subject_id=_subject_id(),
        )
        payload["draft"] = build_dossier_section_draft(
            case_id,
            subject_id=_subject_id(),
        )
        return jsonify(payload)

    @app.get("/api/v1/dossier-assembly/<case_id>/package-import")
    def api_dossier_package_import_get_v21_1(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(inspect_dossier_package_import(case_id))

    @app.post("/api/v1/dossier-assembly/<case_id>/package-import")
    def api_dossier_package_import_post_v21_1(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = import_dossier_package(
            case_id,
            actor=_actor(),
            ip_address=request.remote_addr,
        )
        status_code = 200 if result.get("status") in {"imported", "duplicate"} else 422
        return jsonify(result), status_code

    @app.post("/api/v1/dossier-assembly/<case_id>/arrangement")
    def api_dossier_assembly_arrangement_post_v21_0(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = save_verified_dossier_arrangement(
            case_id,
            _payload(),
            actor=_actor(),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "saved" else 422

    @app.get("/api/v1/dossier-assembly/<case_id>/draft")
    def api_dossier_section_draft_get_v21_2(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_dossier_section_draft(
                case_id,
                subject_id=_subject_id(),
            )
        )

    @app.post("/api/v1/dossier-assembly/<case_id>/draft-snapshot")
    def api_dossier_section_draft_snapshot_post_v21_2(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = _payload()
        result = save_dossier_draft_snapshot(
            case_id,
            actor=_actor(),
            subject_id=_subject_id(),
            finding_order=payload.get("finding_order"),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "saved" else 422

    register_dossier_citation_mapping_routes_v21_3(app)
    register_dossier_quality_review_routes_v21_4(app)
    register_dossier_supervisor_approval_routes_v21_5(app)
    register_dossier_final_export_routes_v21_6(app)
    register_dossier_product_review_routes_v21_7(app)
    register_dossier_release_workspace_routes_v22_0(app)
    register_dossier_release_history_routes_v22_6(app)
    register_dossier_release_product_review_routes_v22_7(app)
    return app

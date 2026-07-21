from __future__ import annotations

from flask import jsonify, request, session

from .operational_import_v37_1 import (
    current_imports,
    find_import,
    register_import_envelope,
)
from .user_account_workspace_v28_1 import actor_is_administrator


def _payload() -> dict:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _authorized():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def register_operational_import_routes_v37_1(app):
    @app.get("/api/v1/operational-imports")
    def api_operational_imports_get_v37_1():
        _, error = _authorized()
        if error:
            return error
        case_id = str(request.args.get("case_id") or "").strip()
        items = current_imports()
        if case_id:
            items = [
                item
                for item in items
                if str((item.get("envelope") or {}).get("case_id") or "")
                == case_id
            ]
        return jsonify(
            {
                "schema": "socmint.operational_import_inventory.v37_1",
                "version": "v37.1.0",
                "imports": items,
                "count": len(items),
                "connector_execution_performed": False,
                "hidden_collection_performed": False,
            }
        )

    @app.post("/api/v1/operational-imports")
    def api_operational_import_post_v37_1():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = register_import_envelope(
            actor=actor,
            case_id=str(payload.get("case_id") or ""),
            purpose=str(payload.get("purpose") or ""),
            artifact_id=str(payload.get("artifact_id") or ""),
            content_sha256=str(payload.get("content_sha256") or ""),
            original_filename=str(payload.get("original_filename") or ""),
            media_type=str(payload.get("media_type") or ""),
            export_format=str(payload.get("export_format") or ""),
            tool_name=str(payload.get("tool_name") or ""),
            tool_version=str(payload.get("tool_version") or ""),
            adapter_name=str(payload.get("adapter_name") or ""),
            adapter_version=str(payload.get("adapter_version") or ""),
            exported_at=str(payload.get("exported_at") or ""),
            imported_at=str(payload.get("imported_at") or ""),
            declared_record_count=payload.get("declared_record_count", -1),
            source_references=payload.get("source_references"),
            collection_context=payload.get("collection_context"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") in {
            "operational_import_registered",
            "operational_import_reused",
        } else 422
        return jsonify(result), code

    @app.get("/api/v1/operational-imports/<import_id>")
    def api_operational_import_detail_get_v37_1(import_id: str):
        _, error = _authorized()
        if error:
            return error
        item = find_import(import_id)
        if item is None:
            return jsonify({"error": "operational import not found"}), 404
        return jsonify(item), 200

    return app

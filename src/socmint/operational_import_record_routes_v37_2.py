from __future__ import annotations

from flask import jsonify, request, session

from .operational_import_record_projection_v37_2 import (
    current_staged_record_projections,
    find_staged_record_projection,
)
from .operational_import_records_v37_2 import (
    current_batches,
    find_batch,
    stage_import_records,
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


def register_operational_import_record_routes_v37_2(app):
    @app.get("/api/v1/operational-import-records")
    def api_operational_import_records_get_v37_2():
        _, error = _authorized()
        if error:
            return error
        import_id = str(request.args.get("import_id") or "").strip() or None
        state = str(request.args.get("state") or "").strip()
        items = current_staged_record_projections(import_id)
        if state:
            items = [item for item in items if item.get("initial_state") == state]
        return jsonify(
            {
                "schema": "socmint.operational_import_record_inventory.v37_2",
                "version": "v37.2.0",
                "records": items,
                "count": len(items),
                "observation_created": False,
                "automatic_promotion": False,
            }
        )

    @app.post("/api/v1/operational-imports/<import_id>/records")
    def api_operational_import_records_post_v37_2(import_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = stage_import_records(
            actor=actor,
            import_id=import_id,
            records=payload.get("records"),
            adapter_diagnostics=payload.get("adapter_diagnostics"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") in {
            "import_records_staged",
            "staged_record_batch_reused",
        } else 422
        return jsonify(result), code

    @app.get("/api/v1/operational-import-records/<staged_record_id>")
    def api_operational_import_record_detail_get_v37_2(staged_record_id: str):
        _, error = _authorized()
        if error:
            return error
        item = find_staged_record_projection(staged_record_id)
        if item is None:
            return jsonify({"error": "staged import record not found"}), 404
        return jsonify(item), 200

    @app.get("/api/v1/operational-import-batches")
    def api_operational_import_batches_get_v37_2():
        _, error = _authorized()
        if error:
            return error
        items = current_batches()
        return jsonify(
            {
                "schema": "socmint.operational_import_batch_inventory.v37_2",
                "version": "v37.2.0",
                "batches": items,
                "count": len(items),
            }
        )

    @app.get("/api/v1/operational-import-batches/<batch_id>")
    def api_operational_import_batch_detail_get_v37_2(batch_id: str):
        _, error = _authorized()
        if error:
            return error
        item = find_batch(batch_id)
        if item is None:
            return jsonify({"error": "staged import batch not found"}), 404
        return jsonify(item), 200

    return app

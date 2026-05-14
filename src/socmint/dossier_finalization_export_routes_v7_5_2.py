from __future__ import annotations

from flask import Response, jsonify, request

from .dossier_finalization_export_v7_5_2 import build_finalization_export_packet
from .dossier_finalization_export_v7_5_2 import build_finalization_export_zip
from .dossier_finalization_export_v7_5_2 import safe_package_name


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _unwrap_request(payload: dict) -> tuple[dict, list[dict] | None, list[dict] | None, str, str | None]:
    if "dossier" in payload and isinstance(payload.get("dossier"), dict):
        dossier = payload.get("dossier") or {}
        connectors = payload.get("connectors") if isinstance(payload.get("connectors"), list) else None
        policy_events = payload.get("policy_events") if isinstance(payload.get("policy_events"), list) else None
        export_mode = str(payload.get("export_mode") or request.args.get("mode") or "final")
        package_name = payload.get("package_name") or request.args.get("package_name")
        return dossier, connectors, policy_events, export_mode, package_name
    return payload, None, None, str(payload.get("export_mode") or request.args.get("mode") or "final"), payload.get("package_name") or request.args.get("package_name")


def register_dossier_finalization_export_routes(app):
    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/export")
    def api_dossier_finalization_export_packet():
        payload = _request_payload()
        dossier, connectors, policy_events, export_mode, package_name = _unwrap_request(payload)
        packet = build_finalization_export_packet(
            dossier,
            connectors=connectors,
            policy_events=policy_events,
            export_mode=export_mode,
            package_name=package_name,
        )
        return jsonify(packet)

    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/export.zip")
    def api_dossier_finalization_export_zip():
        payload = _request_payload()
        dossier, connectors, policy_events, export_mode, package_name = _unwrap_request(payload)
        packet = build_finalization_export_packet(
            dossier,
            connectors=connectors,
            policy_events=policy_events,
            export_mode=export_mode,
            package_name=package_name,
        )
        zip_bytes = build_finalization_export_zip(packet)
        filename = f"{safe_package_name(packet.get('package_name'))}.zip"
        return Response(
            zip_bytes,
            mimetype="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return app

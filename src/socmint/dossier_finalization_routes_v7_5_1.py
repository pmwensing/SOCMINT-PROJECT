from __future__ import annotations

from flask import Response, jsonify, request

from .dossier_finalization_v7_5_1 import build_dossier_finalization_packet
from .dossier_finalization_v7_5_1 import render_finalization_markdown


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _unwrap_request(
    payload: dict,
) -> tuple[dict, list[dict] | None, list[dict] | None, str]:
    if "dossier" in payload and isinstance(payload.get("dossier"), dict):
        dossier = payload.get("dossier") or {}
        connectors = (
            payload.get("connectors")
            if isinstance(payload.get("connectors"), list)
            else None
        )
        policy_events = (
            payload.get("policy_events")
            if isinstance(payload.get("policy_events"), list)
            else None
        )
        export_mode = str(
            payload.get("export_mode") or request.args.get("mode") or "final"
        )
        return dossier, connectors, policy_events, export_mode
    return (
        payload,
        None,
        None,
        str(payload.get("export_mode") or request.args.get("mode") or "final"),
    )


def register_dossier_finalization_routes(app):
    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization")
    def api_dossier_finalization_packet():
        payload = _request_payload()
        dossier, connectors, policy_events, export_mode = _unwrap_request(payload)
        return jsonify(
            build_dossier_finalization_packet(
                dossier,
                connectors=connectors,
                policy_events=policy_events,
                export_mode=export_mode,
            )
        )

    @app.post("/api/v1/dossier-builder/v3/intelligence/finalization/markdown")
    def api_dossier_finalization_markdown():
        payload = _request_payload()
        dossier, connectors, policy_events, export_mode = _unwrap_request(payload)
        packet = build_dossier_finalization_packet(
            dossier,
            connectors=connectors,
            policy_events=policy_events,
            export_mode=export_mode,
        )
        return Response(render_finalization_markdown(packet), mimetype="text/markdown")

    return app

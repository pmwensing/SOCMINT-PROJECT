from __future__ import annotations

from flask import Response, jsonify, request

from .dossier_finalization_closeout_export_bundle_v7_5_11 import (
    build_closeout_export_bundle,
)
from .dossier_finalization_closeout_export_bundle_v7_5_11 import (
    build_closeout_export_zip,
)
from .dossier_finalization_closeout_export_bundle_v7_5_11 import (
    safe_closeout_bundle_name,
)


def _request_payload() -> dict:
    payload = request.get_json(silent=True) or {}
    return payload if isinstance(payload, dict) else {}


def _unwrap_report(payload: dict) -> tuple[dict, str | None]:
    if isinstance(payload.get("report"), dict):
        return payload.get("report") or {}, payload.get("bundle_name")
    return payload, payload.get("bundle_name")


def register_dossier_finalization_closeout_export_bundle_routes(app):
    @app.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export"
    )
    def api_closeout_report_export_bundle():
        payload = _request_payload()
        report, bundle_name = _unwrap_report(payload)
        return jsonify(build_closeout_export_bundle(report, bundle_name=bundle_name))

    @app.post(
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export.zip"
    )
    def api_closeout_report_export_bundle_zip():
        payload = _request_payload()
        report, bundle_name = _unwrap_report(payload)
        bundle = build_closeout_export_bundle(report, bundle_name=bundle_name)
        zip_bytes = build_closeout_export_zip(bundle)
        filename = f"{safe_closeout_bundle_name(bundle.get('bundle_name'))}.zip"
        return Response(
            zip_bytes,
            mimetype="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return app

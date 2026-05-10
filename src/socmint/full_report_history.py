from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Response, jsonify, request

from .entity_dossier_v2 import dossier_root


def _load_export(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    manifest = payload.get("manifest") or {}
    files = manifest.get("files") or []
    roles = {item.get("role"): item for item in files}
    return {
        "name": path.name,
        "path": str(path),
        "generated_at": payload.get("generated_at"),
        "schema": payload.get("schema"),
        "subject_id": payload.get("subject_id"),
        "score": (payload.get("dossier") or {}).get("score") or {},
        "zip_name": Path(payload.get("zip_path") or "").name or None,
        "manifest_name": Path(payload.get("manifest_path") or "").name or None,
        "html_name": Path(payload.get("html_path") or "").name or None,
        "json_name": Path(payload.get("json_path") or "").name or None,
        "markdown_name": Path(payload.get("markdown_path") or "").name or None,
        "artifact_count": manifest.get("artifact_count", len(files)),
        "artifact_roles": sorted(role for role in roles if role),
        "manifest": manifest,
    }


def full_report_export_history(subject_id: int, limit: int = 25) -> dict[str, Any]:
    root = dossier_root()
    pattern = f"subject-{subject_id}-full-entity-dossier-v2-*-EXPORT.json"
    matches = sorted(root.glob(pattern), reverse=True) if root.exists() else []
    exports = []
    for path in matches[:limit]:
        try:
            exports.append(_load_export(path))
        except Exception as exc:
            exports.append({"name": path.name, "path": str(path), "error": str(exc)})
    return {
        "schema": "socmint.full_report_export_history.v7_5_5",
        "subject_id": subject_id,
        "count": len(exports),
        "exports": exports,
    }


def compare_full_report_exports(subject_id: int, left: str | None = None, right: str | None = None) -> dict[str, Any]:
    history = full_report_export_history(subject_id, limit=100)
    exports = history["exports"]
    by_name = {item.get("name"): item for item in exports if item.get("name")}

    if left and right:
        left_export = by_name.get(Path(left).name)
        right_export = by_name.get(Path(right).name)
    elif len(exports) >= 2:
        left_export = exports[1]
        right_export = exports[0]
    else:
        left_export = None
        right_export = None

    if not left_export or not right_export:
        return {
            "schema": "socmint.full_report_export_compare.v7_5_5",
            "subject_id": subject_id,
            "available": False,
            "reason": "At least two exports are required for comparison.",
            "history_count": len(exports),
        }

    left_score = left_export.get("score") or {}
    right_score = right_export.get("score") or {}
    keys = sorted(set(left_score) | set(right_score))
    score_delta = {
        key: {
            "left": left_score.get(key),
            "right": right_score.get(key),
            "delta": (right_score.get(key) or 0) - (left_score.get(key) or 0)
            if isinstance(left_score.get(key, 0), (int, float)) and isinstance(right_score.get(key, 0), (int, float))
            else None,
        }
        for key in keys
    }

    left_roles = set(left_export.get("artifact_roles") or [])
    right_roles = set(right_export.get("artifact_roles") or [])

    return {
        "schema": "socmint.full_report_export_compare.v7_5_5",
        "subject_id": subject_id,
        "available": True,
        "left": left_export,
        "right": right_export,
        "score_delta": score_delta,
        "artifact_role_delta": {
            "added": sorted(right_roles - left_roles),
            "removed": sorted(left_roles - right_roles),
            "unchanged": sorted(left_roles & right_roles),
        },
    }


def _history_html(history: dict[str, Any], compare: dict[str, Any]) -> str:
    subject_id = history["subject_id"]
    rows = []
    for item in history.get("exports", []):
        rows.append(
            "<tr>"
            f"<td><code>{item.get('name', '')}</code></td>"
            f"<td>{item.get('generated_at', '')}</td>"
            f"<td>{item.get('artifact_count', '')}</td>"
            f"<td><code>{item.get('zip_name', '')}</code></td>"
            "</tr>"
        )
    rows_html = "".join(rows) or "<tr><td colspan='4'>No exports found.</td></tr>"

    if compare.get("available"):
        delta_rows = []
        for key, item in (compare.get("score_delta") or {}).items():
            delta_rows.append(
                "<tr>"
                f"<td>{key}</td>"
                f"<td>{item.get('left')}</td>"
                f"<td>{item.get('right')}</td>"
                f"<td>{item.get('delta')}</td>"
                "</tr>"
            )
        compare_html = (
            "<h2>Compare Previous Reports</h2>"
            f"<p><strong>Left:</strong> <code>{compare['left'].get('name')}</code></p>"
            f"<p><strong>Right:</strong> <code>{compare['right'].get('name')}</code></p>"
            "<table border='1' cellpadding='6'><thead><tr><th>Score</th><th>Previous</th><th>Latest</th><th>Delta</th></tr></thead>"
            f"<tbody>{''.join(delta_rows)}</tbody></table>"
        )
    else:
        compare_html = f"<h2>Compare Previous Reports</h2><p>{compare.get('reason')}</p>"

    return f"""
    <!doctype html>
    <html><head><meta charset='utf-8'><title>Full Report History</title></head>
    <body>
      <h1>Full Report Export History — Subject {subject_id}</h1>
      <p><strong>Exports:</strong> {history.get('count')}</p>
      <table border='1' cellpadding='6'>
        <thead><tr><th>Export</th><th>Generated</th><th>Artifacts</th><th>ZIP</th></tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
      {compare_html}
    </body></html>
    """


def register_full_report_history_routes(app) -> None:
    if "api_full_report_history" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_full_report_history(subject_id: int):
        limit = int(request.args.get("limit", 25))
        return jsonify(full_report_export_history(subject_id, limit=limit))

    @login_required
    def api_full_report_compare(subject_id: int):
        return jsonify(
            compare_full_report_exports(
                subject_id,
                left=request.args.get("left"),
                right=request.args.get("right"),
            )
        )

    @login_required
    def ui_full_report_history(subject_id: int):
        history = full_report_export_history(subject_id)
        compare = compare_full_report_exports(subject_id)
        return Response(_history_html(history, compare), mimetype="text/html; charset=utf-8")

    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/full-report/history",
        endpoint="api_full_report_history",
        view_func=api_full_report_history,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/full-report/compare",
        endpoint="api_full_report_compare",
        view_func=api_full_report_compare,
        methods=["GET"],
    )
    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/full-report/history",
        endpoint="ui_full_report_history",
        view_func=ui_full_report_history,
        methods=["GET"],
    )

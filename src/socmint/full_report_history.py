from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from flask import Response, jsonify, request, url_for

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
    try:
        root = dossier_root()
    except OSError as exc:
        return {
            "schema": "socmint.full_report_export_history.v7_5_5",
            "subject_id": subject_id,
            "count": 0,
            "exports": [],
            "available": False,
            "error": str(exc),
        }
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
        "available": True,
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


def _download_url(subject_id: int, name: str | None) -> str:
    return f"/api/v1/spine/subjects/{subject_id}/full-report/download?name={quote(name or '')}"


def _view_url(subject_id: int, name: str | None) -> str:
    return f"/spine/subjects/{subject_id}/full-report/artifact?name={quote(name or '')}"


def _artifact_link(label: str, href: str, primary: bool = False) -> str:
    cls = " class='export-artifact-primary'" if primary else ""
    return f"<a{cls} href='{html.escape(href)}'>{html.escape(label)}</a>"


def _history_html(history: dict[str, Any], compare: dict[str, Any]) -> str:
    subject_id = history["subject_id"]
    cards = []
    for item in history.get("exports", []):
        actions = []
        if item.get("zip_name"):
            actions.append(_artifact_link("Download ZIP", _download_url(subject_id, item.get("zip_name")), True))
        if item.get("manifest_name"):
            actions.append(_artifact_link("Download Manifest", _download_url(subject_id, item.get("manifest_name"))))
            actions.append(_artifact_link("View Manifest", _view_url(subject_id, item.get("manifest_name"))))
        if item.get("html_name"):
            actions.append(_artifact_link("Open HTML", _view_url(subject_id, item.get("html_name"))))
        if item.get("json_name"):
            actions.append(_artifact_link("View JSON", _view_url(subject_id, item.get("json_name"))))
        if item.get("markdown_name"):
            actions.append(_artifact_link("View Markdown", _view_url(subject_id, item.get("markdown_name"))))
        cards.append(
            "<article class='export-artifact-card'>"
            f"<span>Export result</span><strong>{html.escape(str(item.get('name') or ''))}</strong>"
            f"<p>Generated: {html.escape(str(item.get('generated_at') or ''))}</p>"
            f"<p>Artifacts: {html.escape(str(item.get('artifact_count') or 0))}</p>"
            f"<code>{html.escape(str(item.get('zip_name') or 'No ZIP artifact'))}</code>"
            f"<div class='export-artifact-actions'>{''.join(actions)}</div>"
            "</article>"
        )
    cards_html = "".join(cards) or "<p>No exports yet.</p>"
    compare_block = ""
    if compare.get("available"):
        compare_block = f"<pre>{html.escape(json.dumps(compare, indent=2))}</pre>"
    else:
        compare_block = f"<p><strong>Comparison:</strong> {html.escape(str(compare.get('reason') or 'Unavailable'))}</p>"
    return f"""
    <!doctype html>
    <html><head><meta charset='utf-8'><title>Full Report Export History</title>
      <link rel='stylesheet' href='/static/runtime_visual.css'>
    </head>
    <body class='runtime-utility-page'>
      <main class='runtime-utility-container'>
        <section class='runtime-utility-card'>
          <h1>Full Report Export History — Subject {subject_id}</h1>
          <div class='export-summary-list'>
            <div><span>Exports</span><strong>{history.get('count', 0)}</strong></div>
            <div><span>History API</span><code>{html.escape(history.get('schema', ''))}</code></div>
          </div>
          <div class='runtime-utility-actions'>
            <a href='{url_for('ui_full_report_view_panel', subject_id=subject_id)}'>Export Panel</a>
            <a href='{url_for('ui_full_report_retention', subject_id=subject_id)}'>Retention / Pins</a>
            <a href='{url_for('dashboard.subject_dossier_v2', subject_id=subject_id)}'>Full Dossier v2</a>
          </div>
        </section>
        <section class='runtime-utility-card'>
          <h2>Export Artifact Cards</h2>
          <div class='export-artifact-grid'>{cards_html}</div>
        </section>
        <section class='runtime-utility-card'>
          <h2>Comparison</h2>
          {compare_block}
        </section>
      </main>
    </body></html>
    """


def register_full_report_history_routes(app) -> None:
    if "api_full_report_history" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_full_report_history(subject_id: int):
        return jsonify(full_report_export_history(subject_id))

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
    def full_report_history_page(subject_id: int):
        history = full_report_export_history(subject_id, limit=100)
        compare = compare_full_report_exports(
            subject_id,
            left=request.args.get("left"),
            right=request.args.get("right"),
        )
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
        endpoint="full_report_history_page",
        view_func=full_report_history_page,
        methods=["GET"],
    )
    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/full-report/history",
        endpoint="ui_full_report_history",
        view_func=full_report_history_page,
        methods=["GET"],
    )

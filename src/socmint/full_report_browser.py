from __future__ import annotations

import html
from urllib.parse import quote

from flask import Response, redirect, request, url_for

from .entity_dossier_v2 import safe_dossier_path
from .full_report_alias import latest_full_report_export

VIEW_MIMETYPES = {
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}

ROLE_LABELS = {
    "zip_bundle": "ZIP Bundle",
    "export_manifest": "Manifest",
    "dossier_html": "HTML Report",
    "dossier_json": "JSON",
    "dossier_markdown": "Markdown",
}


def _view_artifact(name: str) -> Response:
    path = safe_dossier_path(name)
    mimetype = VIEW_MIMETYPES.get(path.suffix.lower(), "text/plain; charset=utf-8")
    return Response(path.read_text(errors="replace"), mimetype=mimetype)


def _download_url(subject_id: int, name: str) -> str:
    return (
        f"/api/v1/spine/subjects/{subject_id}/full-report/download?name={quote(name)}"
    )


def _view_url(subject_id: int, name: str) -> str:
    return f"/spine/subjects/{subject_id}/full-report/artifact?name={quote(name)}"


def _artifact_cards(subject_id: int, files: list[dict]) -> str:
    cards = []
    for item in files:
        name = str(item.get("name") or "")
        role = str(item.get("role") or "artifact")
        suffix = name.rsplit(".", 1)[-1].lower() if "." in name else "artifact"
        label = ROLE_LABELS.get(role, role.replace("_", " ").title())
        actions = [
            f"<a class='export-artifact-primary' href='{_download_url(subject_id, name)}'>Download {html.escape(label)}</a>"
        ]
        if suffix in {"html", "json", "md", "txt"}:
            action_label = (
                "Open HTML"
                if suffix == "html"
                else f"View {suffix.upper() if suffix != 'md' else 'Markdown'}"
            )
            actions.append(
                f"<a href='{_view_url(subject_id, name)}'>{html.escape(action_label)}</a>"
            )
        cards.append(
            "<article class='export-artifact-card'>"
            f"<span>{html.escape(label)}</span>"
            f"<strong>{html.escape(name)}</strong>"
            f"<p>Size: {html.escape(str(item.get('size_bytes', '')))} bytes</p>"
            f"<code>sha256:{html.escape(str(item.get('sha256', '')))}</code>"
            f"<div class='export-artifact-actions'>{''.join(actions)}</div>"
            "</article>"
        )
    return "".join(cards) or "<p>No manifest artifacts are available.</p>"


def _status_panel(subject_id: int, latest: dict) -> Response:
    if latest.get("available"):
        files = (latest.get("manifest") or {}).get("files", [])
        artifact_cards = _artifact_cards(subject_id, files)
        history_url = url_for("ui_full_report_history", subject_id=subject_id)
        retention_url = url_for("ui_full_report_retention", subject_id=subject_id)
        dossier_url = f"/spine/subjects/{subject_id}/dossier"
        html_name = latest.get("html_name")
        open_html = (
            f"<a class='export-artifact-primary' href='{url_for('ui_full_report_open_latest', subject_id=subject_id)}'>Open HTML Report</a>"
            if html_name
            else ""
        )
        html_page = f"""
        <!doctype html>
        <html><head><meta charset='utf-8'><title>Full Report Export</title>
          <link rel='stylesheet' href='/static/runtime_visual.css'>
        </head>
        <body class='runtime-utility-page'>
          <main class='runtime-utility-container'>
            <section class='runtime-utility-card'>
              <h1>Full Report Export — Subject {subject_id}</h1>
              <div class='export-summary-list'>
                <div><span>Generated</span><strong>{html.escape(str(latest.get("generated_at") or ""))}</strong></div>
                <div><span>Schema</span><code>{html.escape(str(latest.get("schema") or ""))}</code></div>
                <div><span>Artifacts</span><strong>{html.escape(str((latest.get("manifest") or {}).get("artifact_count", len(files))))}</strong></div>
                <div><span>Result</span><code>{html.escape(str(latest.get("result_name") or ""))}</code></div>
              </div>
              <div class='runtime-utility-actions'>{open_html}<a href='{history_url}'>Export History</a><a href='{retention_url}'>Retention / Pins</a><a href='{dossier_url}'>Full Dossier v2</a></div>
            </section>
            <section class='runtime-utility-card'>
              <h2>Export Artifacts</h2>
              <div class='export-artifact-grid'>{artifact_cards}</div>
            </section>
          </main>
        </body></html>
        """
    else:
        html_page = f"""
        <!doctype html>
        <html><head><meta charset='utf-8'><title>Full Report Export</title>
          <link rel='stylesheet' href='/static/runtime_visual.css'>
        </head>
        <body class='runtime-utility-page'>
          <main class='runtime-utility-container'>
            <section class='runtime-utility-card'>
              <h1>Full Report Export — Subject {subject_id}</h1>
              <p>No full-report export is available yet.</p>
              <p>Run Full Report from the Full Dossier v2 page to create ZIP, Manifest, HTML, Markdown, and JSON artifacts.</p>
            </section>
          </main>
        </body></html>
        """
    return Response(html_page, mimetype="text/html; charset=utf-8")


def register_full_report_browser_flow(app) -> None:
    if "ui_full_report_view_panel" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def ui_full_report_view_panel(subject_id: int):
        return _status_panel(subject_id, latest_full_report_export(subject_id))

    @login_required
    def ui_full_report_open_latest(subject_id: int):
        latest = latest_full_report_export(subject_id)
        if not latest.get("available") or not latest.get("html_name"):
            return _status_panel(subject_id, latest), 404
        return redirect(
            url_for(
                "ui_full_report_view_artifact",
                subject_id=subject_id,
                name=latest["html_name"],
            )
        )

    @login_required
    def ui_full_report_view_artifact(subject_id: int):
        name = request.args.get("name", "").strip()
        if not name:
            return Response(
                "name query parameter is required", status=400, mimetype="text/plain"
            )
        return _view_artifact(name)

    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/full-report/view",
        endpoint="ui_full_report_view_panel",
        view_func=ui_full_report_view_panel,
        methods=["GET"],
    )
    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/full-report/open",
        endpoint="ui_full_report_open_latest",
        view_func=ui_full_report_open_latest,
        methods=["GET"],
    )
    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/full-report/artifact",
        endpoint="ui_full_report_view_artifact",
        view_func=ui_full_report_view_artifact,
        methods=["GET"],
    )

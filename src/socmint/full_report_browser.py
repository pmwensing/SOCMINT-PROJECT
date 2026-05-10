from __future__ import annotations

from flask import Response, redirect, request, url_for

from .entity_dossier_v2 import safe_dossier_path
from .full_report_alias import latest_full_report_export

VIEW_MIMETYPES = {
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}


def _view_artifact(name: str) -> Response:
    path = safe_dossier_path(name)
    mimetype = VIEW_MIMETYPES.get(path.suffix.lower(), "text/plain; charset=utf-8")
    return Response(path.read_text(errors="replace"), mimetype=mimetype)


def _status_panel(subject_id: int, latest: dict) -> Response:
    if latest.get("available"):
        rows = []
        for item in (latest.get("manifest") or {}).get("files", []):
            rows.append(
                "<tr>"
                f"<td>{item.get('role', '')}</td>"
                f"<td><code>{item.get('name', '')}</code></td>"
                f"<td>{item.get('size_bytes', '')}</td>"
                f"<td><code>{item.get('sha256', '')}</code></td>"
                "</tr>"
            )
        body = "".join(rows) or "<tr><td colspan='4'>No manifest rows.</td></tr>"
        html = f"""
        <!doctype html>
        <html><head><meta charset='utf-8'><title>Full Report Export</title></head>
        <body>
          <h1>Full Report Export — Subject {subject_id}</h1>
          <p><strong>Generated:</strong> {latest.get('generated_at')}</p>
          <p><strong>Schema:</strong> <code>{latest.get('schema')}</code></p>
          <p><a href='/spine/subjects/{subject_id}/full-report/open'>Open latest HTML report</a></p>
          <p><a href='/api/v1/spine/subjects/{subject_id}/full-report/download?name={latest.get('zip_name')}'>Download ZIP</a></p>
          <p><a href='/api/v1/spine/subjects/{subject_id}/full-report/download?name={latest.get('manifest_name')}'>Download Manifest</a></p>
          <h2>Manifest</h2>
          <table border='1' cellpadding='6'>
            <thead><tr><th>Role</th><th>Name</th><th>Size</th><th>SHA-256</th></tr></thead>
            <tbody>{body}</tbody>
          </table>
        </body></html>
        """
    else:
        html = f"""
        <!doctype html>
        <html><head><meta charset='utf-8'><title>Full Report Export</title></head>
        <body>
          <h1>Full Report Export — Subject {subject_id}</h1>
          <p>No full-report export is available yet.</p>
        </body></html>
        """
    return Response(html, mimetype="text/html; charset=utf-8")


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
        return redirect(url_for("ui_full_report_view_artifact", subject_id=subject_id, name=latest["html_name"]))

    @login_required
    def ui_full_report_view_artifact(subject_id: int):
        name = request.args.get("name", "").strip()
        if not name:
            return Response("name query parameter is required", status=400, mimetype="text/plain")
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

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Response, jsonify, request

from .entity_dossier_v2 import dossier_root
from .entity_dossier_v2 import safe_dossier_path
from .full_report_history import full_report_export_history

PIN_SCHEMA = "socmint.full_report_retention_pins.v7_5_6"
RETENTION_SCHEMA = "socmint.full_report_retention.v7_5_6"


def pin_store_path() -> Path:
    root = dossier_root()
    path = root / "full_report_pins_v7_5_6.json"
    if not path.exists():
        path.write_text(json.dumps({"schema": PIN_SCHEMA, "pins": {}}, indent=2, sort_keys=True))
    return path


def load_pins() -> dict[str, Any]:
    path = pin_store_path()
    try:
        payload = json.loads(path.read_text())
    except Exception:
        payload = {"schema": PIN_SCHEMA, "pins": {}}
    payload.setdefault("schema", PIN_SCHEMA)
    payload.setdefault("pins", {})
    return payload


def save_pins(payload: dict[str, Any]) -> dict[str, Any]:
    payload.setdefault("schema", PIN_SCHEMA)
    payload.setdefault("pins", {})
    pin_store_path().write_text(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def pin_export(subject_id: int, export_name: str, note: str = "") -> dict[str, Any]:
    export_name = Path(export_name).name
    history = full_report_export_history(subject_id, limit=250)
    names = {item.get("name") for item in history.get("exports", [])}
    if export_name not in names:
        return {"ok": False, "error": "export_not_found", "subject_id": subject_id, "export_name": export_name}
    payload = load_pins()
    subject_key = str(subject_id)
    payload["pins"].setdefault(subject_key, {})
    payload["pins"][subject_key][export_name] = {"note": note, "pinned": True}
    save_pins(payload)
    return {"ok": True, "subject_id": subject_id, "export_name": export_name, "pinned": True}


def unpin_export(subject_id: int, export_name: str) -> dict[str, Any]:
    export_name = Path(export_name).name
    payload = load_pins()
    subject_key = str(subject_id)
    if subject_key in payload.get("pins", {}):
        payload["pins"][subject_key].pop(export_name, None)
    save_pins(payload)
    return {"ok": True, "subject_id": subject_id, "export_name": export_name, "pinned": False}


def pinned_export_names(subject_id: int) -> set[str]:
    payload = load_pins()
    return set((payload.get("pins", {}).get(str(subject_id), {}) or {}).keys())


def retention_plan(subject_id: int, keep_latest: int = 5) -> dict[str, Any]:
    history = full_report_export_history(subject_id, limit=500)
    pins = pinned_export_names(subject_id)
    exports = history.get("exports", [])
    keep = []
    delete = []
    for idx, item in enumerate(exports):
        name = item.get("name")
        pinned = name in pins
        item = {**item, "pinned": pinned}
        if pinned or idx < keep_latest:
            keep.append(item)
        else:
            delete.append(item)
    return {
        "schema": RETENTION_SCHEMA,
        "subject_id": subject_id,
        "keep_latest": keep_latest,
        "pinned_count": len(pins),
        "history_count": len(exports),
        "keep_count": len(keep),
        "delete_count": len(delete),
        "keep": keep,
        "delete": delete,
    }


def _artifact_names_for_export(export: dict[str, Any]) -> set[str]:
    names = {Path(export.get("name") or "").name}
    for key in ("zip_name", "manifest_name", "html_name", "json_name", "markdown_name"):
        if export.get(key):
            names.add(Path(export[key]).name)
    for item in (export.get("manifest") or {}).get("files", []) or []:
        if item.get("name"):
            names.add(Path(item["name"]).name)
        elif item.get("path"):
            names.add(Path(item["path"]).name)
    return {name for name in names if name}


def delete_export(subject_id: int, export_name: str, force: bool = False) -> dict[str, Any]:
    export_name = Path(export_name).name
    pins = pinned_export_names(subject_id)
    if export_name in pins and not force:
        return {"ok": False, "error": "export_pinned", "subject_id": subject_id, "export_name": export_name}

    history = full_report_export_history(subject_id, limit=500)
    export = next((item for item in history.get("exports", []) if item.get("name") == export_name), None)
    if not export:
        return {"ok": False, "error": "export_not_found", "subject_id": subject_id, "export_name": export_name}

    root = dossier_root().resolve()
    deleted = []
    missing = []
    for name in sorted(_artifact_names_for_export(export)):
        try:
            path = safe_dossier_path(name)
        except FileNotFoundError:
            missing.append(name)
            continue
        if root not in path.resolve().parents and path.resolve() != root:
            continue
        path.unlink()
        deleted.append(name)

    if export_name in pins:
        unpin_export(subject_id, export_name)

    return {
        "ok": True,
        "subject_id": subject_id,
        "export_name": export_name,
        "deleted": deleted,
        "missing": missing,
        "deleted_count": len(deleted),
    }


def apply_retention(subject_id: int, keep_latest: int = 5, dry_run: bool = True) -> dict[str, Any]:
    plan = retention_plan(subject_id, keep_latest=keep_latest)
    if dry_run:
        return {**plan, "dry_run": True, "deleted": []}
    deleted = []
    blocked = []
    for item in plan.get("delete", []):
        result = delete_export(subject_id, item["name"], force=False)
        if result.get("ok"):
            deleted.append(result)
        else:
            blocked.append(result)
    return {**plan, "dry_run": False, "deleted": deleted, "blocked": blocked}


def _retention_html(subject_id: int) -> str:
    plan = retention_plan(subject_id)
    delete_rows = []
    for item in plan.get("delete", []):
        delete_rows.append(
            "<tr>"
            f"<td><code>{item.get('name')}</code></td>"
            f"<td>{item.get('generated_at')}</td>"
            f"<td>{item.get('artifact_count')}</td>"
            "</tr>"
        )
    keep_rows = []
    for item in plan.get("keep", []):
        keep_rows.append(
            "<tr>"
            f"<td><code>{item.get('name')}</code></td>"
            f"<td>{item.get('generated_at')}</td>"
            f"<td>{'yes' if item.get('pinned') else 'no'}</td>"
            "</tr>"
        )
    return f"""
    <!doctype html><html><head><meta charset='utf-8'><title>Full Report Retention</title></head>
    <body>
      <h1>Full Report Retention — Subject {subject_id}</h1>
      <p><strong>History:</strong> {plan['history_count']} | <strong>Keep:</strong> {plan['keep_count']} | <strong>Delete candidates:</strong> {plan['delete_count']}</p>
      <h2>Kept / Pinned Exports</h2>
      <table border='1' cellpadding='6'><thead><tr><th>Export</th><th>Generated</th><th>Pinned</th></tr></thead><tbody>{''.join(keep_rows) or '<tr><td colspan="3">No kept exports.</td></tr>'}</tbody></table>
      <h2>Delete Candidates</h2>
      <table border='1' cellpadding='6'><thead><tr><th>Export</th><th>Generated</th><th>Artifacts</th></tr></thead><tbody>{''.join(delete_rows) or '<tr><td colspan="3">No delete candidates.</td></tr>'}</tbody></table>
    </body></html>
    """


def register_full_report_retention_routes(app) -> None:
    if "api_full_report_retention_plan" in app.view_functions:
        return

    from .dashboard import login_required, run_required

    @login_required
    def api_full_report_retention_plan(subject_id: int):
        keep_latest = int(request.args.get("keep_latest", 5))
        return jsonify(retention_plan(subject_id, keep_latest=keep_latest))

    @run_required
    def api_full_report_pin(subject_id: int):
        payload = request.get_json(silent=True) or request.form or {}
        return jsonify(pin_export(subject_id, payload.get("name", ""), note=payload.get("note", "")))

    @run_required
    def api_full_report_unpin(subject_id: int):
        payload = request.get_json(silent=True) or request.form or {}
        return jsonify(unpin_export(subject_id, payload.get("name", "")))

    @run_required
    def api_full_report_delete(subject_id: int):
        payload = request.get_json(silent=True) or request.form or {}
        force = str(payload.get("force", "false")).lower() in {"1", "true", "yes"}
        result = delete_export(subject_id, payload.get("name", ""), force=force)
        return jsonify(result), 200 if result.get("ok") else 409

    @run_required
    def api_full_report_apply_retention(subject_id: int):
        payload = request.get_json(silent=True) or request.form or {}
        keep_latest = int(payload.get("keep_latest", 5))
        dry_run = str(payload.get("dry_run", "true")).lower() not in {"0", "false", "no"}
        return jsonify(apply_retention(subject_id, keep_latest=keep_latest, dry_run=dry_run))

    @login_required
    def ui_full_report_retention(subject_id: int):
        return Response(_retention_html(subject_id), mimetype="text/html; charset=utf-8")

    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/full-report/retention", endpoint="api_full_report_retention_plan", view_func=api_full_report_retention_plan, methods=["GET"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/full-report/pin", endpoint="api_full_report_pin", view_func=api_full_report_pin, methods=["POST"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/full-report/unpin", endpoint="api_full_report_unpin", view_func=api_full_report_unpin, methods=["POST"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/full-report/delete", endpoint="api_full_report_delete", view_func=api_full_report_delete, methods=["POST"])
    app.add_url_rule("/api/v1/spine/subjects/<int:subject_id>/full-report/apply-retention", endpoint="api_full_report_apply_retention", view_func=api_full_report_apply_retention, methods=["POST"])
    app.add_url_rule("/spine/subjects/<int:subject_id>/full-report/retention", endpoint="ui_full_report_retention", view_func=ui_full_report_retention, methods=["GET"])

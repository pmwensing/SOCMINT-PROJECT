from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from flask import Response, jsonify, redirect, request, url_for

from .entity_dossier_v2 import dossier_root
from .entity_dossier_v2 import safe_dossier_path
from .full_report_history import full_report_export_history

PIN_SCHEMA = "socmint.full_report_retention_pins.v7_5_6"
RETENTION_SCHEMA = "socmint.full_report_retention.v7_5_6"


def pin_store_path() -> Path:
    root = dossier_root()
    path = root / "full_report_pins_v7_5_6.json"
    if not path.exists():
        path.write_text(
            json.dumps({"schema": PIN_SCHEMA, "pins": {}}, indent=2, sort_keys=True)
        )
    return path


def load_pins() -> dict[str, Any]:
    try:
        path = pin_store_path()
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
        return {
            "ok": False,
            "error": "export_not_found",
            "subject_id": subject_id,
            "export_name": export_name,
        }
    payload = load_pins()
    subject_key = str(subject_id)
    payload["pins"].setdefault(subject_key, {})
    payload["pins"][subject_key][export_name] = {"note": note, "pinned": True}
    save_pins(payload)
    return {
        "ok": True,
        "subject_id": subject_id,
        "export_name": export_name,
        "pinned": True,
    }


def unpin_export(subject_id: int, export_name: str) -> dict[str, Any]:
    export_name = Path(export_name).name
    payload = load_pins()
    subject_key = str(subject_id)
    if subject_key in payload.get("pins", {}):
        payload["pins"][subject_key].pop(export_name, None)
    save_pins(payload)
    return {
        "ok": True,
        "subject_id": subject_id,
        "export_name": export_name,
        "pinned": False,
    }


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


def delete_export(
    subject_id: int, export_name: str, force: bool = False
) -> dict[str, Any]:
    export_name = Path(export_name).name
    pins = pinned_export_names(subject_id)
    if export_name in pins and not force:
        return {
            "ok": False,
            "error": "export_pinned",
            "subject_id": subject_id,
            "export_name": export_name,
        }

    history = full_report_export_history(subject_id, limit=500)
    export = next(
        (
            item
            for item in history.get("exports", [])
            if item.get("name") == export_name
        ),
        None,
    )
    if not export:
        return {
            "ok": False,
            "error": "export_not_found",
            "subject_id": subject_id,
            "export_name": export_name,
        }

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


def apply_retention(
    subject_id: int, keep_latest: int = 5, dry_run: bool = True
) -> dict[str, Any]:
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


def _csrf_input() -> str:
    from .dashboard import csrf_token

    return (
        f"<input type='hidden' name='csrf_token' value='{html.escape(csrf_token())}'>"
    )


def _hidden(name: str, value: Any) -> str:
    return f"<input type='hidden' name='{html.escape(name)}' value='{html.escape(str(value or ''))}'>"


def _button(label: str, danger: bool = False) -> str:
    cls = " style='background:#7f1d1d;color:white'" if danger else ""
    return f"<button type='submit'{cls}>{html.escape(label)}</button>"


def _form(
    action: str,
    fields: dict[str, Any],
    label: str,
    *,
    danger: bool = False,
    extra: str = "",
) -> str:
    inputs = [_csrf_input()]
    inputs.extend(_hidden(key, value) for key, value in fields.items())
    return (
        f"<form method='post' action='{html.escape(action)}' style='display:inline-block;margin:0.15rem'>"
        + "".join(inputs)
        + extra
        + _button(label, danger=danger)
        + "</form>"
    )


def _int_request_arg(name: str, default: int) -> int:
    try:
        return max(1, int(request.values.get(name, default)))
    except (TypeError, ValueError):
        return default


def _retention_html(subject_id: int, keep_latest: int = 5, message: str = "") -> str:
    plan = retention_plan(subject_id, keep_latest=keep_latest)
    pin_action = url_for("ui_full_report_pin", subject_id=subject_id)
    unpin_action = url_for("ui_full_report_unpin", subject_id=subject_id)
    delete_action = url_for("ui_full_report_delete", subject_id=subject_id)
    apply_action = url_for("ui_full_report_apply_retention", subject_id=subject_id)
    retention_url = url_for("ui_full_report_retention", subject_id=subject_id)
    history_url = url_for("ui_full_report_history", subject_id=subject_id)

    keep_rows = []
    for item in plan.get("keep", []):
        name = item.get("name", "")
        pinned = bool(item.get("pinned"))
        pin_controls = (
            _form(unpin_action, {"name": name, "keep_latest": keep_latest}, "Unpin")
            if pinned
            else _form(
                pin_action,
                {
                    "name": name,
                    "note": "Pinned from retention UI",
                    "keep_latest": keep_latest,
                },
                "Pin important",
            )
        )
        delete_extra = (
            f"<label> Confirm: <input name='confirm_name' size='34' "
            f"placeholder='{html.escape(name)}'></label>"
        )
        delete_control = _form(
            delete_action,
            {"name": name, "keep_latest": keep_latest},
            "Delete export",
            danger=True,
            extra=delete_extra,
        )
        keep_rows.append(
            "<tr>"
            f"<td><code>{html.escape(name)}</code></td>"
            f"<td>{html.escape(str(item.get('generated_at') or ''))}</td>"
            f"<td>{'yes' if pinned else 'no'}</td>"
            f"<td>{pin_controls}{delete_control}</td>"
            "</tr>"
        )

    delete_rows = []
    for item in plan.get("delete", []):
        name = item.get("name", "")
        delete_extra = (
            f"<label> Confirm: <input name='confirm_name' size='34' "
            f"placeholder='{html.escape(name)}'></label>"
        )
        controls = _form(
            pin_action,
            {
                "name": name,
                "note": "Pinned from delete candidates",
                "keep_latest": keep_latest,
            },
            "Pin important",
        ) + _form(
            delete_action,
            {"name": name, "keep_latest": keep_latest},
            "Delete export",
            danger=True,
            extra=delete_extra,
        )
        delete_rows.append(
            "<tr>"
            f"<td><code>{html.escape(name)}</code></td>"
            f"<td>{html.escape(str(item.get('generated_at') or ''))}</td>"
            f"<td>{html.escape(str(item.get('artifact_count') or ''))}</td>"
            f"<td>{controls}</td>"
            "</tr>"
        )

    dry_run_form = _form(
        apply_action,
        {"keep_latest": keep_latest, "dry_run": "true"},
        "Dry-run retention",
    )
    apply_form = _form(
        apply_action,
        {"keep_latest": keep_latest, "dry_run": "false"},
        "Apply retention delete candidates",
        danger=True,
        extra="<label> Confirm apply: <input name='confirm_apply' placeholder='APPLY'></label>",
    )

    message_html = (
        f"<p><strong>Status:</strong> {html.escape(message)}</p>" if message else ""
    )
    return f"""
    <!doctype html>
    <html><head><meta charset='utf-8'><title>Full Report Retention</title>
      <link rel='stylesheet' href='/static/runtime_visual.css'>
    </head>
    <body class='runtime-utility-page'>
      <main class='runtime-utility-container'>
        <section class='runtime-utility-card'>
          <h1>Full Report Retention — Subject {subject_id}</h1>
          {message_html}
          <div class='runtime-utility-actions'><a href='{history_url}'>Export History</a><a href='{retention_url}'>Refresh Retention</a></div>
        </section>
        <section class='runtime-utility-card'>
          <form method='get' action='{retention_url}'>
            <label>Keep latest <input type='number' min='1' name='keep_latest' value='{keep_latest}'></label>
            <button type='submit'>Recalculate retention</button>
          </form>
          <p><strong>History:</strong> {plan["history_count"]} | <strong>Keep:</strong> {plan["keep_count"]} | <strong>Delete candidates:</strong> {plan["delete_count"]} | <strong>Pinned:</strong> {plan["pinned_count"]}</p>
        </section>
        <section class='runtime-utility-card'>
          <h2>Retention Actions</h2>
          <div class='runtime-utility-actions'>{dry_run_form}{apply_form}</div>
        </section>
        <section class='runtime-utility-card runtime-table-wrap'>
          <h2>Kept / Pinned Exports</h2>
          <table><thead><tr><th>Export</th><th>Generated</th><th>Pinned</th><th>Actions</th></tr></thead><tbody>{"".join(keep_rows) or '<tr><td colspan="4">No kept exports.</td></tr>'}</tbody></table>
        </section>
        <section class='runtime-utility-card runtime-table-wrap'>
          <h2>Delete Candidates</h2>
          <table><thead><tr><th>Export</th><th>Generated</th><th>Artifacts</th><th>Actions</th></tr></thead><tbody>{"".join(delete_rows) or '<tr><td colspan="4">No delete candidates.</td></tr>'}</tbody></table>
          <p><strong>Delete safety:</strong> type the exact export filename into the Confirm field before deleting. Pinned exports are blocked unless force is used by API.</p>
        </section>
      </main>
    </body></html>
    """


def register_full_report_retention_routes(app) -> None:
    if "api_full_report_retention_plan" in app.view_functions:
        return

    from .dashboard import login_required, run_required

    def _keep_latest_from_request(default: int = 5) -> int:
        return _int_request_arg("keep_latest", default)

    @login_required
    def api_full_report_retention_plan(subject_id: int):
        keep_latest = _keep_latest_from_request(5)
        return jsonify(retention_plan(subject_id, keep_latest=keep_latest))

    @run_required
    def api_full_report_pin(subject_id: int):
        payload = request.get_json(silent=True) or request.form or {}
        return jsonify(
            pin_export(
                subject_id, payload.get("name", ""), note=payload.get("note", "")
            )
        )

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
        try:
            keep_latest = max(1, int(payload.get("keep_latest", 5)))
        except (TypeError, ValueError):
            keep_latest = 5
        dry_run = str(payload.get("dry_run", "true")).lower() not in {
            "0",
            "false",
            "no",
        }
        return jsonify(
            apply_retention(subject_id, keep_latest=keep_latest, dry_run=dry_run)
        )

    @login_required
    def ui_full_report_retention(subject_id: int):
        keep_latest = _keep_latest_from_request(5)
        message = request.args.get("message", "")
        return Response(
            _retention_html(subject_id, keep_latest=keep_latest, message=message),
            mimetype="text/html; charset=utf-8",
        )

    @run_required
    def ui_full_report_pin(subject_id: int):
        keep_latest = _keep_latest_from_request()
        result = pin_export(
            subject_id, request.form.get("name", ""), note=request.form.get("note", "")
        )
        message = (
            "Pinned export."
            if result.get("ok")
            else f"Pin failed: {result.get('error')}"
        )
        return redirect(
            url_for(
                "ui_full_report_retention",
                subject_id=subject_id,
                keep_latest=keep_latest,
                message=message,
            )
        )

    @run_required
    def ui_full_report_unpin(subject_id: int):
        keep_latest = _keep_latest_from_request()
        unpin_export(subject_id, request.form.get("name", ""))
        return redirect(
            url_for(
                "ui_full_report_retention",
                subject_id=subject_id,
                keep_latest=keep_latest,
                message="Unpinned export.",
            )
        )

    @run_required
    def ui_full_report_delete(subject_id: int):
        keep_latest = _keep_latest_from_request()
        name = Path(request.form.get("name", "")).name
        confirm = request.form.get("confirm_name", "")
        if confirm != name:
            return redirect(
                url_for(
                    "ui_full_report_retention",
                    subject_id=subject_id,
                    keep_latest=keep_latest,
                    message="Delete blocked: confirmation did not match export filename.",
                )
            )
        result = delete_export(subject_id, name, force=False)
        message = (
            f"Deleted {result.get('deleted_count', 0)} artifact(s)."
            if result.get("ok")
            else f"Delete blocked: {result.get('error')}"
        )
        return redirect(
            url_for(
                "ui_full_report_retention",
                subject_id=subject_id,
                keep_latest=keep_latest,
                message=message,
            )
        )

    @run_required
    def ui_full_report_apply_retention(subject_id: int):
        keep_latest = _keep_latest_from_request()
        dry_run = str(request.form.get("dry_run", "true")).lower() not in {
            "0",
            "false",
            "no",
        }
        if not dry_run and request.form.get("confirm_apply") != "APPLY":
            return redirect(
                url_for(
                    "ui_full_report_retention",
                    subject_id=subject_id,
                    keep_latest=keep_latest,
                    message="Apply blocked: type APPLY to confirm deletion.",
                )
            )
        result = apply_retention(subject_id, keep_latest=keep_latest, dry_run=dry_run)
        message = (
            f"Dry-run complete: {result.get('delete_count', 0)} delete candidate(s)."
            if dry_run
            else f"Applied retention: {len(result.get('deleted', []))} export(s) deleted."
        )
        return redirect(
            url_for(
                "ui_full_report_retention",
                subject_id=subject_id,
                keep_latest=keep_latest,
                message=message,
            )
        )

    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/full-report/retention",
        endpoint="api_full_report_retention_plan",
        view_func=api_full_report_retention_plan,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/full-report/pin",
        endpoint="api_full_report_pin",
        view_func=api_full_report_pin,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/full-report/unpin",
        endpoint="api_full_report_unpin",
        view_func=api_full_report_unpin,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/full-report/delete",
        endpoint="api_full_report_delete",
        view_func=api_full_report_delete,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/spine/subjects/<int:subject_id>/full-report/apply-retention",
        endpoint="api_full_report_apply_retention",
        view_func=api_full_report_apply_retention,
        methods=["POST"],
    )
    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/full-report/retention",
        endpoint="ui_full_report_retention",
        view_func=ui_full_report_retention,
        methods=["GET"],
    )
    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/full-report/pin",
        endpoint="ui_full_report_pin",
        view_func=ui_full_report_pin,
        methods=["POST"],
    )
    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/full-report/unpin",
        endpoint="ui_full_report_unpin",
        view_func=ui_full_report_unpin,
        methods=["POST"],
    )
    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/full-report/delete",
        endpoint="ui_full_report_delete",
        view_func=ui_full_report_delete,
        methods=["POST"],
    )
    app.add_url_rule(
        "/spine/subjects/<int:subject_id>/full-report/apply-retention",
        endpoint="ui_full_report_apply_retention",
        view_func=ui_full_report_apply_retention,
        methods=["POST"],
    )

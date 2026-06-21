from __future__ import annotations

import html
import json
import os
import platform
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import Response, jsonify, send_file

from .config import load_settings
from .entity_dossier_v2 import dossier_root
from .full_report_alias import latest_full_report_export
from .full_report_history import full_report_export_history

SUPPORT_BUNDLE_SCHEMA = "socmint.support_bundle.v13_34"
SUPPORT_BUNDLE_VERSION = "v13.34"
SUPPORT_BUNDLE_ROUTES = [
    "/command-center",
    "/review/normalization-queue",
    "/subjects/4/dossier/readiness",
    "/subjects/4/claim-evidence-ledger",
    "/spine/subjects/4/dossier",
    "/spine/subjects/4/full-report/history",
    "/spine/subjects/4/full-report/view",
    "/spine/subjects/4/full-report/retention",
    "/release/final-rc/v13.33",
    "/api/v1/dossier-builder/v3/export-blockers/screenshot-manifest",
    "/dossier/export-blockers/screenshot-manifest/download",
]
SECRET_MARKERS = ("PASSWORD", "SECRET", "TOKEN", "KEY", "PASSPHRASE", "INVITE")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def support_bundle_root() -> Path:
    settings = load_settings(require_secret=False)
    root = Path(settings.data_dir) / "support_bundles"
    root.mkdir(parents=True, exist_ok=True)
    return root


def redact_value(name: str, value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    if any(marker in name.upper() for marker in SECRET_MARKERS):
        if not text:
            return ""
        return f"<redacted:{len(text)} chars>"
    return text


def redacted_env_summary() -> dict[str, Any]:
    keys = sorted(
        key
        for key in os.environ
        if key.startswith("SOCMINT_") or key in {"DATABASE_URL"}
    )
    return {key: redact_value(key, os.environ.get(key)) for key in keys}


def config_summary() -> dict[str, Any]:
    settings = load_settings(require_secret=False)
    return {
        "data_dir": settings.data_dir,
        "media_dir": settings.media_dir,
        "database_url": redact_value("DATABASE_URL", settings.database_url),
        "allow_signup": settings.allow_signup,
        "https": settings.https,
        "tor_proxy_configured": bool(settings.tor_proxy),
        "log_level": settings.log_level,
        "log_format": settings.log_format,
        "log_file": settings.log_file,
        "auto_create_db": settings.auto_create_db,
        "admin_user_configured": bool(settings.admin_user),
        "admin_password_configured": bool(settings.admin_password),
        "signup_invite_code_configured": bool(settings.signup_invite_code),
        "backup_passphrase_configured": bool(settings.backup_passphrase),
    }


def route_health_summary(app) -> list[dict[str, Any]]:
    available = {rule.rule: rule.endpoint for rule in app.url_map.iter_rules()}
    return [
        {
            "route": route,
            "registered": route in available,
            "endpoint": available.get(route),
        }
        for route in SUPPORT_BUNDLE_ROUTES
    ]


def export_artifact_summary(subject_id: int = 4) -> dict[str, Any]:
    latest = latest_full_report_export(subject_id)
    history = full_report_export_history(subject_id, limit=25)
    manifest = latest.get("manifest") or {}
    files = manifest.get("files") or []
    return {
        "subject_id": subject_id,
        "latest_available": bool(latest.get("available")),
        "history_count": history.get("count", 0),
        "latest_result": latest.get("result_name") or latest.get("latest"),
        "artifact_count": manifest.get("artifact_count", len(files)),
        "artifacts": [
            {
                "role": item.get("role"),
                "name": item.get("name"),
                "size_bytes": item.get("size_bytes"),
                "sha256_present": bool(item.get("sha256")),
            }
            for item in files
        ],
    }


def recent_error_summary(limit: int = 50) -> dict[str, Any]:
    settings = load_settings(require_secret=False)
    path = Path(settings.log_file) if settings.log_file else None
    if not path or not path.exists() or not path.is_file():
        return {
            "available": False,
            "reason": "SOCMINT_LOG_FILE is not set or file is unavailable",
            "errors": [],
        }
    lines = path.read_text(errors="replace").splitlines()[-1000:]
    errors = [
        line
        for line in lines
        if any(
            marker in line
            for marker in (
                "ERROR",
                "Traceback",
                'status_code":500',
                "Internal Server Error",
            )
        )
    ]
    return {
        "available": True,
        "path": str(path),
        "error_count": len(errors),
        "errors": errors[-limit:],
    }


def filesystem_summary() -> dict[str, Any]:
    settings = load_settings(require_secret=False)
    data_dir = Path(settings.data_dir)
    dossiers = dossier_root()
    support = support_bundle_root()
    return {
        "data_dir": {
            "path": str(data_dir),
            "exists": data_dir.exists(),
            "writable": os.access(data_dir, os.W_OK),
        },
        "dossier_root": {
            "path": str(dossiers),
            "exists": dossiers.exists(),
            "writable": os.access(dossiers, os.W_OK),
        },
        "support_bundle_root": {
            "path": str(support),
            "exists": support.exists(),
            "writable": os.access(support, os.W_OK),
        },
    }


def support_bundle_payload(app=None, subject_id: int = 4) -> dict[str, Any]:
    return {
        "schema": SUPPORT_BUNDLE_SCHEMA,
        "version": SUPPORT_BUNDLE_VERSION,
        "generated_at": utc_now(),
        "purpose": "safe runtime diagnostics for support and post-release troubleshooting",
        "platform": {
            "python": platform.python_version(),
            "system": platform.system(),
            "release": platform.release(),
        },
        "config": config_summary(),
        "environment": redacted_env_summary(),
        "filesystem": filesystem_summary(),
        "routes": route_health_summary(app) if app is not None else [],
        "exports": export_artifact_summary(subject_id=subject_id),
        "recent_errors": recent_error_summary(),
        "acceptance_scripts": {
            "clean_install": "scripts/clean_install_acceptance_v13_33.sh",
            "runtime_acceptance": "scripts/runtime_acceptance_v13_33.sh",
            "screenshot_capture": "scripts/capture_runtime_pages_v13_33.py",
            "support_bundle_capture": "scripts/support_bundle_v13_34.sh",
        },
    }


def write_support_bundle(app=None, subject_id: int = 4) -> dict[str, Any]:
    payload = support_bundle_payload(app=app, subject_id=subject_id)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    base = f"socmint-support-bundle-v13-34-{stamp}"
    root = support_bundle_root()
    json_path = root / f"{base}.json"
    txt_path = root / f"{base}.txt"
    zip_path = root / f"{base}.zip"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    txt_path.write_text(render_support_bundle_text(payload))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(json_path, arcname=json_path.name)
        zf.write(txt_path, arcname=txt_path.name)
        zf.writestr(
            "README.txt",
            "SOCMINT v13.34 support bundle. Secrets are redacted by design.\n",
        )

    return {
        "ok": True,
        "schema": SUPPORT_BUNDLE_SCHEMA,
        "generated_at": payload["generated_at"],
        "json_path": str(json_path),
        "text_path": str(txt_path),
        "zip_path": str(zip_path),
        "zip_name": zip_path.name,
        "size_bytes": zip_path.stat().st_size,
    }


def render_support_bundle_text(payload: dict[str, Any]) -> str:
    lines = [
        "SOCMINT Support Bundle v13.34",
        f"Generated: {payload.get('generated_at')}",
        f"Schema: {payload.get('schema')}",
        "",
        "Routes:",
    ]
    for item in payload.get("routes", []):
        lines.append(
            f"- {item.get('route')}: {'registered' if item.get('registered') else 'missing'}"
        )
    exports = payload.get("exports", {})
    lines.extend(
        [
            "",
            "Exports:",
            f"- latest_available: {exports.get('latest_available')}",
            f"- history_count: {exports.get('history_count')}",
            f"- artifact_count: {exports.get('artifact_count')}",
            "",
            "Recent errors:",
            f"- available: {payload.get('recent_errors', {}).get('available')}",
            f"- error_count: {payload.get('recent_errors', {}).get('error_count', 0)}",
        ]
    )
    return "\n".join(lines) + "\n"


def _html_bool(value: Any) -> str:
    return "YES" if value else "NO"


def render_support_bundle_html(payload: dict[str, Any]) -> str:
    route_cards = "".join(
        "<article class='export-artifact-card'>"
        f"<span>Route</span><strong>{html.escape(item.get('route', ''))}</strong>"
        f"<p>Registered: {_html_bool(item.get('registered'))}</p>"
        f"<code>{html.escape(str(item.get('endpoint') or 'missing'))}</code>"
        "</article>"
        for item in payload.get("routes", [])
    )
    export_cards = "".join(
        "<article class='export-artifact-card'>"
        f"<span>{html.escape(str(item.get('role') or 'artifact'))}</span>"
        f"<strong>{html.escape(str(item.get('name') or 'unnamed'))}</strong>"
        f"<p>Size: {html.escape(str(item.get('size_bytes') or 0))}</p>"
        f"<p>SHA-256 present: {_html_bool(item.get('sha256_present'))}</p>"
        "</article>"
        for item in payload.get("exports", {}).get("artifacts", [])
    )
    return f"""
    <!doctype html>
    <html><head><meta charset='utf-8'><title>Support Bundle v13.34</title>
      <link rel='stylesheet' href='/static/runtime_visual.css'>
    </head>
    <body class='runtime-utility-page'>
      <main class='runtime-utility-container'>
        <section class='runtime-utility-card operator-status-banner'>
          <p class='eyebrow'>Runtime Diagnostics</p>
          <h1>Support Bundle v13.34</h1>
          <p>Safe, redacted diagnostics for post-release support.</p>
          <div class='runtime-utility-actions'><a class='export-artifact-primary' href='/support/bundle/v13.34/download'>Generate Support Bundle ZIP</a><a href='/api/v1/support/bundle/v13.34'>View JSON API</a></div>
        </section>
        <section class='runtime-utility-card'>
          <h2>Summary</h2>
          <div class='export-summary-list'>
            <div><span>Generated</span><strong>{html.escape(payload.get("generated_at", ""))}</strong></div>
            <div><span>Schema</span><code>{html.escape(payload.get("schema", ""))}</code></div>
            <div><span>Routes</span><strong>{len(payload.get("routes", []))}</strong></div>
            <div><span>Export artifacts</span><strong>{html.escape(str(payload.get("exports", {}).get("artifact_count", 0)))}</strong></div>
          </div>
        </section>
        <section class='runtime-utility-card'><h2>Route Health</h2><div class='export-artifact-grid'>{route_cards}</div></section>
        <section class='runtime-utility-card'><h2>Latest Export Artifacts</h2><div class='export-artifact-grid'>{export_cards or "<p>No export artifacts found.</p>"}</div></section>
        <section class='runtime-utility-card'><h2>Redacted Config Summary</h2><pre>{html.escape(json.dumps(payload.get("config", {}), indent=2, sort_keys=True))}</pre></section>
        <section class='runtime-utility-card'><h2>Recent Error Summary</h2><pre>{html.escape(json.dumps(payload.get("recent_errors", {}), indent=2, sort_keys=True))}</pre></section>
      </main>
    </body></html>
    """


def register_support_bundle_routes_v13_34(app) -> None:
    if "ui_support_bundle_v13_34" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_support_bundle_v13_34():
        return jsonify(support_bundle_payload(app=app))

    @login_required
    def ui_support_bundle_v13_34():
        return Response(
            render_support_bundle_html(support_bundle_payload(app=app)),
            mimetype="text/html; charset=utf-8",
        )

    @login_required
    def download_support_bundle_v13_34():
        result = write_support_bundle(app=app)
        return send_file(
            result["zip_path"],
            as_attachment=True,
            download_name=result["zip_name"],
            mimetype="application/zip",
        )

    app.add_url_rule(
        "/api/v1/support/bundle/v13.34",
        endpoint="api_support_bundle_v13_34",
        view_func=api_support_bundle_v13_34,
        methods=["GET"],
    )
    app.add_url_rule(
        "/support/bundle/v13.34",
        endpoint="ui_support_bundle_v13_34",
        view_func=ui_support_bundle_v13_34,
        methods=["GET"],
    )
    app.add_url_rule(
        "/support/bundle/v13.34/download",
        endpoint="download_support_bundle_v13_34",
        view_func=download_support_bundle_v13_34,
        methods=["GET"],
    )

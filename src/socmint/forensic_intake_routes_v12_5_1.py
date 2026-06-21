from __future__ import annotations

import json
from pathlib import Path

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from .forensic_intake_v12_5 import CUSTODY_SCHEMA
from .forensic_intake_v12_5 import MANIFEST_SCHEMA
from .forensic_intake_v12_5 import dropzones_root
from .forensic_intake_v12_5 import ingest_dropzones
from .forensic_intake_v12_5 import intake_dashboard_payload
from .forensic_intake_v12_5 import manifests_root
from .forensic_intake_v12_5 import vault_root


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def forensic_dashboard_payload() -> dict:
    payload = intake_dashboard_payload()
    manifest_dir = manifests_root()
    vault_dir = vault_root()
    manifests = []
    custody = []
    if manifest_dir.exists():
        for path in sorted(manifest_dir.glob("*.json"), reverse=True)[:20]:
            data = _load_json(path)
            manifests.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "schema": (data or {}).get("schema"),
                    "generated_at": (data or {}).get("generated_at"),
                    "item_count": (data or {}).get("item_count")
                    or len((data or {}).get("events", [])),
                }
            )
            if (data or {}).get("schema") == CUSTODY_SCHEMA:
                custody.append(data)
    vault_items = []
    if vault_dir.exists():
        for path in sorted(vault_dir.rglob("original*"))[:200]:
            vault_items.append(
                {
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                    "evidence_id": path.parent.name,
                    "kind": path.parent.parent.name
                    if len(path.parents) > 1
                    else "unknown",
                }
            )
    payload.update(
        {
            "schema": "socmint.forensic_intake_ui.v12_5_1",
            "manifest_index": manifests,
            "vault_items": vault_items,
            "custody_reports": custody[:5],
            "dropzone_browser": payload.get("pending_files", []),
            "promotion_controls": {
                "state": "analyst_review_required",
                "note": "Evidence promotion to dossier/assertion requires reviewed chain-of-custody and validation.",
            },
            "dossier_linkage": {
                "state": "ready_for_v12_plus",
                "note": "Promoted evidence should attach to subject assertions and full dossier export layers.",
            },
        }
    )
    return payload


def register_forensic_intake_routes(app) -> None:
    if "forensic_intake_dashboard" in app.view_functions:
        return

    from .dashboard import login_required, run_required

    @login_required
    def forensic_intake_dashboard():
        payload = forensic_dashboard_payload()
        return render_template("forensic_intake_dashboard.html", payload=payload)

    @run_required
    def forensic_intake_run():
        report = ingest_dropzones(actor=session.get("user") or "operator")
        flash(
            f"Forensic intake completed: {report['ingested_count']} items preserved.",
            "success",
        )
        return redirect(url_for("forensic_intake_dashboard"))

    @login_required
    def api_forensic_intake_dashboard():
        return jsonify(forensic_dashboard_payload())

    app.add_url_rule(
        "/forensic/intake",
        endpoint="forensic_intake_dashboard",
        view_func=forensic_intake_dashboard,
        methods=["GET"],
    )
    app.add_url_rule(
        "/forensic/intake/run",
        endpoint="forensic_intake_run",
        view_func=forensic_intake_run,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/forensic/intake",
        endpoint="api_forensic_intake_dashboard",
        view_func=api_forensic_intake_dashboard,
        methods=["GET"],
    )

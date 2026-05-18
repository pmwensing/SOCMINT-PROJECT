from __future__ import annotations

import json
from pathlib import Path

from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for

from .recon_document_locator import DORK_TEMPLATES
from .recon_document_locator import acquisition_queue_path
from .recon_document_locator import document_locator_search
from .recon_document_locator import queue_for_manual_acquisition
from .recon_document_locator import render_dork_templates


def _queue_payload() -> dict:
    path = acquisition_queue_path()
    if not path.exists():
        return {"schema": "socmint.recon.acquisition_queue.v12_3_1", "items": [], "queue_path": str(path), "count": 0}
    try:
        payload = json.loads(path.read_text())
    except Exception:
        payload = {"schema": "socmint.recon.acquisition_queue.v12_3_1", "items": []}
    payload["queue_path"] = str(path)
    payload["count"] = len(payload.get("items", []))
    return payload


def recon_document_locator_dashboard_payload(query: str | None = None, connectors: list[str] | None = None) -> dict:
    query = (query or "").strip()
    search_payload = None
    if query:
        search_payload = document_locator_search(query, connectors=connectors or None)
    return {
        "schema": "socmint.recon.document_locator_ui.v12_3_2",
        "query": query,
        "connectors": connectors or ["brave", "wayback_cdx", "commoncrawl", "github_code"],
        "connector_options": [
            {"key": "brave", "label": "Brave Search API", "role": "preferred broad web backend"},
            {"key": "wayback_cdx", "label": "Wayback CDX", "role": "historic public web archive"},
            {"key": "commoncrawl", "label": "Common Crawl", "role": "public crawl index"},
            {"key": "github_code", "label": "GitHub Code Search", "role": "public code/document search"},
        ],
        "dork_templates": render_dork_templates(query or "target"),
        "template_library": DORK_TEMPLATES,
        "search": search_payload,
        "queue": _queue_payload(),
        "source_trust_matrix": [
            {"label": "document-candidate", "meaning": "Likely public document/file lead, still not evidence."},
            {"label": "archive", "meaning": "Public archive index result; verify source and capture."},
            {"label": "review", "meaning": "Lead requires analyst review before acquisition."},
            {"label": "stub", "meaning": "Diagnostic placeholder because live recon is disabled or missing API keys."},
        ],
        "legal_safety_matrix": [
            {"label": "public-index-result", "meaning": "Found through public index/search."},
            {"label": "api-search-result", "meaning": "Returned through public search API."},
            {"label": "public-archive-index", "meaning": "Returned through public archive index."},
            {"label": "manual-review-required", "meaning": "Analyst must verify legality, relevance, and source policy."},
            {"label": "located-url-not-evidence", "meaning": "URL becomes evidence only after v12.5 acquisition, hashing, preservation, and promotion."},
        ],
        "v12_5_handoff": {
            "state": "manual_acquisition_queue",
            "next_step": "Review queued lead, then send to v12.5 forensic intake for lawful acquisition and chain-of-custody preservation.",
        },
    }


def register_recon_document_locator_routes(app) -> None:
    if "recon_document_locator_view" in app.view_functions:
        return

    from .dashboard import login_required, run_required

    @login_required
    def recon_document_locator_view():
        query = request.args.get("q", "").strip()
        connectors = request.args.getlist("connectors")
        payload = recon_document_locator_dashboard_payload(query, connectors or None)
        return render_template("recon_document_locator.html", payload=payload)

    @login_required
    def api_recon_document_locator_search():
        payload = request.get_json(silent=True) or {}
        query = (payload.get("query") or request.args.get("q") or "").strip()
        if not query:
            return jsonify({"schema": "socmint.recon.document_locator_ui.v12_3_2", "error": "query is required"}), 400
        connectors = payload.get("connectors") or request.args.getlist("connectors") or None
        return jsonify(document_locator_search(query, connectors=connectors))

    @run_required
    def recon_document_locator_queue():
        raw = request.form.get("result_json") or "{}"
        try:
            result = json.loads(raw)
        except Exception:
            flash("Invalid document locator result payload.", "error")
            return redirect(url_for("recon_document_locator_view"))
        queued = queue_for_manual_acquisition(result, actor=session.get("user"))
        flash(f"Queued lead {queued['queued']['id']} for v12.5 forensic intake review.", "success")
        return redirect(url_for("recon_document_locator_view", q=request.form.get("query", "")))

    @login_required
    def api_recon_document_locator_queue():
        return jsonify(_queue_payload())

    @run_required
    def api_recon_document_locator_queue_add():
        payload = request.get_json(silent=True) or {}
        result = payload.get("result")
        if not isinstance(result, dict):
            return jsonify({"error": "result object is required"}), 400
        queued = queue_for_manual_acquisition(result, actor=session.get("user"))
        return jsonify(queued), 202

    app.add_url_rule("/recon/document-locator", endpoint="recon_document_locator_view", view_func=recon_document_locator_view, methods=["GET"])
    app.add_url_rule("/recon/document-locator/queue", endpoint="recon_document_locator_queue", view_func=recon_document_locator_queue, methods=["POST"])
    app.add_url_rule("/api/v1/recon/document-locator/search", endpoint="api_recon_document_locator_search", view_func=api_recon_document_locator_search, methods=["GET", "POST"])
    app.add_url_rule("/api/v1/recon/document-locator/queue", endpoint="api_recon_document_locator_queue", view_func=api_recon_document_locator_queue, methods=["GET"])
    app.add_url_rule("/api/v1/recon/document-locator/queue", endpoint="api_recon_document_locator_queue_add", view_func=api_recon_document_locator_queue_add, methods=["POST"])

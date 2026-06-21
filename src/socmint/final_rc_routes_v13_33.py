from __future__ import annotations

from flask import Response, jsonify

RC_VERSION = "v13.33"
RC_TITLE = "Final Release Candidate Lock + Clean Install Acceptance"
RC_SCHEMA = "socmint.final_release_candidate.v13_33"
RC_ROUTES = [
    "/command-center",
    "/review/normalization-queue",
    "/subjects/4/dossier/readiness",
    "/subjects/4/claim-evidence-ledger",
    "/spine/subjects/4/dossier",
    "/spine/subjects/4/full-report/history",
    "/spine/subjects/4/full-report/view",
    "/spine/subjects/4/full-report/retention",
    "/release/final-rc/v13.33",
]
RC_ARTIFACTS = ["ZIP", "Manifest", "HTML", "Markdown", "JSON"]


def final_rc_status_payload() -> dict:
    return {
        "schema": RC_SCHEMA,
        "version": RC_VERSION,
        "title": RC_TITLE,
        "status": "release_candidate_locked",
        "clean_install_acceptance": "scripted",
        "route_acceptance": RC_ROUTES,
        "export_acceptance_artifacts": RC_ARTIFACTS,
        "screenshot_capture_helper": "scripts/capture_runtime_pages_v13_33.py",
        "clean_install_script": "scripts/clean_install_acceptance_v13_33.sh",
        "runtime_acceptance_script": "scripts/runtime_acceptance_v13_33.sh",
        "release_note": "release/V13_33_FINAL_RC_LOCK.md",
    }


def _rc_html(payload: dict) -> str:
    route_cards = "".join(
        f"<article class='export-artifact-card'><span>Route</span><strong>{route}</strong></article>"
        for route in payload["route_acceptance"]
    )
    artifact_cards = "".join(
        f"<article class='export-artifact-card'><span>Export artifact</span><strong>{artifact}</strong></article>"
        for artifact in payload["export_acceptance_artifacts"]
    )
    return f"""
    <!doctype html>
    <html><head><meta charset='utf-8'><title>{payload["version"]} Final RC Status</title>
      <link rel='stylesheet' href='/static/runtime_visual.css'>
    </head>
    <body class='runtime-utility-page'>
      <main class='runtime-utility-container'>
        <section class='runtime-utility-card operator-status-banner'>
          <p class='eyebrow'>Final Release Candidate</p>
          <h1>{payload["version"]} — {payload["title"]}</h1>
          <div class='export-summary-list'>
            <div><span>Status</span><strong>{payload["status"]}</strong></div>
            <div><span>Clean install</span><strong>{payload["clean_install_acceptance"]}</strong></div>
            <div><span>Routes</span><strong>{len(payload["route_acceptance"])}</strong></div>
            <div><span>Artifacts</span><strong>{len(payload["export_acceptance_artifacts"])}</strong></div>
          </div>
        </section>
        <section class='runtime-utility-card'>
          <h2>Acceptance Scripts</h2>
          <div class='export-artifact-grid'>
            <article class='export-artifact-card'><span>Clean clone/build/run</span><strong>{payload["clean_install_script"]}</strong></article>
            <article class='export-artifact-card'><span>Runtime acceptance</span><strong>{payload["runtime_acceptance_script"]}</strong></article>
            <article class='export-artifact-card'><span>Screenshot capture</span><strong>{payload["screenshot_capture_helper"]}</strong></article>
            <article class='export-artifact-card'><span>Release note</span><strong>{payload["release_note"]}</strong></article>
          </div>
        </section>
        <section class='runtime-utility-card'>
          <h2>Route Acceptance Lock</h2>
          <div class='export-artifact-grid'>{route_cards}</div>
        </section>
        <section class='runtime-utility-card'>
          <h2>Export Artifact Acceptance Lock</h2>
          <div class='export-artifact-grid'>{artifact_cards}</div>
        </section>
      </main>
    </body></html>
    """


def register_final_rc_routes_v13_33(app) -> None:
    if "ui_final_rc_status_v13_33" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_final_rc_status_v13_33():
        return jsonify(final_rc_status_payload())

    @login_required
    def ui_final_rc_status_v13_33():
        return Response(
            _rc_html(final_rc_status_payload()), mimetype="text/html; charset=utf-8"
        )

    app.add_url_rule(
        "/api/v1/release/final-rc/v13.33",
        endpoint="api_final_rc_status_v13_33",
        view_func=api_final_rc_status_v13_33,
        methods=["GET"],
    )
    app.add_url_rule(
        "/release/final-rc/v13.33",
        endpoint="ui_final_rc_status_v13_33",
        view_func=ui_final_rc_status_v13_33,
        methods=["GET"],
    )

from __future__ import annotations

import html
import json
from collections import defaultdict
from typing import Any

from flask import Response, jsonify

from . import database as db

SCHEMA = "socmint.correlation_scope_audit.v13_35A"
VERSION = "v13.35A"

REQUIRED_SCOPE_TABLES = {
    "spine_seeds": "correlation_scope_id",
    "spine_connector_runs": "correlation_scope_id",
    "spine_observations": "correlation_scope_id",
    "spine_dossier_assertions": "correlation_scope_id",
    "media_profile_enrichments": "correlation_scope_id",
    "account_discoveries": "correlation_scope_id",
}

PROMOTION_REQUIREMENTS = [
    "same_scope",
    "analyst_merged_scope",
    "deterministic_same_target",
]


def _safe_json(value: str | None, default: Any = None) -> Any:
    if default is None:
        default = {}
    try:
        return json.loads(value or "{}")
    except Exception:
        return default


def scope_gate_decision(
    *,
    same_scope: bool = False,
    same_target: bool = False,
    analyst_merge: bool = False,
    ambiguous: bool = False,
) -> dict[str, Any]:
    """Audit-only policy gate for future promotion enforcement.

    v13.35A does not change database schema and does not promote/reject records.
    It defines the decision policy so tests can prove ambiguous cross-scope
    matches are not treated as safe.
    """
    if same_scope:
        state = "allowed"
        reason = "same_scope"
    elif analyst_merge:
        state = "allowed"
        reason = "analyst_merged_scope"
    elif same_target:
        state = "allowed"
        reason = "deterministic_same_target"
    elif ambiguous:
        state = "quarantine"
        reason = "ambiguous_cross_scope_match"
    else:
        state = "needs_review"
        reason = "cross_scope_without_same_target_proof"

    return {
        "state": state,
        "reason": reason,
        "same_scope": same_scope,
        "same_target": same_target,
        "analyst_merge": analyst_merge,
        "ambiguous": ambiguous,
    }


def schema_scope_coverage() -> dict[str, Any]:
    missing = []
    present = []

    for table_name, column_name in REQUIRED_SCOPE_TABLES.items():
        table = db.Base.metadata.tables.get(table_name)
        exists = bool(table is not None and column_name in table.columns)
        row = {
            "table": table_name,
            "required_column": column_name,
            "present": exists,
        }
        if exists:
            present.append(row)
        else:
            missing.append(row)

    return {
        "required": REQUIRED_SCOPE_TABLES,
        "present": present,
        "missing": missing,
        "coverage_complete": not missing,
        "mode": "audit_only_no_schema_migration",
    }


def run_grouping_snapshot(subject_id: int | None = None) -> dict[str, Any]:
    """Group existing runs without mixing different initial seeds.

    Until persistent correlation_scope_id exists, the safest available legacy
    grouping key is subject_id + seed_id. This is an audit snapshot only.
    """
    runs = db.list_spine_connector_runs(subject_id=subject_id, limit=1000)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for run in runs:
        raw = _safe_json(getattr(run, "raw_result_json", "{}"))
        seed_id = getattr(run, "seed_id", None)
        group_key = f"subject:{run.subject_id}:seed:{seed_id or 'unknown'}"
        grouped[group_key].append(
            {
                "run_id": run.id,
                "subject_id": run.subject_id,
                "seed_id": seed_id,
                "connector_key": run.connector_key,
                "status": run.status,
                "raw_result_status": raw.get("status")
                if isinstance(raw, dict)
                else None,
                "created_at": run.created_at.isoformat()
                if getattr(run, "created_at", None)
                else None,
            }
        )

    mixed_groups = [
        key
        for key, rows in grouped.items()
        if len({row["seed_id"] for row in rows}) > 1
    ]

    return {
        "subject_id": subject_id,
        "group_key_policy": "subject_id + seed_id until persistent correlation_scope_id exists",
        "group_count": len(grouped),
        "mixed_group_count": len(mixed_groups),
        "mixed_groups": mixed_groups,
        "groups": grouped,
    }


def correlation_scope_audit_payload(subject_id: int | None = None) -> dict[str, Any]:
    coverage = schema_scope_coverage()
    grouping = run_grouping_snapshot(subject_id=subject_id)

    risk_flags = []
    if not coverage["coverage_complete"]:
        risk_flags.append("missing_persistent_correlation_scope_columns")
    if grouping["mixed_group_count"]:
        risk_flags.append("mixed_seed_groups_detected")

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "audit_required" if risk_flags else "audit_clear",
        "safe_decision": {
            "correlation_correctness_proven": False,
            "expand_enrichment_features": False,
            "quarantine_ambiguous_matches": True,
            "do_not_mix_initial_search_runs_without_scope_proof": True,
        },
        "risk_flags": risk_flags,
        "scope_coverage": coverage,
        "run_grouping": grouping,
        "policy_gate": {
            "promotion_requires": PROMOTION_REQUIREMENTS,
            "ambiguous_cross_scope_state": "quarantine",
            "audit_first_no_schema_migration": True,
        },
    }


def render_correlation_scope_audit_html(payload: dict[str, Any]) -> str:
    missing_cards = "".join(
        "<article class='export-artifact-card'>"
        f"<span>Missing scope column</span><strong>{html.escape(row['table'])}</strong>"
        f"<p>Required: <code>{html.escape(row['required_column'])}</code></p>"
        "</article>"
        for row in payload["scope_coverage"]["missing"]
    )

    group_cards = "".join(
        "<article class='export-artifact-card'>"
        f"<span>Run group</span><strong>{html.escape(key)}</strong>"
        f"<p>Runs: {len(rows)}</p>"
        "</article>"
        for key, rows in payload["run_grouping"]["groups"].items()
    )

    return f"""
    <!doctype html>
    <html>
      <head>
        <meta charset='utf-8'>
        <title>Correlation Scope Audit v13.35A</title>
        <link rel='stylesheet' href='/static/runtime_visual.css'>
      </head>
      <body class='runtime-utility-page'>
        <main class='runtime-utility-container'>
          <section class='runtime-utility-card operator-status-banner'>
            <p class='eyebrow'>Correctness Audit</p>
            <h1>Correlation Scope Lock + Run Isolation Audit v13.35A</h1>
            <p>Audit-first policy gate. This page does not run schema migrations.</p>
            <div class='export-summary-list'>
              <div><span>Status</span><strong>{html.escape(payload["status"])}</strong></div>
              <div><span>Risk flags</span><strong>{len(payload["risk_flags"])}</strong></div>
              <div><span>Scope coverage complete</span><strong>{"YES" if payload["scope_coverage"]["coverage_complete"] else "NO"}</strong></div>
              <div><span>Run groups</span><strong>{payload["run_grouping"]["group_count"]}</strong></div>
            </div>
          </section>

          <section class='runtime-utility-card'>
            <h2>Safe Decision</h2>
            <pre>{html.escape(json.dumps(payload["safe_decision"], indent=2, sort_keys=True))}</pre>
          </section>

          <section class='runtime-utility-card'>
            <h2>Missing Persistent Scope Coverage</h2>
            <div class='export-artifact-grid'>{missing_cards or "<p>No missing scope columns detected.</p>"}</div>
          </section>

          <section class='runtime-utility-card'>
            <h2>Initial Search / Run Grouping Snapshot</h2>
            <p>{html.escape(payload["run_grouping"]["group_key_policy"])}</p>
            <div class='export-artifact-grid'>{group_cards or "<p>No connector runs found.</p>"}</div>
          </section>

          <section class='runtime-utility-card'>
            <h2>Promotion Policy Gate</h2>
            <pre>{html.escape(json.dumps(payload["policy_gate"], indent=2, sort_keys=True))}</pre>
          </section>
        </main>
      </body>
    </html>
    """


def register_correlation_scope_audit_routes_v13_35(app) -> None:
    if "ui_correlation_scope_audit_v13_35" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_correlation_scope_audit_v13_35():
        return jsonify(correlation_scope_audit_payload())

    @login_required
    def ui_correlation_scope_audit_v13_35():
        return Response(
            render_correlation_scope_audit_html(correlation_scope_audit_payload()),
            mimetype="text/html; charset=utf-8",
        )

    app.add_url_rule(
        "/api/v1/audit/correlation-scope/v13.35",
        endpoint="api_correlation_scope_audit_v13_35",
        view_func=api_correlation_scope_audit_v13_35,
        methods=["GET"],
    )
    app.add_url_rule(
        "/audit/correlation-scope/v13.35",
        endpoint="ui_correlation_scope_audit_v13_35",
        view_func=ui_correlation_scope_audit_v13_35,
        methods=["GET"],
    )

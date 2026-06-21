from __future__ import annotations

from typing import Any

from flask import jsonify

from . import database as db
from .correlation_scope_write_path_v13_35 import (
    SCOPE_ID,
    backfill_record_scope,
    scoped_promotion_decision,
)

SCHEMA = "socmint.correlation_scope_db_backfill.v13_35D"
VERSION = "v13.35D"

MODEL_TABLES = [
    ("spine_seeds", db.SpineSeed),
    ("spine_connector_runs", db.SpineConnectorRun),
    ("spine_observations", db.SpineObservation),
    ("spine_dossier_assertions", db.SpineDossierAssertion),
]


def _record_for_model(obj: Any) -> dict[str, Any]:
    return {
        "subject_id": getattr(obj, "subject_id", None),
        "seed_id": getattr(obj, "seed_id", None) or getattr(obj, "id", None),
        "connector_run_id": getattr(obj, "run_id", None) or getattr(obj, "id", None),
        "target_type": getattr(obj, "seed_type", None)
        or getattr(obj, "connector_key", None)
        or getattr(obj, "observation_type", None)
        or getattr(obj, "assertion_type", None),
        "target_value": getattr(obj, "raw_value", None)
        or getattr(obj, "normalized_value", None)
        or getattr(obj, "assertion_value", None),
        "correlation_scope_id": getattr(obj, "correlation_scope_id", None),
        "correlation_scope_state": getattr(obj, "correlation_scope_state", None),
        "correlation_scope_reason": getattr(obj, "correlation_scope_reason", None),
    }


def _apply_scope(obj: Any, scoped: dict[str, Any]) -> bool:
    changed = False
    for attr in [
        "correlation_scope_id",
        "correlation_scope_state",
        "correlation_scope_reason",
    ]:
        if hasattr(obj, attr) and getattr(obj, attr, None) != scoped.get(attr):
            setattr(obj, attr, scoped.get(attr))
            changed = True
    return changed


def backfill_correlation_scopes(
    limit_per_table: int = 10000, commit: bool = True
) -> dict[str, Any]:
    db.ensure_configured()
    summary: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "mode": "db_backfill",
        "idempotent": True,
        "tables": {},
        "total_seen": 0,
        "total_changed": 0,
    }

    with db.Session() as session:
        for table_name, model in MODEL_TABLES:
            rows = session.query(model).limit(limit_per_table).all()
            changed = 0

            for row in rows:
                scoped = backfill_record_scope(_record_for_model(row))
                if _apply_scope(row, scoped):
                    changed += 1

            summary["tables"][table_name] = {"seen": len(rows), "changed": changed}
            summary["total_seen"] += len(rows)
            summary["total_changed"] += changed

        if commit:
            session.commit()
        else:
            session.rollback()

    return summary


def db_scope_proof_payload(limit_per_table: int = 1000) -> dict[str, Any]:
    db.ensure_configured()
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ok",
        "tables": {},
        "scope_columns": [
            "correlation_scope_id",
            "correlation_scope_state",
            "correlation_scope_reason",
        ],
        "quarantine_first": True,
    }

    with db.Session() as session:
        for table_name, model in MODEL_TABLES:
            rows = session.query(model).limit(limit_per_table).all()
            scoped_count = sum(
                1 for row in rows if getattr(row, "correlation_scope_id", None)
            )
            payload["tables"][table_name] = {
                "row_count_sampled": len(rows),
                "scoped_count": scoped_count,
                "unscoped_count": len(rows) - scoped_count,
                "examples": [
                    {
                        "id": getattr(row, "id", None),
                        "subject_id": getattr(row, "subject_id", None),
                        "correlation_scope_id": getattr(
                            row, "correlation_scope_id", None
                        ),
                        "correlation_scope_state": getattr(
                            row, "correlation_scope_state", None
                        ),
                        "correlation_scope_reason": getattr(
                            row, "correlation_scope_reason", None
                        ),
                    }
                    for row in rows[:5]
                ],
            }

    return payload


def two_initial_search_db_isolation_proof() -> dict[str, Any]:
    first = backfill_record_scope(
        {
            "subject_id": "subject-demo",
            "seed_id": "seed-a",
            "connector_run_id": "run-a",
            "finding_type": "profile_url",
            "value": "https://social.example/alex-smith",
        }
    )
    second = backfill_record_scope(
        {
            "subject_id": "subject-demo",
            "seed_id": "seed-b",
            "connector_run_id": "run-b",
            "finding_type": "profile_url",
            "value": "https://social.example/alex-smith",
        }
    )

    decision = scoped_promotion_decision(
        finding_record=second,
        parent_record={
            SCOPE_ID: first[SCOPE_ID],
            "target_type": "name",
            "target_value": "Alex Smith",
        },
    )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "first_scope": first[SCOPE_ID],
        "second_scope": second[SCOPE_ID],
        "separate": first[SCOPE_ID] != second[SCOPE_ID],
        "decision": decision,
    }


def register_correlation_scope_db_backfill_routes_v13_35(app) -> None:
    if "api_correlation_scope_db_proof_v13_35" in app.view_functions:
        return

    from .dashboard import admin_required, login_required

    @login_required
    def correlation_scope_db_proof_v13_35():
        return jsonify(db_scope_proof_payload())

    @admin_required
    def correlation_scope_db_backfill_v13_35():
        return jsonify(backfill_correlation_scopes())

    app.add_url_rule(
        "/api/v1/audit/correlation-scope/v13.35/db-proof",
        endpoint="api_correlation_scope_db_proof_v13_35",
        view_func=correlation_scope_db_proof_v13_35,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/admin/correlation-scope/v13.35/backfill",
        endpoint="api_correlation_scope_db_backfill_v13_35",
        view_func=correlation_scope_db_backfill_v13_35,
        methods=["POST"],
    )

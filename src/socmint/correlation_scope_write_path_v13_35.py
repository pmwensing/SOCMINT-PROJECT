from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .correlation_scope_enforcement_v13_35 import (
    SCHEMA as ENFORCEMENT_SCHEMA,
    VERSION as ENFORCEMENT_VERSION,
    derive_correlation_scope_id,
    promotion_scope_decision,
)

SCHEMA = "socmint.correlation_scope_write_path.v13_35C"
VERSION = "v13.35C"

SCOPE_ID = "correlation_scope_id"
SCOPE_STATE = "correlation_scope_state"
SCOPE_REASON = "correlation_scope_reason"


@dataclass(frozen=True)
class ScopeWriteResult:
    schema: str
    version: str
    correlation_scope_id: str
    correlation_scope_state: str
    correlation_scope_reason: str


def assign_seed_scope(
    *,
    subject_id: Any,
    seed_id: Any,
    seed_type: Any,
    seed_value: Any,
    existing_scope_id: str | None = None,
) -> ScopeWriteResult:
    scope_id = existing_scope_id or derive_correlation_scope_id(
        subject_id=subject_id,
        seed_id=seed_id,
        connector_run_id="root",
        target_type=seed_type,
        target_value=seed_value,
        legacy=False,
    )
    return ScopeWriteResult(
        schema=SCHEMA,
        version=VERSION,
        correlation_scope_id=scope_id,
        correlation_scope_state="root_seed",
        correlation_scope_reason="assigned_at_seed_creation"
        if not existing_scope_id
        else "existing_scope_preserved",
    )


def inherit_scope(
    *,
    parent_scope_id: str | None,
    subject_id: Any,
    seed_id: Any,
    connector_run_id: Any,
    target_type: Any,
    target_value: Any,
    existing_scope_id: str | None = None,
) -> ScopeWriteResult:
    if existing_scope_id:
        scope_id = existing_scope_id
        reason = "existing_scope_preserved"
    elif parent_scope_id:
        scope_id = parent_scope_id
        reason = "inherited_from_parent_scope"
    else:
        scope_id = derive_correlation_scope_id(
            subject_id=subject_id,
            seed_id=seed_id,
            connector_run_id=connector_run_id,
            target_type=target_type,
            target_value=target_value,
            legacy=True,
        )
        reason = "derived_legacy_scope_no_parent"

    return ScopeWriteResult(
        schema=SCHEMA,
        version=VERSION,
        correlation_scope_id=scope_id,
        correlation_scope_state="scoped",
        correlation_scope_reason=reason,
    )


def record_scope_fields(
    record: dict[str, Any], result: ScopeWriteResult
) -> dict[str, Any]:
    updated = dict(record)
    updated[SCOPE_ID] = result.correlation_scope_id
    updated[SCOPE_STATE] = result.correlation_scope_state
    updated[SCOPE_REASON] = result.correlation_scope_reason
    return updated


def backfill_record_scope(record: dict[str, Any]) -> dict[str, Any]:
    if record.get(SCOPE_ID):
        return record_scope_fields(
            record,
            ScopeWriteResult(
                schema=SCHEMA,
                version=VERSION,
                correlation_scope_id=str(record[SCOPE_ID]),
                correlation_scope_state=str(record.get(SCOPE_STATE) or "scoped"),
                correlation_scope_reason=str(
                    record.get(SCOPE_REASON) or "existing_scope_preserved"
                ),
            ),
        )

    scope_id = derive_correlation_scope_id(
        subject_id=record.get("subject_id")
        or record.get("spine_subject_id")
        or record.get("case_subject_id"),
        seed_id=record.get("seed_id")
        or record.get("root_seed_id")
        or record.get("initial_search_id"),
        connector_run_id=record.get("connector_run_id")
        or record.get("run_id")
        or record.get("root_run_id"),
        target_type=record.get("target_type")
        or record.get("seed_type")
        or record.get("finding_type")
        or record.get("observation_type"),
        target_value=record.get("target_value")
        or record.get("seed_value")
        or record.get("value")
        or record.get("display_value"),
        legacy=True,
    )

    return record_scope_fields(
        record,
        ScopeWriteResult(
            schema=SCHEMA,
            version=VERSION,
            correlation_scope_id=scope_id,
            correlation_scope_state="legacy_backfilled",
            correlation_scope_reason="derived_legacy_scope_per_subject_seed_run_target",
        ),
    )


def backfill_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [backfill_record_scope(record) for record in records]


def scoped_promotion_decision(
    *,
    finding_record: dict[str, Any],
    parent_record: dict[str, Any],
    analyst_merged_scope: bool = False,
) -> dict[str, Any]:
    return promotion_scope_decision(
        finding_scope_id=finding_record.get(SCOPE_ID),
        parent_scope_id=parent_record.get(SCOPE_ID),
        finding_type=finding_record.get("finding_type")
        or finding_record.get("target_type")
        or finding_record.get("type"),
        finding_value=finding_record.get("value")
        or finding_record.get("target_value")
        or finding_record.get("display_value"),
        parent_type=parent_record.get("finding_type")
        or parent_record.get("target_type")
        or parent_record.get("type"),
        parent_value=parent_record.get("value")
        or parent_record.get("target_value")
        or parent_record.get("display_value"),
        analyst_merged_scope=analyst_merged_scope,
    )


def write_path_status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "enforcement_schema": ENFORCEMENT_SCHEMA,
        "enforcement_version": ENFORCEMENT_VERSION,
        "scope": "write_path_propagation_and_backfill_only",
        "non_goals": [
            "no_new_connectors",
            "no_new_enrichment_sources",
            "no_broad_ui_redesign",
            "no_final_v13_35_tag",
        ],
        "rules": [
            "new_seed_gets_scope",
            "child_records_inherit_parent_scope",
            "legacy_backfill_is_idempotent",
            "ambiguous_cross_scope_profile_quarantines",
        ],
    }

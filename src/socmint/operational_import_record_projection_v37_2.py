from __future__ import annotations

from typing import Any

from .operational_import_records_v37_2 import current_batches


def current_staged_record_projections(
    import_id: str | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for batch in current_batches():
        parent_import_id = str(batch.get("operational_import_id") or "")
        if import_id and parent_import_id != import_id:
            continue
        for item in batch.get("records") or []:
            if not isinstance(item, dict):
                continue
            records.append(
                {
                    **item,
                    "operational_import_id": parent_import_id,
                    "staged_record_batch_id": batch.get("staged_record_batch_id"),
                    "batch_event_sha256": batch.get("batch_event_sha256"),
                    "batch_recorded_at": batch.get("recorded_at"),
                }
            )
    return sorted(
        records,
        key=lambda item: str(item.get("staged_record_id") or ""),
    )


def find_staged_record_projection(
    staged_record_id: str,
) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_staged_record_projections()
            if item.get("staged_record_id") == staged_record_id
        ),
        None,
    )

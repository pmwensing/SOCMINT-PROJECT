# v19.2 Persistent Decision Filtering and Review Controls

The v19.2 layer adds actor, decision, and date filtering; durable-history pagination; and review-state controls to the existing persistent case-review decision UI.

## Filtering

Durable decision history can now be filtered by:

- actor
- decision
- persisted date from
- persisted date to
- review state

The API accepts the same filters through query parameters on:

- `GET /api/v1/case-intelligence-review/<case_id>/decisions/persistent`

## Pagination

The durable-history API now returns:

- current page
- page size
- total matching entries
- page count
- previous/next availability

The workspace provides previous/next controls and selectable page sizes.

## Review controls

Supported review states are:

- `unreviewed`
- `reviewed`
- `needs_follow_up`
- `accepted`

Review-state changes are recorded as separate `audit_logs` annotations through:

- `POST /api/v1/case-intelligence-review/<case_id>/decisions/<decision_record_id>/review-state`

Each annotation records the reviewer, review state, optional review note, timestamp, and source decision record id.

## Immutability

The original durable decision audit record is immutable. Review controls never update or delete it. The current review state is projected from the latest separate annotation record.

## Safety and schema

- Review annotations are case-scoped.
- Invalid states and cross-case decision ids are blocked.
- No automatic delivery-state mutation is introduced.
- The existing `audit_logs` table is reused.
- No new table, schema mutation, or migration is introduced.

## Validation

Focused regression coverage is provided in:

- `tests/test_v19_2_persistent_decision_filtering_review_controls.py`

# v25.1 Correlation Candidate Review and Decision

Adds immutable analyst review decisions for v25.0 cross-case correlation candidates.

Analysts may accept, reject, defer, or split a visible candidate correlation. Every decision requires explicit confirmation, reviewer identity from the authenticated session, and a non-empty decision reason.

Each review event preserves:

- the complete candidate snapshot
- every source occurrence and provenance SHA-256
- participating case IDs
- category and normalized match value
- candidate SHA-256
- reviewer identity
- decision reason
- active workspace access scope
- minimum case threshold
- immutable audit-record ID and timestamp
- review-decision SHA-256

Split decisions require at least two non-empty groups. Every source occurrence must appear exactly once across those groups, with no overlap or omissions. The split records analyst interpretation only; it does not rewrite the source candidate or any case-level provenance.

Routes:

- `GET /api/v1/cross-case-intelligence/<correlation_id>/reviews`
- `POST /api/v1/cross-case-intelligence/<correlation_id>/review`

The browser workspace now shows the latest review, review count, source occurrences, accept/reject/defer/split controls, explicit confirmation, split grouping controls, and the recorded API result.

v25.1 creates immutable audit history only. It preserves every source occurrence, does not mutate the v25.0 candidate snapshot, does not modify case records or provenance, performs no collection or connector execution, and introduces no migration.

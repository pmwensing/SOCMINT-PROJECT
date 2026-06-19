# v29.1 Collection Job Contract and State Machine

Adds the authoritative Collection Job Contract and State Machine for controlled collection lifecycle governance.

Supported states are drafted, authorized, queued, running, completed, failed, blocked, cancelled, and superseded.

Each contract records connector, target binding, case/entity/source scope, authorization binding, collection purpose, idempotency key, optional legacy scan-job binding, attempt number, immutable definition hash, event ID, and event SHA-256.

Each transition records from-state, to-state, attempt number, optional refreshed authorization binding, failure category, retry eligibility, reason, previous-state binding, and deterministic hashes.

Allowed transitions are explicit. Invalid state jumps, duplicate active idempotency keys, missing authorization, missing reasons, and unclassified failure transitions are blocked.

Retry eligibility is projected only for failed or blocked work. Authorization, scope, policy, and duplicate failures are not retryable. Re-queueing retryable failed or blocked work increments the attempt number.

All writes require an authenticated active administrator, CSRF validation, explicit confirmation, and a transition or administrative reason.

Preservation boundaries:

- append-only collection-job history
- no connector execution
- no retry execution
- no legacy scan-job mutation
- no case-access mutation
- no source evidence rewrite
- no secret exposure

Routes:

- `GET /collection-operations/jobs`
- `GET /api/v1/collection-operations/jobs`
- `POST /api/v1/collection-operations/jobs`
- `POST /api/v1/collection-operations/jobs/<collection_job_id>/transition`

This slice introduces no migration. Contract and transition events are stored in the existing audit log.

# v29.5 Retry, Recovery, and Operator Intervention

Adds controlled retry requests, retry approvals, recovery plans, operator intervention records, blocked-state resolution guidance, manual cancellation, supersession, and append-only recovery history.

Each retry request binds to a failed or blocked v29.1 collection job that is explicitly retry eligible. The request records an idempotency key, backoff seconds, earliest retry time, retry window end, maximum attempts, requested attempt number, failure category, job-event hash, actor, reason, and deterministic recovery-event hash.

Retry approvals and denials are separate immutable decisions. An approved request does not execute a connector and does not automatically requeue a job.

Recovery plans define ordered steps, plan type, retry-request binding, replacement-job binding, requested attempt number, and whether operator intervention is required. Retry plans require an approved retry request.

Operator intervention supports manual review, blocked-state resolution, quarantine review, manual cancellation, and supersession. Cancellation and supersession may apply the existing append-only v29.1 terminal state transition. Other resolutions remain advisory and must continue through the controlled job and policy workflows.

The workspace reports pending and approved requests, open and expired retry windows, approved retries waiting for backoff, retries without recovery plans, recovery plans, operator interventions, and immutable recovery history.

Preservation boundaries:

- no automatic connector execution
- no automatic retry execution
- no legacy scan-job mutation
- no evidence mutation
- no case-access change
- no secret exposure
- append-only recovery history
- no migration

Routes:

- `GET /collection-operations/recovery`
- `GET /api/v1/collection-operations/recovery`
- `POST /api/v1/collection-operations/jobs/<collection_job_id>/retry-requests`
- `POST /api/v1/collection-operations/retry-requests/<retry_request_id>/decision`
- `POST /api/v1/collection-operations/jobs/<collection_job_id>/recovery-plans`
- `POST /api/v1/collection-operations/jobs/<collection_job_id>/interventions`

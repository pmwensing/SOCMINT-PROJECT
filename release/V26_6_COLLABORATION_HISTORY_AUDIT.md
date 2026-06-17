# v26.6 Collaboration History and Audit

Adds a read-only, access-scoped collaboration audit workspace consolidating team assignments and revocations, notes and corrections, mentions, acknowledgements and read events, review requests, task handoffs, request and handoff transitions, responses, escalations, resolutions, and a deterministic workload queue checkpoint.

Every ordered history event exposes actor, affected user, case ID, event type, timestamp, source action and record ID, source binding and SHA-256, access scope, previous state, and new state.

The current collaboration state summarizes the active team, current owner, open requests, pending handoffs, unacknowledged items, overdue items, unresolved responses, active escalations, and unresolved action counts. The complete state receives a deterministic SHA-256.

The browser and API routes are `/collaboration/history` and `/api/v1/collaboration/history`. Both require authentication and enforce the existing case access scope.

This slice is read-only. It creates no history or queue record, mutates no source collaboration event, changes no case access scope, performs no connector execution or collection activity, and introduces no migration.

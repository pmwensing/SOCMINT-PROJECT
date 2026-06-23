# v34.8 Operator Acceptance and Production Hardening

## Scope

This hardening slice validates the merged v34 execution surface and closes the production gaps identified after release.

## Operator acceptance matrix

Each action family must be exercised in a controlled test database with an injected authoritative delegate:

1. audience, package, and authorization
2. delivery and receipt
3. feedback and correction
4. recall and retention

For every family, acceptance requires:

- an eligible action creates a deterministic confirmation contract
- a cancelled or unconfirmed request performs no execution
- a route/action mismatch is rejected
- an unavailable or unauthorized delegate is rejected
- the first confirmed submission executes once
- a duplicate confirmation is rejected from durable storage
- the response identifies authoritative record IDs when supplied by the delegate
- the response includes confirmation-claim and execution audit IDs
- the canonical v33 workspace is refreshed and returned

## Delegate compatibility audit

The runtime exposes:

`GET /api/v1/dissemination-governance/delegate-signature-audit`

The audit compares every registered action's required target identifiers with the current callable signature of its allowlisted v32 delegate. A missing delegate or required parameter fails the audit.

## Durable replay protection

Confirmation claims are persisted as append-only `AuditLog` records using the confirmation SHA-256 digest as the target value. Duplicate checks therefore survive process restarts and multiple application workers sharing the same database.

The execution result is recorded separately with:

- case ID
- governance action
- delegate service
- confirmation digest
- result reference digest
- authoritative record identifiers

## Result and workspace linkage

Successful execution responses now include:

- durable confirmation-claim audit record
- execution audit record
- authoritative record identifiers extracted from the delegate result
- result reference SHA-256
- refreshed canonical v33 workspace
- refreshed workspace SHA-256

## Boundaries

- no automatic action execution
- no generic dynamic imports
- no duplicate governance backend
- no direct transport implementation
- no access-scope change
- no migration required; existing append-only audit storage is reused

# v25.0 Cross-Case Intelligence Workspace

Introduces a read-only, human-review-first workspace for candidate correlations across entities, identifiers, infrastructure, evidence, timelines, and repeated patterns in multiple cases.

The workspace derives candidate correlations from existing case-targeted audit details. It does not create a parallel intelligence store and does not treat a shared value as a confirmed identity, relationship, or evidentiary fact.

Every correlation preserves case-level provenance:

- case ID
- source audit-record ID
- source action
- field path
- actor
- source timestamp
- provenance SHA-256

Access controls are applied before correlation. When the session supplies `allowed_case_ids`, only those cases and their occurrences may contribute to results. An empty or invalid case-access scope exposes no case data. Without an explicit case list, the workspace uses all cases otherwise visible to the authenticated session.

Candidate categories:

- entities and subject/profile references
- identifiers such as usernames, handles, email addresses, phone numbers, account IDs, and external IDs
- infrastructure such as domains, hostnames, IP addresses, URLs, and endpoints
- evidence references including evidence, artifact, claim, assertion, source, capture, document, and media IDs
- timeline values and event references
- repeated source actions and repeated blocker patterns across cases

Routes:

- `GET /cross-case-intelligence`
- `GET /api/v1/cross-case-intelligence`

The optional `minimum_case_count` query parameter controls the minimum number of visible cases required for a candidate correlation. Its enforced minimum is two.

All outputs are candidate correlations requiring human review. v25.0 is read-only: it creates no correlation record, mutates no source event, introduces no connector execution or collection activity, and requires no migration.

# v38.8 — Public Discovery and Capture Workspace

## Objective

Provide one administrator-only, read-only integration surface for the v38 public discovery and capture program. The workspace combines sanitized status from discovery requests, policy gates, passive candidates, synthetic provenance, accepted artifacts, source records, independence assessments, operational imports, Browsertrix enablements, capture triage, and uncertain execution recovery.

The workspace does not become a collection, execution, review, evidence, import, observation, dossier, export, or publication authority.

## Routes

- `GET /public-discovery-capture`
- `GET /api/v1/public-discovery-capture/workspace`

Both routes require an authenticated administrator. No POST, PUT, PATCH, or DELETE route is introduced.

## Safe projections

The workspace constructs explicit projections rather than serializing authoritative records directly.

Allowed fields include:

- stable record IDs;
- case and approved-domain scope;
- status, decision, state, and review flags;
- sanitized URLs already held by source records;
- counts and timestamps;
- content-hash prefixes rather than full hash-bound authority records;
- non-sensitive resource-limit summaries;
- ledger consistency and uncertain-outcome status.

The workspace excludes:

- raw page, PDF, WARC, WACZ, screenshot, archive, or response content;
- credentials, cookies, authorization headers, authenticated browser state, or account references;
- full authorization, confirmation, certification, runtime-authorization, or policy bindings;
- confirmation SHA-256 values;
- private storage paths or approved storage roots;
- container command lines, environment variables, image-control details, or process output;
- raw audit metadata and execution history;
- arbitrary nested collection context or provenance metadata.

## Summary and findings

The workspace summarizes:

- discovery request and allow/block gate counts;
- passive batch and candidate counts;
- synthetic capture and completed-provenance counts;
- artifact and accepted-artifact counts;
- source and independence-group counts;
- operational-import counts;
- production-enablement and active/claimed counts;
- capture-triage and support-eligible counts;
- uncertain execution counts.

Read-only findings identify:

- blocked discovery gates;
- quarantined passive candidates;
- incomplete synthetic provenance;
- candidate-review captures;
- out-of-scope captures;
- unconfirmed mirror proposals;
- active or claimed Browsertrix enablements;
- uncertain execution outcomes.

Each finding points to the existing authority that must be reviewed. The workspace provides no action to resolve it.

## Authoritative reuse

- v38.1 remains authoritative for discovery requests and crawl manifests;
- v38.2 remains authoritative for source, scope, robots, terms, access, query, and resource decisions;
- v38.3 remains authoritative for passive candidate normalization;
- v38.4 remains authoritative for synthetic capture provenance;
- v29 remains authoritative for artifacts and acceptance;
- v36.1 remains authoritative for source registration;
- v36.4 remains authoritative for source independence;
- v37.1 remains authoritative for import envelopes;
- v38.6.4 remains authoritative for Browsertrix enablement, claim, and revocation;
- v35 remains authoritative for durable execution and uncertain-outcome recovery;
- v38.7 remains authoritative for duplicate, change, relevance, mirror-proposal, and handoff triage.

## Safety controls

The workspace declares and enforces:

- read-only operation;
- safe projections only;
- no raw content, credential, cookie, private-path, command, or confirmation-hash exposure;
- no automatic collection or retry;
- no automatic artifact acceptance;
- no automatic source-independence assessment;
- no automatic observation promotion;
- no automatic truth assignment;
- no automatic entity merge;
- no automatic claim approval;
- no automatic dossier mutation;
- no automatic import staging;
- no automatic export or publication;
- no write actions exposed by the workspace.

## Browser E2E

The Chromium browser test runs against a temporary SQLite database and the registered application. It verifies:

- administrator login reaches the workspace;
- every safety marker is rendered;
- the empty recovery state states that automatic replay is unavailable;
- no form, button, POST method, collection, execution, retry, artifact-acceptance, independence-assessment, promotion, merge, approval, dossier, export, or publication control is present;
- sensitive field names are absent from rendered HTML;
- the JSON API reports read-only mode, safe projections, and an empty write-action list.

The E2E test performs no public network request and uses no real case evidence.

## Acceptance criteria

- unauthenticated HTML redirects to login;
- unauthenticated API returns 401;
- non-administrators receive 403;
- administrators receive HTML and JSON read models;
- safe projections omit all prohibited values;
- blocked, pending-review, active-enablement, and uncertain states are visible as findings;
- the workspace exposes no mutation controls;
- route registration occurs through the existing analytic-review chain;
- focused service, route, and Chromium E2E tests pass;
- full CI, Full Verification, legacy readiness, PostgreSQL checks, migration/backup/boot checks, and the combined v32-v38 browser workflow pass.

## Validation

```bash
pytest -q \
  tests/test_v38_8_public_discovery_capture_workspace.py \
  tests/test_v38_8_public_discovery_capture_workspace_routes.py
python scripts/run_v38_8_public_discovery_capture_browser_e2e.py
```

## Next authority

After v38.8 is merged and green, v38.9 may run the controlled fictional end-to-end pilot, record exact release evidence, and formally close the v38 program. v38.9 must not introduce new runtime, network, schema, migration, or authority behavior.

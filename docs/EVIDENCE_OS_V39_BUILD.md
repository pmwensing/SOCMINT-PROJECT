# Evidence OS v39 Build

## Purpose

V39 adds a governed evidence-to-claim analysis layer without allowing an adapter, parser, analyst helper or model to assign truth, approve a claim, merge an entity, mutate a dossier, publish, or file evidence automatically.

The governed flow is:

```text
Immutable evidence
    -> proposed observation
    -> human observation review
    -> proposed finding
    -> source-backed finding approval
    -> conservative claim-proof projection
    -> separate dossier decision
```

## Delivered in v39.0 through v39.2

### v39.0 — Evidence foundation

- Immutable evidence item registry with SHA-256 deduplication.
- Per-case evidence keys and source metadata.
- Proposed observations linked to source evidence.
- Human review states: `approved`, `rejected`, and `needs_work`.
- Audit events for evidence ingestion and observation review.

### v39.1 — Governed findings

- Proposed findings linked to observations.
- Controlled fact, allegation, inference and question classifications.
- Approval blocked without approved source observations.
- Cross-case observation contamination rejected.
- Findings linkable to claims, proceedings, issues, timeline events and entities.

### v39.2 — Evidence analysis

- Support, contradiction, qualification, duplicate and context relationships.
- Controlled source-quality classes and bounded quality scores.
- Effective confidence derived from analyst confidence and source quality.
- Conservative claim-proof states: `unproven`, `context-only`, `supported`, `corroborated` and `contested`.
- Coverage based on approved findings, approved observations and distinct evidence sources.

## v39.3 — 46 Montreal Street adapter controls

The case adapter is restricted to canonical case key `46MONST` and supports three modes:

- `off`
- `passive`
- `on`

`passive` is the fail-safe default.

The effective mode is the least permissive of the system maximum, case mode and one-run requested mode.

### Off

- Blocks adapter inventory, validation, preview, projection and import authorization.
- Preserves existing records and audit history.
- Cannot transition directly to `on`.

### Passive

May inventory, validate, prepare a deterministic import plan, calculate claim-proof and timeline projections, and produce scope-compliance reports.

It cannot execute an authoritative import, assign truth, approve claims, merge entities, mutate a dossier, publish, submit evidence, or trigger public-web collection.

Every passive report ends with:

```text
No authoritative case records were changed.
```

### On — controlled import eligibility

`on` does not itself import records. It only makes `execute_controlled_import` eligible after:

- explicit operator confirmation;
- an attributable actor and reason;
- a valid approved import-plan SHA-256;
- a prior passive review path.

Execution requires a second explicit confirmation and exact equality with the active import-plan SHA-256.

### Audit and storage boundary

Mode history reuses the existing append-only `AuditLog` authority through:

- `case_adapter_system_mode_changed`
- `case_adapter_mode_changed`

The mode controller creates no competing evidence, observation, claim, entity, timeline or dossier authority.

### Case scope

The adapter preserves distinct pre-fire and post-fire lockout proceeding scopes.

For 71 Cowdy Street it includes only:

- upstairs noise;
- the water leak.

All other Cowdy Street issues are excluded, and the Cowdy Street landlord must not be characterized adversely.

## Next increments

### v39.4 — Timeline and responsibility chains

- Timeline events linked to evidence-backed findings.
- Notice, opportunity, response, failure and consequence chains.
- Conflict-preserving chronology and unresolved-date handling.

### v39.5 — Case-intelligence workspace

- Authenticated, case-scoped read views.
- Adapter status and mode controls.
- Passive preview, claim-proof coverage and integrity findings.
- No direct truth, merge, dossier, export or publication controls.

### v39.6 — Controlled 46 Montreal import execution

- Deterministic import-plan creation and approval.
- Idempotent, replay-protected execution.
- Existing-authority reuse.
- Dry-run and fictional pilot before real case data.

## Verification targets

```bash
pytest -q \
  tests/test_v39_0_evidence_os.py \
  tests/test_v39_1_evidence_findings.py \
  tests/test_v39_2_evidence_analysis.py \
  tests/test_v39_3_montreal_46_adapter_control.py
```

The release must not be merged until focused tests and normal repository release gates pass against the exact PR head.

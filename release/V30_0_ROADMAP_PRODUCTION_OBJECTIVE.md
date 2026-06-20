# v30.0 — Corroboration, Analytic Confidence, and Review

## Program objective

Convert accepted collection outputs into explainable, reviewable, and explicitly confidence-scored analytic contributions without collapsing evidence, observations, assessments, or human judgment into one opaque result.

v30 begins after the v29 collection program proved authorized ingestion, provenance, quality, trust, and human-controlled dossier eligibility. The next gap is the analytic layer between accepted observations and consequential dossier conclusions.

## Primary workspace

**Analytic Review Workspace**

v30.0 now implements the initial read-only workspace. It inventories existing evidence, observations, claims, confidence records, review decisions, contradictions, and dossier contribution readiness before any new write contract is introduced.

## Roadmap

| Slice | Title | Purpose | Status |
|---|---|---|---|
| v30.0 | Analytic Review Workspace and Planning Baseline | Establish the inventory, route, findings, and safe program boundaries. | Implemented |
| v30.1 | Corroboration Claim Contract | Define append-only analytic claims with explicit case, entity, actor, purpose, and source bindings. | Planned |
| v30.2 | Evidence and Observation Linkage | Bind claims to immutable evidence and normalized observations using deterministic hashes. | Planned |
| v30.3 | Contradiction and Disagreement Handling | Preserve conflicting evidence and analyst disagreement without destructive overwrite. | Planned |
| v30.4 | Confidence Model and Explainability | Produce bounded confidence assessments with visible inputs, limitations, and reasons. | Planned |
| v30.5 | Human Analytic Review and Decision Record | Require explicit analyst review before consequential use. | Planned |
| v30.6 | Dossier Contribution and Reassessment | Approve, hold, reject, or reassess analytic contributions while preserving prior decisions. | Planned |
| v30.7 | Product Review and Browser E2E Checkpoint | Validate the complete browser workflow and close v30 only after all gates pass. | Planned |

## Entry-gate definition

The entry gate is now `v30_0_read_only_baseline_implemented`:

- roadmap, production objective, primary workspace, and workflow spine are explicit;
- existing evidence, observation, confidence, review, and dossier contracts are reused;
- runtime and routes exist for the read-only baseline;
- no migration was introduced;
- closure gates remain defined before write-path implementation begins.

## Production boundaries

v30 must not:

- execute connectors;
- rewrite raw evidence or observations;
- assign truth automatically;
- assign high confidence automatically;
- mutate dossiers automatically;
- change case access;
- expose credentials or secrets;
- add a migration without a proven schema gap.

## Production invariants

- Evidence, observations, claims, confidence, and review decisions remain distinct layers.
- Contradictory evidence is preserved rather than silently discarded.
- Confidence is explainable and is never represented as truth.
- Consequential use requires human review.
- Bindings are deterministic and append-only.
- Reassessment preserves earlier decisions and their supporting context.
- Dossier contribution requires explicit approval.

## v30.0 implementation

The read-only Analytic Review Workspace provides:

- existing evidence and observation inventory;
- existing dossier assertion and confidence inventory;
- review-item and review-decision inventory;
- contradiction findings for conflicting normalized claim values;
- collection-quality and dossier-contribution readiness summaries;
- explicit no-mutation and no-execution guarantees;
- administrator-only UI and API routes;
- focused tests.

## Validation contract

```bash
python3 -m pytest -q tests/test_v30_0*.py
python3 -m pytest -q tests/test_v30*.py
python3 -m pytest -q
```

The program remains open. The next implementation target is v30.1 Corroboration Claim Contract.

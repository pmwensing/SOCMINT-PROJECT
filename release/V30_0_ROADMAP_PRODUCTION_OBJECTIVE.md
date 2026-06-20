# v30.0 — Corroboration, Analytic Confidence, and Review

## Program objective

Convert accepted collection outputs into explainable, reviewable, and explicitly confidence-scored analytic contributions without collapsing evidence, observations, assessments, or human judgment into one opaque result.

v30 begins after the v29 collection program proved authorized ingestion, provenance, quality, trust, and human-controlled dossier eligibility. The next gap is the analytic layer between accepted observations and consequential dossier conclusions.

## Primary workspace

**Analytic Review Workspace**

The initial workspace should be read-only. It should inventory existing evidence, observations, candidate claims, corroboration relationships, contradictions, confidence records, human review decisions, and dossier contribution readiness before any new write contract is introduced.

## Roadmap

| Slice | Title | Purpose |
|---|---|---|
| v30.0 | Analytic Review Workspace and Planning Baseline | Establish the inventory, route, findings, and safe program boundaries. |
| v30.1 | Corroboration Claim Contract | Define append-only analytic claims with explicit case, entity, actor, purpose, and source bindings. |
| v30.2 | Evidence and Observation Linkage | Bind claims to immutable evidence and normalized observations using deterministic hashes. |
| v30.3 | Contradiction and Disagreement Handling | Preserve conflicting evidence and analyst disagreement without destructive overwrite. |
| v30.4 | Confidence Model and Explainability | Produce bounded confidence assessments with visible inputs, limitations, and reasons. |
| v30.5 | Human Analytic Review and Decision Record | Require explicit analyst review before consequential use. |
| v30.6 | Dossier Contribution and Reassessment | Approve, hold, reject, or reassess analytic contributions while preserving prior decisions. |
| v30.7 | Product Review and Browser E2E Checkpoint | Validate the complete browser workflow and close v30 only after all gates pass. |

## Entry-gate definition

Planning may be considered complete when:

- the roadmap, production objective, primary workspace, and workflow spine are explicit;
- existing evidence, observation, confidence, review, and dossier contracts have been inventoried;
- no authoritative equivalent workspace or route already exists;
- claim, corroboration, contradiction, confidence, and review boundaries are defined;
- runtime code, routes, and migrations remain absent until the baseline inventory proves the need;
- closure gates are defined before implementation begins.

The current entry-gate status is `planning_complete_runtime_not_started`.

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

## First implementation target

v30.0 should add a read-only Analytic Review Workspace with:

- an inventory of existing analytic and evidence records;
- candidate claim and corroboration summaries;
- contradiction and disagreement findings;
- confidence and review readiness findings;
- route and migration drift checks;
- no analytic mutation;
- no dossier mutation;
- focused tests and a release note.

## Validation contract

Each v30 slice must provide focused tests. Program closure requires:

```bash
python3 -m pytest -q tests/test_v30*.py
python3 -m pytest -q
python3 scripts/run_v30_7_analytic_review_browser_e2e.py --json
```

The program remains open until the v30.7 browser report records zero failures and the planning contract explicitly marks `v30_closed` as true.

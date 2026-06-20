# v30.0 — Corroboration, Analytic Confidence, and Review

## Program objective

Convert accepted collection outputs into explainable, reviewable, and explicitly confidence-scored analytic contributions without collapsing evidence, observations, assessments, or human judgment into one opaque result.

## Primary workspace

**Analytic Review Workspace**

v30.0 implements the read-only workspace. v30.1 adds append-only corroboration claims. v30.2 binds those claims to accepted evidence and observations. v30.3 preserves contradictions and disagreements. v30.4 adds bounded explainable confidence assessments. v30.5 adds explicit human review and reassessment records. v30.6 adds a separate append-only dossier-contribution gate. v30.7 adds the product-review checkpoint and browser E2E runner.

## Roadmap

| Slice | Title | Purpose | Status |
|---|---|---|---|
| v30.0 | Analytic Review Workspace and Planning Baseline | Establish the inventory, route, findings, and safe program boundaries. | Implemented |
| v30.1 | Corroboration Claim Contract | Define append-only analytic claims with explicit case, entity, actor, purpose, and source bindings. | Implemented |
| v30.2 | Evidence and Observation Linkage | Bind claims to immutable evidence and normalized observations using deterministic hashes. | Implemented |
| v30.3 | Contradiction and Disagreement Handling | Preserve conflicting evidence and analyst disagreement without destructive overwrite. | Implemented |
| v30.4 | Confidence Model and Explainability | Produce bounded confidence assessments with visible inputs, limitations, and reasons. | Implemented |
| v30.5 | Human Analytic Review and Decision Record | Require explicit analyst review before consequential use. | Implemented |
| v30.6 | Dossier Contribution and Reassessment | Approve, hold, reject, withdraw, or reassess analytic contributions while preserving prior decisions. | Implemented |
| v30.7 | Product Review and Browser E2E Checkpoint | Validate the complete browser workflow and close v30 only after all gates pass. | Checkpoint implemented; validation pending |

## Implemented boundaries

- Claims, source linkages, conflict events, confidence assessments, human reviews, and dossier-contribution decisions are append-only.
- Human approval requires substantial confidence and no unresolved analytic conflict.
- Dossier-contribution approval requires the latest human review to remain approved.
- Review and contribution reassessments preserve every prior decision and record the superseded record ID.
- Contribution approval records eligibility only; it does not mutate a dossier automatically.
- Product review checks modules, assets, routes, duplicate routes, and unexpected v30 migrations.
- Browser E2E checks the workspace, product review, core analytic APIs, and checkpoint readiness.
- Claims, evidence, observations, confidence records, reviews, and dossiers are not rewritten.
- No database migration was introduced.

## Closure validation contract

```bash
python3 -m pytest -q tests/test_v30_7*.py
python3 -m pytest -q tests/test_v30*.py
python3 -m pytest -q
python3 scripts/run_v30_7_analytic_review_browser_e2e.py --json
```

v30 remains open until all four gates pass and the planning contract explicitly records `v30_closed: true`.

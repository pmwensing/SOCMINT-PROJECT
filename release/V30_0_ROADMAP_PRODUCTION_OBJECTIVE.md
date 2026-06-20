# v30.0 — Corroboration, Analytic Confidence, and Review

## Program objective

Convert accepted collection outputs into explainable, reviewable, and explicitly confidence-scored analytic contributions without collapsing evidence, observations, assessments, or human judgment into one opaque result.

## Primary workspace

**Analytic Review Workspace**

v30.0 implements the read-only workspace. v30.1 adds append-only corroboration claims. v30.2 binds those claims to accepted evidence and derived observations through deterministic source manifests.

## Roadmap

| Slice | Title | Purpose | Status |
|---|---|---|---|
| v30.0 | Analytic Review Workspace and Planning Baseline | Establish the inventory, route, findings, and safe program boundaries. | Implemented |
| v30.1 | Corroboration Claim Contract | Define append-only analytic claims with explicit case, entity, actor, purpose, and source bindings. | Implemented |
| v30.2 | Evidence and Observation Linkage | Bind claims to immutable evidence and normalized observations using deterministic hashes. | Implemented |
| v30.3 | Contradiction and Disagreement Handling | Preserve conflicting evidence and analyst disagreement without destructive overwrite. | Next |
| v30.4 | Confidence Model and Explainability | Produce bounded confidence assessments with visible inputs, limitations, and reasons. | Planned |
| v30.5 | Human Analytic Review and Decision Record | Require explicit analyst review before consequential use. | Planned |
| v30.6 | Dossier Contribution and Reassessment | Approve, hold, reject, or reassess analytic contributions while preserving prior decisions. | Planned |
| v30.7 | Product Review and Browser E2E Checkpoint | Validate the complete browser workflow and close v30 only after all gates pass. | Planned |

## Implemented boundaries

- v30.0 remains read-only.
- v30.1 claim creation and withdrawal are append-only.
- v30.2 linkage records are append-only and validate accepted artifacts, observations, and observation-to-artifact consistency.
- Claim, evidence, and observation records are not rewritten.
- Truth, confidence, review completion, and dossier eligibility are not assigned.
- No database migration was introduced.

## Production invariants

- Evidence, observations, claims, confidence, and review decisions remain distinct layers.
- Contradictory evidence is preserved rather than silently discarded.
- Confidence is explainable and is never represented as truth.
- Consequential use requires human review.
- Bindings are deterministic and append-only.
- Reassessment preserves earlier decisions and their supporting context.
- Dossier contribution requires explicit approval.

## Validation contract

```bash
python3 -m pytest -q tests/test_v30_0*.py tests/test_v30_1*.py tests/test_v30_2*.py
python3 -m pytest -q tests/test_v30*.py
python3 -m pytest -q
```

The program remains open. The next implementation target is v30.3 Contradiction and Disagreement Handling.

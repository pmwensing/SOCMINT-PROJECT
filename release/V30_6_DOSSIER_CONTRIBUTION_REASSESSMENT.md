# v30.6 — Dossier Contribution and Reassessment

## Objective

Require a separate, explicit dossier-contribution decision after human analytic review while preserving reassessments and preventing automatic dossier mutation.

## Delivered

- append-only analytic dossier-contribution records
- decisions: approved, held, rejected, and withdrawn
- deterministic bindings to the claim and latest human-review decision
- approval restricted to claims whose latest human review is approved and authorizes consequential use
- explicit target dossier section, rationale, administrative reason, and confirmation
- withdrawal restricted to a previously approved contribution
- reassessment records that supersede but never erase prior contribution decisions
- current-decision and full-history inventories
- contribution summaries and approved-review waiting findings in the Analytic Review Workspace
- administrator-only list and create APIs
- focused contract and route tests

## Routes

- `GET /api/v1/analytic-review/dossier-contributions`
- `GET /api/v1/analytic-review/claims/<claim_id>/dossier-contributions`
- `POST /api/v1/analytic-review/claims/<claim_id>/dossier-contributions`

## Boundaries

Approval records eligibility for contribution through the existing dossier pipeline. It does not write to or alter a dossier automatically. No claim, review, confidence, evidence, observation, connector, or schema mutation is performed.

## Next action

Validate v30.6 and proceed to v30.7 Product Review and Browser E2E Checkpoint.

# v34 Release Evidence

## Release identity

- Program: Operational Case Governance Actions and Human-Confirmed Execution Workspace
- Pull request: #281
- Final validated branch head: `6921231cbabba411a2a6ba5d943e04906d09a66a`
- Squash merge commit on `master`: `b9ca3f713ee29227c15746a77781199afc003ec0`
- Merged: 2026-06-23
- Rollback reference: parent of merge commit `b9ca3f713ee29227c15746a77781199afc003ec0`

## Exact-head validation evidence

All required checks passed on the final branch head before merge:

- CI run 3926 — success
- SOCMINT Full Verification run 959 — success
- SOCMINT v12.10.19 Verify run 2247 — success
- SOCMINT v32.7, v33.7 and v34.7 Browser E2E run 93 — success

The CI run included lint, the complete test suite, publication browser regression, export gate verification, Docker Compose validation, Alembic smoke, backup/restore smoke, production boot smoke, and dependency audit.

The squash merge itself did not create a separate PR-triggered workflow run. The exact validated source tree was protected with the expected head SHA during merge.

## Delivered routes

- `GET /api/v1/dissemination-governance/cases/<case_id>/action-eligibility`
- `POST /api/v1/dissemination-governance/cases/<case_id>/actions/<action>/confirmation`
- `POST /api/v1/dissemination-governance/cases/<case_id>/actions/<action>/execute`
- `GET /dissemination-governance/v34-product-review`
- `GET /api/v1/dissemination-governance/v34-product-review`

## Delivered action families

- audience, package, and authorization
- delivery and receipt
- feedback and correction
- recall and retention

## Preserved controls

- v32 services remain authoritative
- v33 remains the canonical case read surface
- action eligibility is checked before confirmation
- every mutating action requires explicit confirmation
- delegates are selected from an explicit allowlist
- duplicate confirmation is rejected
- automatic and broad bulk execution remain unavailable
- no transport implementation, access change, or schema migration was introduced by v34

## Post-merge status

- `master` contains merge commit `b9ca3f713ee29227c15746a77781199afc003ec0`
- merged branch `feat/v34-0-planning-entry-gate` is no longer present
- no separate post-merge workflow status exists because the validation workflows are pull-request triggered

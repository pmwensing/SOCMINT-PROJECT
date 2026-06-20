# v29.6 — Collection Quality, Trust, and Dossier Contribution

## Production objective

Require collection outputs to prove quality, provenance integrity, trust, and dossier value before consequential use.

## Delivered

- deterministic artifact quality scoring from chain of custody, provenance bindings, acceptance state, observation yield, and duplicate status
- explicit trust tiers: `untrusted`, `limited`, `supported`, and `trusted`
- append-only quality assessments bound to immutable evidence events
- explicit human dossier-contribution decisions: `approved`, `held`, or `rejected`
- approval restricted to supported or trusted assessments
- collection quality workspace, API routes, operator UI, findings, review queue, and focused regression coverage

## Safety and architecture invariants

- no connector execution
- no raw evidence rewrite
- no automatic dossier mutation
- no automatic consequential use
- append-only audit history
- deterministic bindings and hashes
- human review required for dossier contribution

## Next action

Validate the v29.6 focused and full regression gates, then proceed to v29.7 Product Review and Browser E2E Checkpoint.

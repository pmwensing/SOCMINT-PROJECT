# v12.10.31H — Retire stale 31F route-string assertion

Problem:
- v12.10.31G moved route validation to endpoint-suffix based detection.
- The older v12.10.31F test still asserts `summary["missing_v12_routes"] == 0`.
- That test is stale because the audit now tracks endpoint suffixes as the authoritative runtime route proof.

Fix:
- Rewrite the 31F compatibility test to accept the newer endpoint-suffix route proof.
- Update 31G test runner so it does not fail on obsolete exact route-string assumptions.
- Preserve the real blocker: schema/model migration drift.

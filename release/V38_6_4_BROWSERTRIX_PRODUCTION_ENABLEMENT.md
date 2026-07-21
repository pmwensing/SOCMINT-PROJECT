# v38.6.4 — Certification-Bound Browsertrix Production Enablement

## Objective

Add the only production-enablement authority for the v38.6 Browsertrix runtime. A passing deployment certification may support a separate, time-bounded, single-use grant for one exact production execution plan. The grant cannot broaden the certified runtime, image, network, storage root, or resource limits.

## Authority chain

`passing v38.6.3 certification → exact production execution plan → time-bounded enablement → single-use operator claim → v38.6.2 production runtime preparation → v35 durable execution identity → one runtime attempt`

The certification proves deployment infrastructure. The production plan remains independently bound to its v38.1 request, v38.2 policy gate, v38.5 public HTTP preflight, and v38.6 Browsertrix request controls.

## Enablement issuance

`issue_production_enablement` requires:

- explicit reviewer confirmation and reason;
- a prepared v38.6.3 certification plan;
- a passing v38.6.3 certification result with every required proof true;
- exact certification-plan, runtime-request, and SHA-256 bindings;
- a separate prepared production execution plan;
- a deployment policy explicitly set to production mode;
- exact production case and approved-domain scope;
- a non-fictional production domain;
- production resource limits equal to or narrower than certification limits;
- the same runtime, pinned image digest, isolated network, and approved storage root used by certification;
- an exact deployment and execution-plan binding;
- an issued, valid-from, and expiry time;
- a maximum enablement duration of 24 hours.

The issued grant is append-only, deterministic, idempotent, operator-action-required, single-use, and non-automatic.

## Single-use claim

`claim_production_enablement` requires:

- the exact enablement ID and SHA-256;
- an active, unclaimed, unrevoked enablement;
- the exact authorized production execution plan;
- a claim time inside the enablement window;
- explicit operator confirmation and reason.

The resulting runtime authorization binds:

- enablement ID and SHA-256;
- deployment, case, and approved domain;
- production execution-plan ID and SHA-256;
- runtime, image digest, network, and storage root;
- authorized resource limits;
- claim and expiry times;
- single-use, no automatic execution, and no automatic retry.

## Runtime enforcement

The v38.6.2 runtime now requires an explicit execution mode.

### Deployment certification mode

- requires an explicit certification-run flag;
- accepts only `.test` targets;
- rejects production authorization;
- remains suitable for deployment-only fictional fixture certification.

### Production mode

- requires a claimed v38.6.4 runtime authorization;
- validates exact plan, deployment, case, domain, runtime, image, network, storage, and time bindings;
- checks the persisted enablement is still claimed and not revoked;
- rejects broadened or mismatched scope;
- records a unique v35 durable execution identity before starting the process;
- rejects duplicate use of the same runtime authorization;
- transitions the durable execution to succeeded, failed, or uncertain;
- never automatically retries failed or uncertain execution.

An exception before the process outcome is known becomes `uncertain`. A result-loader failure after an external effect also becomes `uncertain`. Neither condition is replayed.

## Revocation

`revoke_production_enablement` may revoke an active or claimed enablement with explicit reviewer confirmation, timestamp, and reason. Production runtime preparation requires the current persisted state to remain claimed; a revoked grant cannot be prepared for execution.

## Safety boundary

This slice does not:

- automatically issue or claim enablement;
- issue grants longer than 24 hours;
- authorize more than one execution identity;
- permit production limits broader than certification;
- permit runtime, image, network, storage-root, case, domain, or execution-plan drift;
- permit `.test` or `.invalid` domains as production targets;
- permit credentials, cookies, profiles, forms, uploads, CAPTCHA bypass, shell execution, privilege, host networking, image pulls, scope growth, or automatic retry;
- register artifacts or sources;
- create imports or observations;
- assign truth, merge entities, approve claims, mutate dossiers, export, or publish.

## Persistence and replay protection

Enablement issuance, claim, and revocation are append-only AuditLog events. Production execution reuses the v35 durable execution ledger with the runtime-authorization SHA-256 as the unique confirmation identity. A second execution attempt with the same authorization is blocked before the process runner is called.

## Validation

```bash
pytest -q \
  tests/test_v38_6_2_browsertrix_container_runtime.py \
  tests/test_v38_6_3_browsertrix_deployment_certification.py \
  tests/test_v38_6_4_browsertrix_production_enablement.py
```

## Next authority

After this slice is merged and green, v38.7 may implement duplicate, mirror, recapture, change, relevance, and scope triage for accepted public-web captures. v38.7 must not alter this production execution authority or automatically promote captures into observations, claims, dossiers, exports, or publication.

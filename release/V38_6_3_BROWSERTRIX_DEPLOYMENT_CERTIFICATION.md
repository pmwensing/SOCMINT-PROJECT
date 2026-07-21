# v38.6.3 — Browsertrix Deployment Certification Gate

## Objective

Add a deployment-only certification contract behind the disabled-by-default v38.6.2 container runtime. Certification proves a locally pinned Browsertrix deployment can reach one fictional approved fixture while external egress remains blocked, storage controls hold, cleanup completes, and the resulting preservation envelope validates.

Passing certification does not enable production execution.

## Browsertrix output compatibility

The v38.6 preservation validator now accepts both supported screenshot evidence forms:

- a separate PNG or JPEG screenshot; or
- a Browsertrix screenshot WARC archive such as `screenshots.warc.gz`.

Crawl metadata may be JSON or JSONL/NDJSON. The WACZ and crawl-metadata requirements remain mandatory, and at least one screenshot-evidence form remains mandatory.

This is an additive output-profile change. Existing PNG/JPEG and JSON fixtures remain valid.

## Certification preparation

`prepare_deployment_certification` requires:

- an exact prepared v38.6.2 runtime request;
- a runtime that is explicitly enabled only for the deployment certification attempt;
- the exact runtime and execution-plan hashes;
- an isolated deployment or staging environment;
- explicit operator confirmation and an administrative reason;
- one fictional `.test` fixture URL already bound to the execution plan;
- one `.invalid` external-egress probe URL;
- the expected SHA-256 of the fictional fixture content;
- all v38.6.2 network-containment attestations;
- exact approved storage bindings;
- standard-CI live execution disabled;
- production enablement not requested;
- one attempt and no automatic retry.

The certification plan is deterministic and hash-bound.

## Certification execution

`execute_deployment_certification` uses an injected deployment executor and requires exact observation bindings for:

- certification plan ID and SHA-256;
- runtime request ID and SHA-256;
- fixture and probe URLs;
- successful fictional fixture response and content hash;
- external probe attempted but blocked with no response;
- isolated network, DNS, egress, and target-binding enforcement;
- no successful network host other than the approved fixture host;
- one attempt with no automatic retry;
- exact storage path and approved-root bindings;
- completed cleanup and no output quarantine requirement;
- a valid v38.6.1 execution result;
- a valid v38.6 preservation manifest.

Failure, executor exception, containment drift, storage mismatch, unexpected successful host, invalid preservation output, or an unblocked external probe becomes an explicit failed or blocked result. It is never silently retried.

## Standard CI boundary

Standard CI remains fully offline. Tests use a fake certification executor and fictional records. They do not launch Docker, Podman, Browsertrix, Chromium, DNS, HTTP, or a local fixture server.

A real certification run is deployment-only and must use:

- a locally pinned image digest;
- the v38.6.2 isolated egress-controlled network;
- temporary approved private storage;
- a fictional local HTTP fixture mapped to a `.test` hostname;
- a blocked `.invalid` probe;
- deployment-specific cleanup and evidence retention.

## Safety boundary

This slice does not:

- grant production enablement;
- change the pinned Browsertrix image version;
- permit arbitrary domains, credentials, cookies, profiles, forms, uploads, CAPTCHA bypass, or off-domain navigation;
- permit standard CI live execution;
- add automatic retry;
- register artifacts or sources;
- create imports or observations;
- assign truth, merge entities, approve claims, mutate dossiers, export, or publish.

## Acceptance criteria

- old separate-screenshot output fixtures remain valid;
- screenshot WARC plus WACZ plus JSONL metadata validates;
- missing screenshot evidence remains blocked;
- plans are deterministic and exact-runtime-bound;
- only `.test` fixture and `.invalid` probe targets are accepted;
- external egress success fails certification;
- unexpected successful hosts fail certification;
- cleanup and storage bindings are mandatory;
- successful certification records all required proofs;
- `production_enablement_granted` is always false.

## Validation

```bash
pytest -q \
  tests/test_v38_6_browsertrix_preservation.py \
  tests/test_v38_6_1_browsertrix_execution.py \
  tests/test_v38_6_2_browsertrix_container_runtime.py \
  tests/test_v38_6_3_browsertrix_deployment_certification.py
```

## Next authority

After a deployment produces a separately reviewed passing certification record, v38.6.4 may add a certification-bound production enablement gate. That gate must be disabled by default, deployment-specific, time-bounded, exact-certification-bound, revocable, and unable to broaden case, domain, storage, image, network, or resource scope.

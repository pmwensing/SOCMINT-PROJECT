# v38.6 — Browsertrix Preservation Request and Result-Envelope Gates

## Objective

Add the governance contracts needed before any real Browsertrix process execution is introduced.

This slice prepares a deterministic, case-scoped Browsertrix preservation request and validates a returned hash-bound preservation package. It does **not** launch Browsertrix, perform a network request, register evidence, promote observations, mutate dossiers, export, or publish.

## Entry conditions

- v38.5 is merged and green.
- The discovery request exists under v38.1.
- The v38.2 decision allows the request and marks it live-network eligible.
- Robots and terms decisions allow execution.
- A successful v38.5 public HTTP capture is bound to the same request, gate, and URL.
- The operator provides an explicit JavaScript-rendering justification, administrative reason, execution identity, approved private-storage target, bounded resource limits, and confirmation.

## Request gate

`prepare_browsertrix_request` produces a deterministic request ID and SHA-256 over:

- case, purpose, collection-job, discovery-request, gate, and execution bindings;
- requested URL and approved domain;
- JavaScript justification and operator reason;
- Browsertrix adapter identity;
- private storage target;
- content-type and resource limits;
- v38.5 capture/content hash binding;
- disabled authentication, credentials, supplied cookies, saved profiles, form submission, file upload, CAPTCHA bypass, automatic retries, and off-domain navigation.

## Result-envelope gate

`validate_browsertrix_result` requires:

- exact request ID, request hash, execution ID, and URL binding;
- same-domain final URL and redirects;
- completed status and valid UTC timestamps;
- Browsertrix and browser versions;
- page/download/redirect metrics within approved limits;
- WACZ, screenshot, and crawl-metadata outputs;
- valid filename, media type, byte count, and SHA-256 for each output;
- deterministic preservation-manifest SHA-256.

WARC may be supplied as an additional output. Raw output bytes remain in approved private storage and are not written to the result envelope.

## Safety and authority boundaries

This slice contains no subprocess, container, queue, browser, DNS, HTTP, or live-network execution path. The result validator accepts metadata supplied by a future execution authority; it does not claim the process ran merely because a request was prepared.

Validated output remains unregistered. A later step must explicitly route outputs through existing v29.4 artifact acceptance, v36.1 source registration, and v37 import review controls.

The module cannot create observations, assign truth, merge entities, approve claims, mutate dossiers, export, or publish.

## Validation

```bash
pytest -q tests/test_v38_6_browsertrix_preservation.py
```

Tests use fictional URLs and metadata only.

## Next action

After this gate is merged and green, add a separately controlled Browsertrix execution adapter that consumes only a prepared request and returns only a result matching this envelope. Keep process execution, artifact acceptance, and analytical promotion as separate authorities.

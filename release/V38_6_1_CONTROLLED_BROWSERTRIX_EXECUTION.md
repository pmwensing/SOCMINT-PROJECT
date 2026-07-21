# v38.6.1 — Controlled Browsertrix Execution Gate

## Objective

Introduce a controlled Browsertrix execution boundary behind the merged v38.6 request and result-envelope contracts without permitting uncontrolled shell, container, browser, retry, storage, or network behavior.

## Delivered

- deterministic execution-plan identity and SHA-256;
- exact binding to a prepared v38.6 Browsertrix request;
- pinned Browsertrix image and fixed executable;
- explicit argument-array execution with shell disabled;
- non-privileged, non-host-network, read-only-root container policy;
- bounded CPU, memory, process, page, depth, duration, byte, timeout, screenshot, redirect, and concurrency controls;
- one approved capture-output mount only;
- telemetry disabled and no arbitrary environment variables;
- automatic retry disabled with exactly one attempt;
- cleanup required after success, failure, timeout, or cancellation;
- injected executor boundary for deterministic fictional CI execution;
- explicit stdout, stderr, exit code, timeout, cancellation, timing, version, URL, redirect, page, byte, and output records;
- exact execution-plan/result binding before v38.6 preservation-result validation.

## Safety boundary

This slice defines and validates a controlled execution plan. Public CI uses an injected fake executor and fictional output records. It does not install or launch Browsertrix, Docker, Podman, Chromium, or a network client in CI.

The adapter does not:

- accept shell fragments;
- use `shell=True`;
- use privileged or host-network mode;
- mount a user home directory, browser profile, credential store, or secret path;
- supply authentication, credentials, cookies, or saved profiles;
- enable form submission, uploads, CAPTCHA bypass, automatic retry, or off-domain scope growth;
- register evidence artifacts or sources;
- create v37 imports or observations;
- assign truth, merge entities, approve claims, mutate dossiers, export, or publish.

## Execution flow

`prepared v38.6 request → deterministic execution plan → injected executor → normalized execution result → exact plan/result binding → v38.6 result-envelope validation`

## Acceptance criteria

- only a valid `browsertrix_request_prepared` record can produce a plan;
- the image equals `webrecorder/browsertrix-crawler:1.5.0`;
- command execution is an argument array and shell execution is false;
- all process and browser resource limits are present and bounded;
- only the approved private capture-output target is mounted;
- execution is single-attempt and never silently retried;
- timeout, cancellation, executor exception, and non-zero exit become explicit failed records;
- successful validation occurs only after exact execution-plan and request bindings pass;
- public tests use a fake executor and perform no live browser or network operation.

## Validation

```bash
pytest -q tests/test_v38_6_1_browsertrix_execution.py
```

## Next authority

After this gate is merged and green, v38.6.2 may add a separately reviewed real container-runtime implementation of the `Executor` interface. The runtime must preserve every invariant in this gate and remain disabled by default until deployment-specific network egress and storage controls are proven.

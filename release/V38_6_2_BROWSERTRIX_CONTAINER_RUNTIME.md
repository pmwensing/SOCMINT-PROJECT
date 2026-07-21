# v38.6.2 — Browsertrix Container Runtime

## Objective

Add a real Docker/Podman subprocess implementation behind the merged v38.6.1 executor boundary while keeping execution disabled by default and fail-closed unless deployment-specific controls are proven.

## Delivered

- explicit runtime-enable and operator-confirmation gates;
- exact v38.6.1 execution-plan SHA-256 binding;
- Docker/Podman allowlist;
- immutable Browsertrix image reference using a deployment-approved SHA-256 digest;
- local image inspection with no implicit image pull;
- safe `private://` storage resolution beneath an approved root;
- traversal, symlink escape, sensitive-path, emptiness, ownership-mode, and restrictive-permission checks;
- required network, DNS, egress, and approved-target-binding attestations;
- fixed argument-array container command with `shell=False`;
- read-only root filesystem, no-new-privileges, all capabilities dropped, bounded PIDs, CPU, memory, timeout, and one output-only mount;
- telemetry disabled and arbitrary environment injection prohibited;
- exactly one execution attempt with no automatic retry;
- bounded stdout and stderr;
- explicit timeout, failure, cleanup, and quarantine outcomes;
- successful handoff into the existing v38.6.1 `ExecutionResult` contract;
- offline unit tests using fake storage, runtime inspection, subprocess, and result-loader adapters.

## Runtime safety boundary

The runtime remains blocked unless all required deployment policy fields are explicitly present and true. There are no permissive fallbacks.

The implementation does not:

- pull container images during an investigation run;
- accept mutable image tags as execution authority;
- use privileged or host-network mode;
- mount the Docker socket, home directory, browser profiles, credential stores, or secret paths;
- accept shell fragments or `shell=True`;
- inject arbitrary environment variables;
- retry failed, timed-out, or cancelled runs;
- treat a zero exit code as preservation acceptance;
- register artifacts or sources;
- create imports or observations;
- assign truth, merge entities, approve claims, mutate dossiers, export, or publish.

## Execution flow

`validated v38.6.1 execution plan → deployment runtime policy → safe storage resolution → local image/runtime inspection → hardened container command → single subprocess attempt → v38.6.1 ExecutionResult → existing result-envelope validation`

## Acceptance criteria

- runtime disabled unless explicitly enabled;
- exact execution-plan hash required;
- image must be referenced and locally present by matching SHA-256 digest;
- all four network containment controls must be verified;
- storage must resolve beneath an approved root into a new empty restrictive directory;
- command must use an argument array, no shell, no privilege, no host network, no implicit pull, and one output mount;
- failure and timeout produce cleanup and quarantine requirements;
- public CI performs no live Docker, Podman, Browsertrix, DNS, or HTTP operation.

## Validation

```bash
pytest -q tests/test_v38_6_2_browsertrix_container_runtime.py
```

## Next authority

After this runtime slice is green and separately reviewed, a deployment-only integration test may use a locally pinned image, isolated egress-controlled network, temporary approved storage, and a fictional local HTTP fixture. Standard CI must remain offline.

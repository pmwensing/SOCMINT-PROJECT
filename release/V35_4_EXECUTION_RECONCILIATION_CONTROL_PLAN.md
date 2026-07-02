# v35.4 Execution Reconciliation Control Plane

## Objective

Provide an administrator-only operator workflow for inspecting and reconciling uncertain governance executions without invoking the authoritative delegate again.

## Safety boundary

The control plane must never:

- retry or invoke a v32 delegate service;
- create a second governance execution for the same confirmation;
- replace or mutate an existing authoritative result envelope;
- transition an execution without expected-state and expected-version checks;
- expose submitted operator values in validation errors;
- offer an automatic retry control.

## Read model

The uncertain-execution queue returns only executions whose durable state is `uncertain` and includes:

- execution ID and execution record ID;
- case ID and governance action;
- delegate service;
- confirmation SHA-256;
- current state and state version;
- last actor, reason and update time;
- invocation ledger record and contract-validation SHA-256;
- confirmation-issuance audit reference;
- any recorded result reference and authoritative record IDs;
- whether an authoritative result envelope already exists;
- ledger-consistency status;
- `automatic_retry: false`.

## Reconciliation request contract

A reconciliation request requires:

- `execution_id`;
- `expected_state` equal to `uncertain`;
- `expected_version`;
- `authoritative_record_ids` as a non-empty mapping;
- `result_reference_sha256`;
- `workspace_sha256`;
- `reconciliation_reason`;
- one or more evidence references describing how the authoritative result was verified;
- the authenticated administrator actor supplied by the server.

The request must not accept delegate-service arguments, confirmation overrides, state overrides or retry flags.

## Durable operation

The service must use the v35.3 atomic result-envelope transition and bind reconciliation to:

- the original confirmation issuance;
- the contract-validation digest recorded in the durable `running` event;
- the execution identity and delegate service;
- expected `uncertain` state and version;
- the verified authoritative record IDs and result reference;
- the administrator, reason and evidence references.

The successful operation performs only:

`uncertain -> reconciled`

It does not call the delegate.

## API and operator workflow

Planned endpoints:

- `GET /api/v1/dissemination-governance/executions/uncertain`
- `GET /api/v1/dissemination-governance/executions/<execution_id>`
- `POST /api/v1/dissemination-governance/executions/<execution_id>/reconcile`

Planned operator page:

- `/dissemination-governance/execution-reconciliation`

The page must display durable history and binding evidence before enabling the reconciliation submission.

## Acceptance gates

- administrator authorization is enforced on every route;
- non-administrators receive no execution details;
- list and detail routes are read-only;
- reconciliation requires expected state/version and rejects stale submissions;
- delegate registry entries are never resolved or invoked by reconciliation code;
- identical submissions replay the existing result envelope;
- conflicting submissions are rejected without overwriting the first result;
- every successful reconciliation records actor, reason, evidence references and timestamp;
- browser tests prove no retry or delegate-invocation control is present;
- SQLite and PostgreSQL tests pass;
- full CI, migration, backup/restore, production boot and container verification pass.

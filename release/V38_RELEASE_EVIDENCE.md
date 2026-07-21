# v38 Release Evidence

## Program

**Lawful Public-Web Discovery and Capture**

Status: **closed**

## Merge ledger

| Slice | PR | Validated head | Merge SHA |
|---|---:|---|---|
| v38.0 | #317 | `71c03b9700eb30eafe2c156c1f559c37732b75fa` | `959afa3de67c881874d93ec96221268f6618e89d` |
| v38.1 | #318 | `f82a35318d14b6ba7afbfee020d8fe9611e50a49` | `53a56d3bd2afed719fc731611eb33f0e68571219` |
| v38.2 | #319 | `d72f25bf63f3a31fd7c35366cec1c328c3b675e3` | `843ca3d070f0e77cbf9513014e5ca631bd2f51ce` |
| v38.3 | #320 | `5a75fed4c88d87b2a664107145d00792b7560d53` | `f8534ed721e4b529715ba02a49024c2ab62ef5d5` |
| v38.4 | #321 | `0cdb87661f5963ef225385663c680539f7a547c0` | `e67a145454b80ad194e6a9a133d75ebc7b101529` |
| v38.5 | #322 | `72634e46386bb15bf9ca519b263597e3c941c79e` | `c94e1060538799f596048cbf02ffb28a88e2891f` |
| v38.6 | #323 | `93ac0ece408a20764854c7ee4d87437f4c3e8a48` | `a022236a3fd7da8d4c5b730506aa1e682246d70f` |
| v38.6.1 | #324 | `7824ea418ba42c22cc8616e3538e9b3eda3c1011` | `a129f7e9e1411584bf25b5d623a0546fd2a67138` |
| v38.6.2 | #325 | `efc26e26ea401bbdd71557ae583c04f5137e5b68` | `6e9ee7c2392ce0de1df702cb75895604d22e7de8` |
| v38.6.3 | #326 | `c72675f95e7642c59f5303d1ea5c23b80dc8ee5c` | `80c9871ab9c05f7e666b161c00e77ab4bb562865` |
| v38.6.4 | #328 | `668224ae72dd662412c3041c43c4a5230846da56` | `9a84eb269661a95fd041aabe0b411140a9b0a2aa` |
| v38.7 | #329 | `7bb167e81fda6f56a7f6d43a86038fa9d51f7ac2` | `3613c6d4d31ee1e76985240a423ad21d194f1555` |
| v38.8 | #330 | `66344973f22af9efa8aec70091c7b0e610a43710` | `d5c18c1784144ac9b0343185508fc3987ea85aa8` |

PR #327 was not used.

## Final runtime checkpoint

v38.8 head `66344973f22af9efa8aec70091c7b0e610a43710`:

- CI 4531 — success;
- Full Verification 1194 — success;
- legacy readiness 2491 — success;
- combined v32 through v38 browser E2E 184 — success.

The combined browser workflow passed:

- the complete focused v32 through v38 test set;
- v32 dissemination browser E2E;
- v33 case-governance browser E2E;
- v34 governance-execution browser E2E;
- v35 reconciliation and recovery browser E2E;
- v36 entity-accuracy browser E2E;
- v37 operational-case-intelligence browser E2E;
- v38 Public Discovery and Capture Workspace browser E2E.

## Controlled fictional pilot

Contract: `release/V38_9_CONTROLLED_FICTIONAL_PILOT.json`

Result: passed.

The proof matrix covers planning order, request registration, allow/block policy, passive archive candidates, synthetic provenance, public HTTP capture, Browsertrix preservation and controlled execution, deployment certification, production enablement, duplicate/change/relevance triage, v37 handoff, and read-only workspace/browser safety.

No real case evidence, real third-party crawl, production live collection, credential, cookie, private account, access-control bypass, Tor, or dark-web source was used.

## Closure package

- `release/V38_9_CONTROLLED_FICTIONAL_PILOT.json`
- `release/V38_9_PROGRAM_CLOSURE_CONTRACT.json`
- `release/V38_9_PROGRAM_CLOSURE.md`
- `release/V38_RELEASE_EVIDENCE.md`
- `tests/test_v38_9_program_closure.py`

The package introduces no runtime, route, migration, schema, network, or authority behavior.

## Closure-head validation

Pending the first exact-head v38.9 closure run. This section and the machine-readable closure contract are amended with the final head and workflow numbers before merge.

# v36 Release Evidence

## Program

**Entity Accuracy, Verification, and Dossier Synthesis**

## Closure date

2026-07-20

## Slice delivery ledger

| Slice | Pull request | Merge SHA | Delivered capability |
|---|---:|---|---|
| v36.0 | #294 | `dfbaee61f65832f9475cd386dc74389f865e5248` | planning, compatibility, ownership, and non-duplication gate |
| v36.1 | #295 | `80f395a93287dd19efade49e19b819675e5eb95d` | source registry and capture integrity |
| v36.2 | #296 | `3a9417ee804acbdefee507d630196d2cc58c3fb3` | canonical observation envelopes and quarantine review |
| v36.3 | #297 | `160c02e8a0b827dac20e212bed70bf1ee08f392a` | explainable entity candidate resolution |
| v36.4 | #298 | `a84c2bdd7a57af242203ab1eb9ca74ff1e3be7d5` | source independence and dependency graph |
| v36.5 | #299 | `5449c3e29ea5e4bba097dc2fb3f2055c48078dd8` | dimensional claim verification and alternative ranking |
| v36.6 | #300 | `47c1ad43079f59a2fc863aa190717cfdd2a599d4` | relationship and timeline verification |
| v36.7 | #303 | `8d4d5a301247ad45a0d6257acc92ef161100afdd` | versioned dossier synthesis |
| v36.8 | #304 | `94bb889e3cda2e378a57190eac0d1a50714eb800` | integrated workspace and browser E2E |

Superseded stacked PRs #301 and #302 were closed without merge and replaced by clean branches based on the authoritative merged baseline. Pre-closure PR #292 was likewise replaced by clean v36.0 PR #294 after v35 formally closed.

## Validation ledger

| Slice | CI | Full Verification | Legacy readiness | Browser E2E |
|---|---:|---:|---:|---:|
| v36.0 | 4210 | 1070 | 2403 | planning-only |
| v36.1 | 4226 | 1072 | 2405 | not applicable |
| v36.2 | 4235 | 1074 | 2407 | not applicable |
| v36.3 | 4247 | 1076 | 2409 | not applicable |
| v36.4 | 4256 | 1078 | 2411 | not applicable |
| v36.5 | 4293 | 1082 | 2414 | not applicable |
| v36.6 | 4297 | 1085 | 2416 | not applicable |
| v36.7 | 4302 | 1087 | 2418 | not applicable |
| v36.8 | 4310 | 1091 | 2421 | 172 |

## Final validated runtime head

- Pull request: **#304**
- Head: `6aa600ea0623a1af52faad3955a521c22bdf9a09`
- Merge: `94bb889e3cda2e378a57190eac0d1a50714eb800`
- CI: **4310**, success
- Full Verification: **1091**, success
- legacy v12.10.19 readiness: **2421**, success
- combined v32.7 through v36.8 Browser E2E: **172**, success

The browser workflow ran the focused v32 through v36 suite, then all browser checkpoints through v36.8. The final v36.8 checkpoint verified the required read-only markers and absence of forms or merge, approval, export, publication, collection, and dossier-mutation controls.

## Corrective validation record

Two issues were corrected before final validation:

1. v36.5 tests were aligned with the defined bounded scoring formula: a 95 weighted score minus 15 conflict and 5 limitation penalties equals 75, and alternative-ranking test inputs were changed so the lower alternative did not also hit the hard pre-review cap of 79.
2. v36.8 isolated route tests were given explicit `dashboard.login`, `dashboard.index`, and `dashboard.logout` endpoint stubs required by the production redirect and base template.

Neither correction weakened a production safety control. The final heads passed their complete required gates.

## Preserved evidentiary model

The delivered program continues to distinguish:

- raw artifacts from normalized observations;
- observations from claims;
- identity confidence from factual support;
- source reliability from source independence;
- support ranking from truth;
- human analytic review from dossier contribution;
- dossier synthesis snapshots from export or publication;
- correlation and co-occurrence from causation.

## Release decision

The evidence supports formal closure of v36. No runtime or schema work remains inside this program. Any later extension must begin with a new planning and compatibility gate and must continue to preserve the existing case, privacy, evidence, audit, human-review, dossier, export, and manifest authorities.

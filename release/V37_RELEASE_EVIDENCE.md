# v37 Release Evidence

## Program

**Operational Case Intelligence Pipeline**

## Closure date

2026-07-20

## Foundation and slice delivery ledger

| Delivery | Pull request | Merge SHA | Capability |
|---|---:|---|---|
| 46 Montreal foundation | #306 | `1448fc27e05eb144bf4bdebb83a7aaee6e824d8b` | current-baseline case configuration, scope, evidence-vault helpers, and tests |
| v37.0 | #307 | `f8723b2c00feca2b3732f2d2c5f02f06fb3e3a4e` | planning and compatibility gate |
| v37.1 | #308 | `8f68cf779acef6a52da7272e4b4ad330759c72f0` | case-scoped universal import envelopes |
| v37.2 | #309 | `c942d7b67376867acd64beb6e940ba6bc864ed09` | offline adapters, staged records, duplicate detection, and quarantine |
| v37.3 | #310 | `30c320577ca90e0f7751e1b978890fb9839ce141` | controlled fictional 46 Montreal pilot |
| v37.4 | #311 | `37bac6f3e4b21d5c506a676f73dcdd3af0b95e27` | explicit single-record observation promotion |
| v37.5 | #312 | `a2abfd8407acbe64fcad19f5c7832be47ee5eea9` | guided read-only analyst workflow |
| v37.6 | #313 | `875a7c2456be8119bc4edef5e50e43a6fec58e25` | relationship and chronology workflow |
| v37.7 | #314 | `b14d570675fa8adbd15252f5af80e877ce378189` | controlled dossier export-readiness projection |
| v37.8 | #315 | `a9e53695a2db374791904aa56f6264770058d387` | integrated read-only workspace and browser E2E |

## Slice validation ledger

| Slice | CI | Full Verification | Legacy readiness | Browser E2E |
|---|---:|---:|---:|---:|
| v37.0 | 4375 | 1118 | 2430 | planning-only |
| v37.1 | 4387 | 1124 | 2432 | not applicable |
| v37.2 | 4404 | 1133 | 2435 | not applicable |
| v37.3 | 4417 | 1140 | 2437 | not applicable |
| v37.4 | 4420 | 1142 | 2439 | not applicable |
| v37.5 | 4423 | 1144 | 2441 | not applicable |
| v37.6 | 4426 | 1146 | 2443 | not applicable |
| v37.7 | 4429 | 1148 | 2445 | not applicable |
| v37.8 | 4432 | 1150 | 2447 | 180 |

## Final validated runtime head

- Pull request: **#315**
- Head: `7bb00b7516c87af7d85128402d634609c5226efd`
- Merge: `a9e53695a2db374791904aa56f6264770058d387`
- CI: **4432**, success
- Full Verification: **1150**, success
- legacy v12.10.19 readiness: **2447**, success
- combined v32.7 through v37.8 Browser E2E: **180**, success

The browser workflow ran the focused v32 through v37 test suite and every browser checkpoint through v37.8. The final checkpoint verified the Operational Case Intelligence Workspace's read-only markers and the absence of forms or named collection, automatic promotion, merge, claim-approval, dossier-mutation, export, and publication controls.

## Corrective validation record

Before final release validation, the following test-harness and integration issues were corrected:

1. the v37.0 planning test was reduced to stable machine-readable contract and baseline assertions rather than brittle prose coupling;
2. the v37.2 empty-CSV test was aligned with the adapter's required-input contract;
3. the v37.2 duplicate-history helper was changed so submitted records and existing history can be supplied independently;
4. staged-record projections were given their exact parent operational-import ID;
5. the fictional pilot fixture check covers Windows drive-path forms without embedding real private paths;
6. isolated Flask route tests were given the dashboard endpoints required by the production base template.

None of these corrections weakened a production safety boundary. Each final master-target head passed its required release gates.

## Pilot evidence

The public pilot evidence is fictional and exercises:

- direct 46 Montreal scope;
- 559 Macdonnel relocation/mitigation context;
- Cowdy-only exclusion;
- unanchored candidate-entity review;
- evidence-location projection without original-file upload.

No real case evidence, credentials, private URLs, personal cloud links, or original evidence files are included in public fixtures.

## Preserved evidentiary model

v37 continues to distinguish:

- operator-provided exports from collection actions;
- raw artifacts from import envelopes and staged records;
- staged records from accepted observations;
- observations from claims;
- identity assessment from factual support;
- duplicates and dependent sources from independent corroboration;
- direct evidence, supported inference, and co-occurrence;
- dossier synthesis from export readiness;
- export readiness from export or publication.

## Release decision

The evidence supports formal closure of v37. No runtime or schema work remains inside this program. Any later extension must begin with a new planning and compatibility gate and preserve the existing case, privacy, evidence, audit, human-review, dossier, redaction, export, and publication authorities.

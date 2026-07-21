# v37.0 — Operational Case Intelligence Pipeline Roadmap

## Objective

Turn the closed v36 analytical foundation into one defensible operator workflow:

`tool export → preserved artifact → case-scoped import → staged records → reviewed observations → entity/claim/relationship review → approved dossier snapshot → export-readiness package`

v37 does not create a new truth engine, evidence vault, identity graph, dossier backend, or export authority. It orchestrates existing services and records new import/review events through append-only audit history.

## Entry conditions

- v36 is formally closed.
- The 46 Montreal case configuration, scope filter, hash-manifest helper, and evidence-location helper are present on the current baseline.
- Runtime work begins only after this planning gate is merged.
- Public CI fixtures are fictional and contain no real case evidence, credentials, cloud links, or personal records.

## Delivery slices

### v37.0 — Planning and compatibility gate

- define authority ownership and non-duplication boundaries;
- define privacy and synthetic-fixture requirements;
- define the v37.1–v37.9 delivery sequence;
- add focused planning tests;
- no runtime or migration.

### v37.1 — Case-scoped universal import envelopes

- JSON, JSONL/NDJSON, CSV, and HTML-report adapter contracts;
- required case, purpose, operator, tool, adapter, filename, SHA-256, artifact, collection/export time, and import time;
- deterministic import IDs and rerun keys;
- append-only import inventory and detail APIs;
- no connector execution or hidden collection.

### v37.2 — Immutable manifests and staged records

- deterministic record hashes;
- accepted, quarantined, duplicate, and rejected counts;
- duplicate detection within and across imports;
- normalization warnings and adapter diagnostics;
- staged records remain observations-to-review, not truth or claims.

### v37.3 — Controlled 46 Montreal pilot

- apply the case scope filter to fictional pilot records;
- classify direct 46 Montreal records as in scope;
- preserve 559 Macdonnel as relocation/mitigation context;
- block Cowdy-only issue expansion;
- require review for unanchored candidate entities;
- prove evidence-location registration without uploading originals.

### v37.4 — Analyst import review and observation promotion

- administrator review queue;
- explicit accepted/quarantined/rejected decisions;
- explicit promotion into the existing v29 observation service;
- promotion requires accepted artifact, in-scope/reviewed record, reason, and confirmation;
- no bulk automatic promotion.

### v37.5 — Guided entity and claim review

- compose v36.3 candidate resolution, v30.1 claims, v30.3 conflicts, v36.5 verification, and v30.5 review status;
- surface missing sources, ties, contradictions, and unresolved candidate identities;
- no automatic merge, claim approval, or review completion.

### v37.6 — Relationship and chronology assembly

- compose accepted observations, verified claims, and v36.6 relationship/timeline assessments;
- keep event, report, capture, and validity times separate;
- distinguish direct evidence, supported inference, and co-occurrence;
- no causation assignment.

### v37.7 — Dossier and export readiness

- select an approved v36.7 dossier snapshot;
- verify current v30.6 contribution decisions;
- record redaction, scope, disclosure, quality, approval, audit, and manifest readiness;
- produce a readiness package only;
- existing export/publication services remain authoritative.

### v37.8 — Integrated workspace and browser E2E

- one administrator workspace for imports, quarantine, candidate review, claim review, chronology, snapshots, and export readiness;
- explicit read/write boundaries;
- browser proof that no collection, merge, claim-approval, export, or publication bypass exists.

### v37.9 — Pilot evidence and closure

- exact merge and validation ledger;
- fictional 46 Montreal-shaped pilot evidence;
- CI, Full Verification, legacy readiness, and browser E2E;
- closure only after all planned slices are merged.

## Acceptance criteria

- every imported record resolves to an import manifest and accepted artifact hash;
- repeated imports are idempotent;
- duplicate and mirrored records do not inflate support;
- quarantined records cannot support claims;
- entity merges require a recorded human decision;
- unresolved conflicts and ranking ties remain visible;
- relationship timelines preserve inference warnings;
- original sensitive evidence and credentials never enter the public repository;
- export-readiness preparation cannot export or publish;
- all consequential actions remain append-only and hash-bound.

## Next action

`implement_v37_1_case_scoped_import_envelopes`

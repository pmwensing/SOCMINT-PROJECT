# v36.7 — Versioned Dossier Synthesis

## Objective

Create reproducible, versioned dossier synthesis snapshots from currently approved v30.6 contribution decisions and exact v36 assessment hashes without automatically exporting, publishing, or mutating the existing dossier backend.

## Delivered

- append-only dossier synthesis snapshots by case and entity;
- approved-current-contribution filtering;
- required current v36.5 verification for every included claim;
- section-level assembly using the approved target dossier section;
- substantially supported, moderately supported, limited, disputed, and insufficient categories;
- relationship-assessment bindings from v36.6;
- claim, verification, contribution, conflict, and relationship integrity hashes;
- deterministic integrity manifest and snapshot hash;
- monotonically increasing snapshot versions;
- previous-snapshot ID and hash chaining;
- coverage counts by section and support category;
- administrator-only inventory, creation, detail, and latest-snapshot APIs;
- analytic-review route integration.

## Routes

- `GET /api/v1/entity-accuracy/dossier-snapshots`
- `POST /api/v1/entity-accuracy/dossier-snapshots`
- `GET /api/v1/entity-accuracy/dossier-snapshots/latest`
- `GET /api/v1/entity-accuracy/dossier-snapshots/<snapshot_id>`

## Safety boundary

- only currently approved v30.6 contributions are eligible;
- every included claim must have a current v36.5 verification;
- disputed claims remain visibly disputed;
- snapshot creation does not export or publish;
- no existing dossier, claim, review, source, graph, or contribution record is mutated;
- the existing export, quality, readiness, approval, audit, and manifest services remain authoritative for later output.

## Verification

Focused coverage includes approved-only filtering, verification requirements, support-category partitioning, disputed-claim preservation, relationship bindings, manifest integrity, version sequencing, previous-snapshot chaining, administrator routes, latest-snapshot lookup, analytic-review registration, and static absence of export or publication calls.

## Next action

Implement v36.8 Entity Accuracy Workspace and browser E2E checkpoint, then close the v36 program only after all exact-head release gates pass.

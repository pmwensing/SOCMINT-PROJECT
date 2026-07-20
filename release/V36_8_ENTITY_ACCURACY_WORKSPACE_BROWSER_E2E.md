# v36.8 — Entity Accuracy Workspace and Browser E2E

## Objective

Provide one administrator-only, read-only workspace that exposes source integrity, canonical observations, entity candidates, source independence, claim verification, relationship timelines, dossier snapshots, and unresolved integrity findings without introducing a second review, approval, export, publication, collection, or mutation surface.

## Delivered

- integrated `Entity Accuracy Workspace` at `GET /entity-accuracy`;
- read-only workspace API at `GET /api/v1/entity-accuracy/workspace`;
- source, canonical-observation, entity-candidate, source-independence, claim-verification, relationship-timeline, and dossier-snapshot inventories;
- current integrity and review findings with next safe actions;
- explicit administrator authorization;
- explicit no-truth, no-automatic-merge, no-automatic-publication, and no-write markers;
- analytic-review route-chain registration;
- Selenium browser checkpoint;
- combined v32 through v36 focused and browser workflow.

## Browser contract

The browser checkpoint requires the rendered workspace to expose:

- `data-entity-accuracy-workspace="v36.8"`;
- `data-read-only="true"`;
- `data-automatic-truth-assignment="false"`;
- `data-automatic-entity-merge="false"`;
- `data-automatic-dossier-publication="false"`;
- `data-write-actions="none"`;
- all seven inventory and integrity sections.

It also proves the absence of forms and merge, approval, export, publication, collection, or dossier-mutation controls.

## Safety boundary

- no truth assignment;
- no automatic entity merge;
- no claim approval or review completion;
- no source, artifact, observation, graph, claim, contribution, snapshot, dossier, export, or publication mutation;
- no connector execution or hidden collection;
- no bypass of case, privacy, authorization, or human-review controls.

## Verification

The combined browser workflow runs all focused v32 through v36 tests and all browser checkpoints through v36.8. Exact-head CI, Full Verification, legacy verification, and browser E2E are required before merge.

## Next action

After all v36 slices are merged and exact-head validation is green, add the formal v36 program closure contract and release evidence package.

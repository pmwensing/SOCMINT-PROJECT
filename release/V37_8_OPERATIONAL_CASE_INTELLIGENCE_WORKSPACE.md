# v37.8 — Operational Case Intelligence Workspace and Browser E2E

## Objective

Provide one administrator-only, read-only workspace that integrates import review, entity/claim analysis, chronology, dossier snapshots, and export-readiness status without exposing collection, promotion, merge, approval, export, publication, or dossier-mutation controls.

## Delivered

- integrated workspace at `GET /operational-case-intelligence`;
- read-only API at `GET /api/v1/operational-case-intelligence/workspace`;
- workflow findings and counts from v37.5;
- chronology from v37.6;
- export-readiness inventory from v37.7;
- explicit no-collection, no-automatic-promotion, no-merge, no-claim-approval, no-export, and no-publication markers;
- Selenium browser checkpoint;
- combined v32 through v37 focused and browser workflow;
- analytic-review route integration.

## Browser contract

The browser checkpoint proves the presence of all read-only safety markers and the absence of forms and named collect, promote, merge, approve, export, publish, or dossier-mutation controls.

## Safety boundary

- no collection or private-source access;
- no automatic observation promotion;
- no entity merge or claim approval;
- no dossier or snapshot mutation;
- no export or publication;
- all write services remain separate explicit administrator actions with their existing confirmation and authority gates.

## Authoritative baseline

Final release validation is performed with this slice targeting `master` after the v37.7 merge through PR #314 at `b14d570675fa8adbd15252f5af80e877ce378189`.

## Next action

After all v37 slices are merged and final exact-head validation is green, add v37.9 program closure and release evidence.

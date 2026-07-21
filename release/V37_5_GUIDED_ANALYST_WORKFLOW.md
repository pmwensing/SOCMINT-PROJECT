# v37.5 — Guided Analyst Workflow

## Objective

Provide one read-only analyst composition over operational imports, scope review, observation promotion, entity candidates, claims, conflicts, verification, relationships, and dossier snapshots.

## Delivered

- integrated import, staged-record, scope-assessment, review-decision, and promotion inventories;
- embedded v36.8 Entity Accuracy Workspace;
- findings for unassessed records, pending human review, quarantine, duplicates, candidate identity review, accepted records awaiting promotion, and separated relocation context;
- inherited visibility into unresolved conflicts, tied alternatives, relationship assessments, and dossier snapshot gaps;
- administrator-only read-only workflow API;
- analytic-review route integration.

## Safety boundary

- no write actions are exposed by this workflow;
- no automatic collection, promotion, entity merge, claim approval, dossier mutation, export, or publication;
- v30.5 remains the consequential analytic-review gate;
- v30.6 remains the dossier-contribution gate;
- all specialized write actions remain separate explicit services.

## Authoritative baseline

Final release validation is performed with this slice targeting `master` after the v37.4 merge through PR #311 at `37bac6f3e4b21d5c506a676f73dcdd3af0b95e27`.

## Next action

Implement relationship/chronology review and controlled dossier export-readiness preparation.

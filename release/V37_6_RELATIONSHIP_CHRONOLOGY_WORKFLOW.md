# v37.6 — Relationship and Chronology Workflow

## Objective

Assemble reviewed import observations and v36.6 relationship assessments into one read-only chronology while preserving distinct event, report, capture, validity-start, and validity-end times.

## Delivered

- promoted import-observation chronology entries;
- v36.6 relationship-assessment entries;
- chronological case filtering and relationship entity filtering;
- direct-import-observation, supported-inference, and co-occurrence-only classifications;
- explicit inference warnings and limitations;
- relocation-context entries retained but barred from issue-claim support;
- counts for promoted observations, relationship assessments, supported inference, co-occurrence, and relocation context;
- administrator-only read-only chronology API;
- analytic-review route integration.

## Safety boundary

- co-occurrence is never promoted into a relationship;
- causation and truth are not assigned;
- no graph, claim, dossier, export, or publication mutation;
- the chronology exposes no write actions;
- v36.6 remains the relationship-assessment authority.

## Authoritative baseline

Final release validation is performed with this slice targeting `master` after the v37.5 merge through PR #312 at `a2abfd8407acbe64fcad19f5c7832be47ee5eea9`.

## Next action

Implement controlled dossier snapshot review, redaction declarations, and export-readiness preparation without invoking export or publication services.

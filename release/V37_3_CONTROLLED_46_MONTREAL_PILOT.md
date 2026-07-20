# v37.3 — Controlled 46 Montreal Pilot

## Objective

Apply the rebuilt 46 Montreal case scope to fictional staged records and record explicit human review decisions without exposing real case evidence or automatically creating observations, claims, dossiers, exports, or publications.

## Delivered

- deterministic scope assessments for staged import records;
- direct `46 Montreal` references classified in scope;
- `559 Macdonnel` preserved as relocation/mitigation context only;
- Cowdy-only issue records classified out of scope;
- unanchored entities classified as candidate-review-required;
- duplicate records must be rejected;
- candidate acceptance requires a reviewed candidate-resolution reference;
- quarantined acceptance requires an explicit quarantine resolution;
- relocation records may be retained as observations but cannot support issue claims;
- evidence-location manifest projections using existing helpers without uploading originals;
- administrator-only assessment, decision, inventory, detail, and location-projection APIs;
- a fictional four-record pilot fixture and scope-boundary tests;
- analytic-review route integration.

## Safety boundary

- no real case evidence or personal records are included in public fixtures;
- no original evidence is uploaded to GitHub;
- no automatic observation promotion;
- no truth assignment, entity merge, claim approval, dossier mutation, export, or publication;
- out-of-scope records cannot be accepted;
- relocation context cannot be used as issue-claim support.

## Next action

Implement v37.4 explicit one-record-at-a-time promotion into the existing v29 observation authority after a current accepted pilot review decision.

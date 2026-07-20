# v36.6 — Relationship and Timeline Verification

## Objective

Create source-grounded, time-bounded relationship and event assessments with explicit inference warnings, while preventing co-occurrence from becoming an inferred relationship or causation claim.

## Delivered

- person, organization, domain, account, communication, event-association, and co-occurrence assessment types;
- required proposed v30 claim and current v36.5 verification binding;
- required accepted v36.2 observations and same-case v36.1 sources;
- separate event, report, capture, validity-start, and validity-end times;
- direct-evidence, supported-inference, and co-occurrence-only classes;
- mandatory inference warning and limitations;
- deterministic append-only assessment hashes;
- entity-filtered chronological inventory;
- administrator-only inventory, detail, and assessment APIs;
- analytic-review route integration.

## Controls

- report and capture times cannot precede the event;
- validity end cannot precede validity start;
- co-occurrence must remain `co_occurrence_only`;
- `co_occurrence_only` cannot be used for another relationship type;
- sources and observations must match the claim case;
- observations must be accepted;
- the claim must already have a v36.5 verification assessment.

## Routes

- `GET /api/v1/entity-accuracy/relationship-timeline`
- `POST /api/v1/entity-accuracy/relationship-timeline`
- `GET /api/v1/entity-accuracy/relationship-timeline/<assessment_id>`

## Safety boundary

- no relationship is asserted as truth;
- no causation is assigned;
- no identity graph edge is created or updated;
- no source, observation, claim, review, or dossier mutation;
- no automatic promotion from co-occurrence to association.

## Verification

Focused coverage includes time ordering, validity intervals, co-occurrence restrictions, verified-claim requirements, accepted-observation requirements, duplicate blocking, chronological entity filtering, administrator routes, analytic-review registration, and absence of graph or causation write routes.

## Next action

Implement v36.7 Versioned Dossier Synthesis over currently approved v30.6 contribution decisions and exact v36 assessment hashes without automatically exporting or publishing the dossier.

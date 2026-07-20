# v36.3 — Entity Candidate Resolution

## Objective

Assess whether two candidate entity identifiers may refer to the same entity using explainable, source-bound signals and a separate human decision record without automatically merging identities or mutating the identity graph.

## Delivered

- deterministic candidate identities bound to case, entity pair, accepted observations, signals, and limitations;
- strong, supporting, weak, and negative signal classes;
- visible score components, caps, counts, and recommendation;
- weak-only cap of 20;
- no-strong-signal cap of 49;
- negative-signal cap of 69;
- `likely_same_entity`, `possible_same_entity`, `keep_separate`, and `insufficient_evidence` recommendations;
- append-only human decisions: recommend merge, keep separate, insufficient evidence, or needs revision;
- merge recommendations restricted to candidates assessed as likely the same entity;
- administrator-only inventory, detail, assessment, and decision APIs;
- analytic-review route integration.

## Signal classes

### Strong

Exact unique identifiers, reciprocal verified links, cryptographic control, exact registry identifiers, and verified domain control.

### Supporting

Stable username reuse, consistent biography, location or employment history, linked accounts, recurring contacts, archive continuity, and relationship clusters.

### Weak

Common names, avatar similarity, geographic proximity, shared interests, shared following, and tool probability.

### Negative

Conflicting unique identifiers, incompatible timelines, conflicting locations, distinct verified control, and explicit denials.

## Routes

- `GET /api/v1/entity-accuracy/entity-candidates`
- `POST /api/v1/entity-accuracy/entity-candidates`
- `GET /api/v1/entity-accuracy/entity-candidates/<candidate_id>`
- `POST /api/v1/entity-accuracy/entity-candidates/<candidate_id>/decision`

## Safety boundary

- no automatic merge;
- no identity graph mutation;
- no identity or truth assignment;
- no claim creation or dossier mutation;
- every signal must bind one or more accepted canonical observations from the same case;
- weak signals cannot independently produce a likely-same recommendation;
- negative signals prevent a merge recommendation;
- a human decision remains a review record, not a merge operation.

## Verification

Focused coverage includes strong/supporting/weak/negative scoring, score caps, same-case accepted-observation requirements, merge-decision restrictions, append-only decision history, administrator routes, analytic-review registration, and static proof that graph merge functions are not imported or exposed.

## Next action

Implement v36.4 Source Independence Graph so mirrored, syndicated, derivative, and common-origin source records do not inflate corroboration.

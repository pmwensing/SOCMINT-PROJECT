# v36.4 — Source Independence Graph

## Objective

Group source records by independently assessed origin so mirrored, syndicated, derivative, and common-origin records cannot inflate corroboration merely because they appear at multiple URLs or in multiple captures.

## Delivered

- deterministic same-case source groups;
- independent, mirror, syndication, derivative, common-origin, and unknown relationships;
- source bindings to event, capture, content hash, and canonical URL;
- explicit dependency and independent-origin signals;
- automatic exact-content-hash detection;
- independence scores of 100, 20, 10, 5, or 0 according to the assessed relationship;
- append-only reassessment history with one current projection per source set;
- administrator-only inventory, detail, and assessment APIs;
- analytic-review route integration.

## Controls

- exact matching content hashes cannot be assessed as independent;
- independent status requires an `independent_primary_capture` signal;
- dependency signals conflict with an independent assessment;
- mirror status requires an exact-content or canonical-URL matching signal;
- all sources must belong to the same case;
- source records remain unmodified;
- no claim support or truth is assigned by this slice.

## Routes

- `GET /api/v1/entity-accuracy/source-independence`
- `POST /api/v1/entity-accuracy/source-independence`
- `GET /api/v1/entity-accuracy/source-independence/<independence_group_id>`

## Safety boundary

- no source mutation;
- no automatic claim corroboration;
- no truth assignment or claim approval;
- no deletion of dependency history;
- no domain allowlist or URL-count independence assumption;
- no dossier mutation or export.

## Verification

Focused coverage includes independent-primary evidence, exact-hash dependency, mirror constraints, conflicting dependency signals, same-case enforcement, duplicate blocking, administrator routes, analytic-review registration, and absence of source update routes.

## Next action

Implement v36.5 Claim Verification and Alternative Ranking using source reliability, capture integrity, source independence, entity-resolution context, temporal relevance, limitations, and preserved conflicts.

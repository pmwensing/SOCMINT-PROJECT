# v36.9 — Entity Accuracy Program Closure

## Closure decision

The **v36 — Entity Accuracy, Verification, and Dossier Synthesis** program is closed.

All planned slices from v36.0 through v36.8 have been implemented, validated, and merged. v36.9 adds only the closure contract, release evidence, and focused closure tests. No runtime service, route, migration, collection action, scoring behavior, review behavior, dossier mutation, export, or publication capability is introduced by this closure slice.

## Production outcome

v36 composes the existing SOCMINT evidence, analytic-review, identity, dossier, audit, governance, privacy, and export layers into an evidence-not-truth entity accuracy workflow.

The delivered lifecycle is:

1. register a captured source against an accepted artifact, case, and content hash;
2. assess source reliability for the intended claim type;
3. wrap accepted source observations in deterministic canonical envelopes;
4. preserve low-confidence or problematic observations in quarantine pending review;
5. assess possible entity matches using visible positive, negative, strong, supporting, and weak signals;
6. require a separate human entity-candidate decision without mutating the identity graph;
7. group mirrored, syndicated, derivative, common-origin, and independently captured sources;
8. assess claim support through separate identity, source, directness, capture, temporal, independence, linkage, conflict, and limitation dimensions;
9. rank alternatives without assigning truth and preserve top ties;
10. represent relationships and events with separate event, report, capture, and validity times plus mandatory inference warnings;
11. synthesize versioned snapshots only from currently approved v30.6 dossier contributions;
12. expose all layers in one administrator-only, read-only workspace with browser proof that no write controls are present.

## Delivered slices

- **v36.0** — Planning and Compatibility Gate
- **v36.1** — Source Registry and Capture Integrity
- **v36.2** — Canonical Observation Contract
- **v36.3** — Entity Candidate Resolution
- **v36.4** — Source Independence Graph
- **v36.5** — Claim Verification and Alternative Ranking
- **v36.6** — Relationship and Timeline Verification
- **v36.7** — Versioned Dossier Synthesis
- **v36.8** — Entity Accuracy Workspace and Browser E2E
- **v36.9** — Program Closure and Release Evidence

## Preserved authority boundaries

The following layers remain authoritative and were not replaced:

- existing case, role, purpose, authorization, minimization, sensitive-context, retention, and privacy controls;
- accepted evidence artifacts and append-only AuditLog history;
- v30 claims, evidence/observation linkages, conflicts, confidence records, human reviews, and dossier-contribution decisions;
- the existing identity graph and its reviewed merge process;
- existing dossier quality, readiness, supervisor approval, export, audit, bundle, and manifest services.

## Safety invariants

v36 does not provide:

- connector, parser, adapter, scoring-model, or AI truth assignment;
- automatic entity merging;
- automatic claim approval or human-review completion;
- source-count corroboration without dependency assessment;
- destructive conflict resolution;
- automatic dossier mutation, export, or publication;
- a second evidence vault, observation authority, identity authority, truth table, or dossier product pipeline;
- hidden collection, credential abuse, private-source authentication bypass, or access expansion.

The entity accuracy workspace is read-only. The browser checkpoint proves the absence of forms and merge, approval, export, publication, collection, or dossier-mutation controls.

## Final runtime validation

The final v36.8 head `6aa600ea0623a1af52faad3955a521c22bdf9a09` passed:

- CI **4310**;
- Full Verification **1091**;
- legacy runtime readiness **2421**;
- combined v32 through v36 browser E2E **172**.

It was merged through PR **#304** as `94bb889e3cda2e378a57190eac0d1a50714eb800`.

## Closure scope

v36.9 is documentation-and-test-only. It records the final decision that:

- v36 is closed;
- no v36 runtime or schema work remains;
- all future runtime work requires a new planning and compatibility gate;
- the exact v36 historical contracts, hashes, conflicts, reviews, snapshots, and release evidence remain preserved.

## Next action

`define_the_next_program_planning_and_compatibility_gate_before_runtime_work`

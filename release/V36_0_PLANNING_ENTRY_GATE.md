# v36.0 Entity Accuracy Planning Entry Gate

## Program

**Entity Accuracy, Verification, and Dossier Synthesis**

## Entry-gate result

The production objective, primary workspace, nine-slice roadmap, existing capability inventory, schema ownership map, non-duplication requirements, analytical dimensions, privacy boundaries, validation expectations, and closure contract are defined.

This slice is planning-only. It adds no runtime service, route, migration, source score, observation adapter, entity-resolution action, claim-ranking action, relationship inference, dossier synthesis, or workspace behavior.

## Required lifecycle

1. validate case purpose, authority, scope, minimization, sensitivity, and retention requirements
2. preserve each collected tool output as an immutable hash-addressed artifact
3. normalize the output into a versioned observation envelope without assigning identity or truth
4. propose narrow identifier, entity, relationship, event, or attribute claims
5. bind each claim to exact sources, observations, artifacts, adapters, and derivation hashes
6. identify source origin, mirrors, syndication, dependency, and independent corroboration groups
7. preserve conflicts and compare mutually exclusive alternatives
8. assess identity, support, source, integrity, time, independence, conflict, and limitations separately
9. require explicit human analytic review before consequential use
10. require a separate dossier-contribution decision
11. synthesize a reproducible versioned dossier through the existing dossier and export pipeline
12. retain every prior assessment, rejected hypothesis, conflict, review, withdrawal, and export manifest

## Preserved controls

- connectors produce evidence and observations, never truth
- evidence and observation storage remain authoritative
- v30 claims, linkages, conflicts, confidence, human reviews, and dossier contributions remain authoritative
- identity candidates remain unmerged until explicit review
- confidence remains bounded, explainable, and distinct from truth
- dependent sources cannot inflate corroboration
- rejected and contradictory hypotheses remain visible
- dossier contribution remains separate from analytic approval
- AuditLog history remains append-only
- dossier exports continue through existing quality, readiness, approval, audit, and manifest gates
- privacy purpose, scope, minimization, sensitive-context, and retention requirements remain enforceable controls
- no private-source authentication bypass, credential abuse, or collection without authority

## Compatibility prerequisite

v36.0 planning may be reviewed while v35 remains active, but no v36.1 runtime or schema implementation may begin until v35 is formally closed and the exact v36.0 planning head passes focused, full-suite, lint, and CI validation.

## Next action

`implement_v36_1_source_registry_and_capture_integrity_after_v35_closure`

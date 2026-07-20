# v36 — Entity Accuracy, Verification, and Dossier Synthesis

## Production objective

Convert accepted SOCMINT and OSINT collection outputs into source-grounded, explainable, conflict-preserving, human-reviewed entity claims and versioned dossier contributions.

v36 must not allow connectors, parsers, scoring code, or AI models to assign truth, merge identities, approve claims, or write directly into a dossier. It composes the existing spine, evidence, v30 analytic-review, identity-graph, dossier-export, AuditLog, and closed v35 governance controls rather than replacing them.

## Closed baseline

v35 is formally closed through `release/V35_6_PROGRAM_CLOSURE_CONTRACT.json`. The closure merge is `f9a2af381f98e9919bc0913c7e67f3cc0b8deb22`; the final runtime merge is `f1b750241d03217aed0cb2a2fa255c7c9e5f37ee`. Automatic retry remains disabled.

## Primary workspace

**Entity Accuracy and Dossier Synthesis Workspace**

The workspace will show source origin and capture integrity, canonical observations, candidate entity matches, identifier claims, source-dependency groups, competing claims, dimensional confidence components, relationship and timeline evidence, human decisions, and dossier eligibility.

## Canonical lifecycle

1. accept an authorized case and scoped seed;
2. execute an approved collection tool or ingest an approved result;
3. preserve the raw artifact and capture hash;
4. normalize tool output into canonical observations;
5. generate reviewable entity candidates and narrow claims;
6. bind claims to exact observations, artifacts, sources, and derivation hashes;
7. group dependent or mirrored sources before corroboration scoring;
8. preserve contradictions and rank competing supported alternatives;
9. require explicit human analytic review before consequential use;
10. require a separate dossier-contribution decision;
11. synthesize a versioned dossier whose statements trace to source evidence.

## Roadmap

- v36.0 — Planning and Compatibility Gate
- v36.1 — Source Registry and Capture Integrity
- v36.2 — Canonical Observation Contract
- v36.3 — Entity Candidate Resolution
- v36.4 — Source Independence Graph
- v36.5 — Claim Verification and Alternative Ranking
- v36.6 — Relationship and Timeline Verification
- v36.7 — Versioned Dossier Synthesis
- v36.8 — Entity Accuracy Workspace and Browser E2E

## Required analytical separation

v36 keeps these dimensions independently visible:

- identity confidence;
- factual support;
- source reliability for the claim type;
- capture integrity;
- temporal relevance;
- source independence;
- conflict status;
- human-review status;
- dossier-contribution status.

A display score may summarize visible components, but no unexplained master truth score is permitted.

## Hard boundaries

- no connector or parser truth assignment;
- no automatic entity merge;
- no direct identifier promotion into a canonical entity record;
- no source-count corroboration without dependency grouping;
- no destructive conflict resolution;
- no automatic human-review completion;
- no automatic dossier mutation;
- no competing evidence backend;
- no historical audit mutation;
- no case-access expansion;
- no privacy-purpose or minimization bypass;
- no authentication bypass or collection from private sources without authority.

## Required dossier outcome

A generated dossier must distinguish substantially supported, moderately supported, disputed, superseded, obsolete, rejected, and unresolved claims. It must preserve rejected hypotheses and expose the evidence, limitations, conflicts, review decision, temporal scope, and integrity manifest behind every included statement.

## Entry state

v36.0 is planning-only. Its v35 closure prerequisite is satisfied, but runtime services, routes, migrations, source scoring, entity matching, claim ranking, relationship inference, dossier synthesis, and workspace actions remain unavailable until this planning gate passes and is merged.

## Next action

`implement_v36_1_source_registry_and_capture_integrity`

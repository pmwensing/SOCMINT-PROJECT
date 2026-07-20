# v36.0 Schema Ownership and Non-Duplication Map

## Purpose

Define which existing layer remains authoritative for every v36 concept before runtime work begins. v36 may add append-only analytic records and reproducible projections, but it must not create a competing evidence, identity, review, audit, or dossier backend.

## Ownership map

| Concept | Authoritative owner | v36 responsibility | Prohibited duplication |
|---|---|---|---|
| Case and authorized scope | existing case and scope controls | validate every v36 input and output against the existing case | no parallel case registry or access model |
| Seed identifiers | dossier spine seed records | consume scoped seeds and retain seed provenance | no direct identifier promotion into canonical truth |
| Connector execution | existing connector and closed v35 governance execution layers | record adapter and run bindings | no hidden execution engine or background collector |
| Raw artifacts | existing evidence storage and accepted artifact records | add source-origin and capture-integrity bindings | no second artifact vault or mutable artifact copy |
| Observations | existing spine observations | normalize through a versioned adapter contract and preserve derivation | no replacement observation table or destructive normalization |
| Analytic claims | v30.1 append-only corroboration claims | add typed entity, identifier, relationship, and temporal claim conventions | no mutable canonical fact table |
| Claim source linkage | v30.2 deterministic evidence and observation linkage | include source-registry and independence-group bindings | no untraceable claim support |
| Conflicts | v30.3 append-only conflict and resolution history | add explicit alternative sets and ranking context | no overwriting or deleting competing claims |
| Confidence | v30.4 append-only explainable assessments | add identity, source, temporal, integrity, independence, and ranking dimensions | no opaque truth score or silent confidence mutation |
| Human review | v30.5 append-only review and reassessment | require review of entity-resolution and verification outcomes | no machine approval or inferred consent |
| Dossier eligibility | v30.6 append-only dossier-contribution decisions | consume current approved contribution decisions | no approval implied by confidence alone |
| Identity graph | existing identity graph and merge candidates | add explainable candidate-assessment projections and temporal identifier ownership | no automatic merge or competing graph identity authority |
| Relationships and events | existing graph, timeline, and claim structures | require source, time, confidence dimensions, and inference warnings | no relationship edge without evidence context |
| Audit history | existing append-only AuditLog | append deterministic v36 events and bindings | no historical mutation or private shadow ledger |
| Current-state query views | existing database projections and workspace patterns | add reproducible EntityAccuracySnapshot projections | no projection represented as ground truth |
| Dossier assembly | existing dossier builder and assembly workspaces | synthesize approved contributions by section | no alternate dossier product pipeline |
| Quality and traceability | existing quality, readiness, traceability, approval, and export gates | replace heuristic eligibility inputs with statement-level bindings where v36 applies | no bypass of existing gates |
| Exports and manifests | existing export store, pack, audit, and manifest services | add v36 assessment and source-dependency hashes | no unsigned or unmanifested v36 export |
| Privacy and retention | existing policy, case, role, export, and retention controls | require purpose, scope, minimization, sensitivity, and retention decisions | no public-availability assumption or private-source bypass |

## New v36 records permitted

- `SourceRecord` — original source origin, retrieved location, capture integrity, adapter version, claim-type reliability profile, and independence group
- `CanonicalObservationEnvelope` — deterministic adapter envelope referencing rather than replacing an existing observation
- `EntityResolutionAssessment` — explainable candidate-match signals and a human-reviewed merge or keep-separate recommendation
- `SourceDependencyAssessment` — derivation, mirror, syndication, common-origin, and independence bindings
- `ClaimVerificationAssessment` — dimensional assessment and alternative ranking derived from exact claim, source, linkage, conflict, and limitation hashes
- `RelationshipTimelineAssessment` — source-grounded temporal relationship or event assessment with inference warnings
- `EntityAccuracySnapshot` — reproducible current projection over immutable and append-only records
- `DossierSynthesisSnapshot` — versioned section assembly over currently approved v30 contribution decisions

These records must be append-only events or reproducible projections. None is an unrestricted mutable truth record.

## Identifier rule

Names, usernames, email addresses, phone numbers, domains, account URLs, avatars, device identifiers, and visual fingerprints remain observations or claims until the applicable human review authorizes their intended use. Entity display labels may summarize approved claims but do not replace their history.

## Source rule

Reliability belongs to a source for a particular claim type and assessment context. A domain allowlist, platform name, source count, or tool probability cannot assign reliability by itself.

## Projection rule

An `EntityAccuracySnapshot` is deterministic over exact event and artifact hashes. Repeating the same inputs must produce the same snapshot. Any changed source, linkage, conflict, limitation, review, or contribution decision must produce a new snapshot identifier.

## Runtime prerequisite

The v35 closure prerequisite is satisfied by `release/V35_6_PROGRAM_CLOSURE_CONTRACT.json`. v36.1 may begin only after this ownership map and the complete v36.0 planning gate pass focused and full regression checks and are merged.

# v37.0 — Schema Ownership Map

| Concern | Authoritative owner | v37 responsibility |
|---|---|---|
| Case, purpose, authorization, privacy and minimization | existing case/security/privacy controls | require and expose bindings; do not replace |
| Collection authorization and attempt identity | v29 collection-job contracts | bind imports to the existing contract/export context |
| Raw artifact, hash and custody state | v29 evidence ingestion | require accepted artifact and matching SHA-256 |
| Source provenance and reliability | v36.1 | reference or create through existing source APIs only |
| Canonical observations and quarantine | v36.2 | promote reviewed import records through existing observation authority |
| Identity candidates and merge decisions | v36.3 plus existing identity graph | orchestrate review; never write graph merges automatically |
| Source independence | v36.4 | display dependency context; do not count duplicates as corroboration |
| Claims, conflicts and verification | v30.1–v30.5 and v36.5 | guide review; preserve alternatives and ties |
| Relationships and timelines | v36.6 | assemble reviewed chronology; preserve inference warnings |
| Dossier contributions and snapshots | v30.6 and v36.7 | select reviewed snapshots; do not mutate the dossier backend |
| Redaction, quality, approval, export and publication | existing release/export services | create readiness projections only |
| Audit history | append-only AuditLog | store import, review and readiness events without mutation |

## Non-duplication rules

- no parallel case registry;
- no second artifact vault;
- no second observation authority;
- no second identity graph;
- no mutable canonical fact or truth table;
- no alternate dossier product pipeline;
- no alternate export or publication authority;
- v37 projections must be reproducible from exact event and artifact hashes.

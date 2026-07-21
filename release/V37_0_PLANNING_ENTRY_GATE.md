# v37.0 — Planning Entry Gate

## Gate decision

v37.0 is planning-only. It adds no service, route, migration, collection action, import execution, observation promotion, entity merge, claim decision, dossier mutation, export, or publication capability.

## Required conditions before v37.1

- v36 closure contract exists and records `v36_closed: true`;
- the 46 Montreal case foundation is present on `master` through PR #306, merge `1448fc27e05eb144bf4bdebb83a7aaee6e824d8b`;
- the v37 planning contract and roadmap are merged;
- existing v29–v36 authorities remain the declared owners of artifacts, observations, identity, claims, relationships, dossiers, and exports;
- synthetic fixtures are required for public CI;
- sensitive evidence, credentials, private URLs, and personal cloud links are prohibited from public fixtures.

## Entry-gate invariants

- adapters consume operator-provided exports; they do not run collection tools;
- raw exports are preserved and hash-bound before normalization;
- every import requires case, purpose, operator, artifact, tool, and adapter metadata;
- deterministic reruns cannot create duplicate support;
- quarantine blocks observation promotion and claim support;
- human review controls entity, claim, relationship, contribution, dossier, and export decisions;
- export-readiness is a projection, not an export or publication action.

## Next action

`implement_v37_1_case_scoped_import_envelopes`

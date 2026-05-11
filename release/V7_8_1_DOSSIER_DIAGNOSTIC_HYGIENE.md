# SOCMINT v7.8.1 — Dossier Diagnostic Hygiene + Real-Enrichment Only Legacy Dossier

## Why

The v7.8.0 Intelligence Console and Ultimate Dossier correctly separated real enrichment from connector diagnostics. However, the older Full Entity Profile Dossier v2 still counted diagnostic records as timeline/observation data.

This patch aligns the legacy Full Dossier v2 with the v7.8 truth model.

## Changed

- Full Entity Profile Dossier v2 schema bumped to:
  - `socmint.full_entity_profile_dossier.v7_8_1`
- `connector_no_result` observations are excluded from real observation scoring.
- `seed_expansion_candidate` observations are excluded from real observation scoring.
- ArchiveBox dry-run `archive_candidate` observations are treated as diagnostics unless they contain real capture/snapshot metadata.
- Full Dossier v2 now separates:
  - `Timeline / Real Observations`
  - `Connector Diagnostics`
  - `Dossier Assertions`
- Dossier Score now includes:
  - `real_observation_count`
  - `diagnostic_count`
  - `assertion_count`
  - `evidence_count`
  - existing finding/evidence/custody counts

## Preserved

- Connector diagnostics remain visible for audit/debugging.
- Diagnostics do not count as real observations.
- Ultimate Dossier remains the source-of-truth entity/human report.
- Full Dossier v2 remains available for backward compatibility.

## Validate

```bash
bash scripts/test_v7_8_0.sh
```

Expected:

```text
v7.8.0 ultimate dossier smoke passed
v7.7.0 Spine intelligence smoke passed
v7.8.0 full dossier regression
10 passed
```

## Human-test expectation

For a subject with 10 connector runs that all produce only dry-run/no-result diagnostics:

- Intelligence Console should show:
  - Real enrichment: 0
  - Diagnostics: 10
  - Assertions: 0
- Ultimate Dossier should show:
  - Assertions: 0
  - Real enrichment: 0
  - Trace entries: 0
- Full Dossier v2 should show:
  - real_observation_count: 0
  - diagnostic_count: 10
  - assertion_count: 0
  - Connector Diagnostics section contains the diagnostic rows
  - Timeline / Real Observations contains no connector_no_result rows

# SOCMINT v7.8.0 — Ultimate Entity/Human Dossier Export

This branch is the integrated milestone for:

- v7.7.1 — Real Connector Output Normalizer Coverage Pack
- v7.7.2 — Evidence Binder + Source Traceability
- v7.7.3 — Entity/Human Resolution Model
- v7.7.4 — Dossier Narrative + Timeline Panels
- v7.8.0 — Ultimate Entity/Human Dossier Export

## Why

v7.7.0 established the Spine-native dossier path. v7.8.0 turns that path into an ultimate dossier package by converting connector output into structured observations, tracing assertions back to evidence, resolving whether the subject is entity/human/hybrid, composing narrative panels, and exporting HTML/JSON/CSV outputs.

## v7.7.1 — Real Connector Output Normalizer Coverage Pack

Added `src/socmint/connector_normalizers.py`.

Normalizer coverage:

- Sherlock / Maigret:
  - `profile_url`
  - `platform_presence`
- SocialScan / Holehe:
  - `account_presence`
- h8mail:
  - `exposure_indicator`
  - `exposure_email_reference`
- PhoneInfoga:
  - `phone_country`
  - `phone_carrier`
  - `phone_line_type`
  - `phone_number_type`
  - `phone_valid`
  - `phone_region`
  - `phone_timezone`
- ArchiveBox:
  - `archive_snapshot`
  - skips dry-run `archive_candidate` as non-enrichment
- Generic fallback:
  - `external_url`
  - non-seed email/phone observations

Integrated the normalizer into Spine extraction so raw connector stdout/stderr/JSON can produce dossier-grade observations.

## v7.7.2 — Evidence Binder + Source Traceability

Added source traceability payloads:

- assertion ID
- assertion type/value/confidence/state
- source refs
- evidence refs
- connector run IDs
- connector names
- run status
- raw artifact paths
- SHA256 hashes
- artifact MIME/size metadata

## v7.7.3 — Entity/Human Resolution Model

Added entity/human classification:

- `human_subject`
- `entity_subject`
- `entity_human_hybrid`
- `unresolved_subject`

Resolution metrics:

- identity confidence
- confidence band
- human signal count
- entity signal count
- confirmed assertion count
- high-confidence assertion count
- primary identifiers
- contradiction detection for selected identity metadata

## v7.7.4 — Dossier Narrative + Timeline Panels

Added narrative panels:

- executive summary
- key findings
- evidence posture
- gaps and cautions
- recommended next actions

Added timeline entries from:

- connector runs
- observations
- assertions

## v7.8.0 — Ultimate Entity/Human Dossier Export

Added:

- `src/socmint/ultimate_dossier.py`
- `src/socmint/ultimate_dossier_routes.py`
- `src/socmint/templates/ultimate_dossier.html`

New routes:

- `GET /spine/subjects/<subject_id>/ultimate-dossier`
- `GET /api/v1/spine/subjects/<subject_id>/ultimate-dossier`
- `GET /spine/subjects/<subject_id>/ultimate-dossier/assertions.csv`

Exports:

- HTML dossier
- JSON dossier package
- CSV assertion index

## Validate

```bash
bash scripts/test_v7_8_0.sh
```

## Smoke coverage

The v7.8.0 smoke test verifies:

- connector normalizers produce structured observations
- deterministic Spine runs, raw artifacts, observations, and assertions are created
- source traceability is generated
- entity/human resolution is generated
- executive narrative is generated
- timeline is generated
- assertion CSV export works
- HTML dossier route works
- JSON dossier route works
- CSV route works
- v7.7.0 Spine intelligence regression still passes
- Full Dossier regression still passes

## Primary analyst path

```text
/spine
/spine/subjects/<id>/intelligence
/spine/subjects/<id>/ultimate-dossier
/spine/subjects/<id>/dossier
```

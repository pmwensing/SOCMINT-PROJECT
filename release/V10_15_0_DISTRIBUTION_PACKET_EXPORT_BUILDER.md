# SOCMINT v10.15.0 — Distribution Packet Export Builder

## Summary

Adds a ZIP export builder for approved distribution packets. The builder packages the distribution decision, certification data, operator action history, dossier manifest, markdown statement, and available dossier artifacts into a downloadable release bundle.

## Focus

The export builder answers:

- Is the packet certified and operator approved?
- Can a downloadable distribution ZIP be built?
- Which files were included in the release bundle?
- What is the ZIP SHA-256 digest and size?
- Which manifest records the export contents?

## Changes

- Adds `src/socmint/distribution_packet_export.py`.
- Adds `src/socmint/distribution_packet_export_routes.py`.
- Registers routes in `src/socmint/wsgi.py`.
- Adds export build/download links to `src/socmint/templates/certification_dashboard.html`.
- Adds `tests/test_distribution_packet_export_v10_15.py`.
- Adds `scripts/test_v10_15.sh`.

## Routes

- `POST /api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/build`
- `GET /api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>`
- `GET /api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/download`

## ZIP contents

- `README.txt`
- `distribution_statement.md`
- `distribution_packet.json`
- `dossier_manifest.json`
- `operator_action_log.jsonl`
- `operator_action_summary.json`
- `artifacts/*`

## Gate behavior

The builder refuses to create the ZIP unless the packet is both certified and operator approved.

## Persistence

Distribution ZIPs are written under:

```text
exports/distribution_packets/<case_id>/<subject_id>/distribution_packet.zip
```

The export manifest is written to:

```text
exports/distribution_packets/<case_id>/<subject_id>/distribution_export_manifest.json
```

## Merge gate

Run:

```bash
bash scripts/test_v10_15.sh
```

or:

```bash
PYTHONPATH=src pytest -q tests/test_distribution_packet_export_v10_15.py tests/test_distribution_actions_v10_14.py tests/test_certification_dashboard_v10_13.py tests/test_dossier_certification_index_v10_12.py
```

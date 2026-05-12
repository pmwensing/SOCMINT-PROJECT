# SOCMINT v8.0.0 - High-End SOCMINT Workflows

This milestone adds the product layer needed for a polished analyst workflow:
evidence capture, case management, analyst console, connector marketplace,
entity-resolution lab, graph canvas, export builder, and responsible-use gates.

## Core Storage

- `case_records`
- `case_events`
- `evidence_captures`
- `responsible_use_scope`

Migration: `0008_high_end_socmint_workflows`.

## Analyst Surfaces

```text
/analyst/console
/cases
/evidence/capture
/connectors/marketplace
/responsible-use
/exports/builder
/spine/<id>/graph/canvas
/spine/<id>/resolution-lab
```

## API Surfaces

```text
/api/v1/analyst/workbench
/api/v1/evidence/capture
/api/v1/evidence/captures
/api/v1/evidence/captures/<capture_id>/verify
/api/v1/cases
/api/v1/cases/<case_key>
/api/v1/connectors/marketplace
/api/v1/responsible-use/scope
/api/v1/responsible-use/review
/api/v1/responsible-use/gate
/api/v1/exports/builder
/api/v1/spine/<subject_id>/graph/canvas
/api/v1/spine/<subject_id>/resolution-lab
```

## Validation

```bash
ruff check src tests scripts
pytest -q tests/test_high_end_workflows.py
```

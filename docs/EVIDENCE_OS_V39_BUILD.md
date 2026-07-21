# Evidence OS v39.0 Foundation

## Purpose

This release begins the evidence-first case intelligence layer without replacing the existing dossier, case-access, or collection systems.

The governed flow is:

```text
Immutable evidence -> proposed observation -> human review -> approved finding -> dossier/report
```

## Delivered in v39.0.0

- Immutable evidence item registry with SHA-256 deduplication.
- Per-case evidence keys and source metadata.
- Proposed observations linked to source evidence.
- Explicit evidence classifications and bounded confidence values.
- Human review states: `approved`, `rejected`, and `needs_work`.
- Audit events for evidence ingestion and observation review.
- Additive schema creation compatible with the repository's existing runtime style.

## Initial tables

- `evidence_items`
- `evidence_observations`
- `evidence_findings`
- `finding_observations`

The findings tables are created now so later releases can add approval and report-generation services without another foundational redesign.

## Integrity rules

1. Evidence source rows are never updated by the ingestion API.
2. Duplicate content within a case resolves to the existing SHA-256 record.
3. Observations begin as `proposed` and cannot silently become findings.
4. Confidence is constrained to the inclusive range 0.0-1.0.
5. AI- or analyst-generated statements remain separate from source evidence.
6. All review decisions are attributable to an actor and written to the audit log.

## Next increments

### v39.1 — Findings and claim links

- Create approved findings from reviewed observations.
- Link findings to claim families, proceedings, authorities, entities, and timeline events.
- Require at least one approved observation for each approved finding.

### v39.2 — Evidence API and workspace

- Authenticated case-scoped API endpoints.
- Case access enforcement using `case_access_decision`.
- Evidence list, detail, observation review, and integrity-status views.

### v39.3 — 46 Montreal Street import adapter

- Import the controlled exhibit register.
- Preserve the pre-fire/post-fire proceeding boundary.
- Apply the Cowdy Street scope restriction.
- Produce a deterministic import report instead of silently merging records.

## Verification target

```bash
pytest -q tests/test_v39_0_evidence_os.py
```

The release should not be merged until the focused tests and the repository's normal CI gates pass.

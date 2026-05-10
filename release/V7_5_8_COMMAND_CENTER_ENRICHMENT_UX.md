# SOCMINT v7.5.8 — Next-Level SOCMINT Command Center UX + Enrichment Flow Repair

## Added

- New SOCMINT Command Center landing page.
- Unified analyst next-step workflow:
  1. Create/select subject
  2. Add seeds and run connectors
  3. Review enrichment
  4. Generate Full Report
  5. Export/evidence readiness
- Command-center metrics for:
  - subjects
  - queued jobs
  - running jobs
  - failed jobs
  - findings
- Worker/job status guidance.
- Local/dev `Process queued jobs now` button.
- Enrichment tool compatibility warnings.
- Tool compatibility guidance by target type.
- Subject action cards linking to:
  - subject dossier
  - Full Dossier v2
  - export history
  - retention / pins
- Command Center JSON endpoint.
- v7.5.8 command-center UX smoke.
- `make test758` and `make zip758`.

## New routes

- `GET /api/v1/command-center`
- `POST /command-center/process-jobs`

## UX repair

The old dashboard made the older target-scan flow dominant and hid the newer Spine / Full Dossier v2 workflow. v7.5.8 makes the v7.5.x workflow the primary landing experience and clearly labels the older target scan as a legacy/local scan path.

## Enrichment repair

The Command Center now warns when the target type and tools are mismatched. Example: email targets with username-first tools such as Sherlock or Maigret show a visible warning and suggestions.

## Safety / workflow behavior

- Existing v7.5.7 retention safety remains intact.
- Queue processing is explicit and visible.
- Completed jobs link toward results when available.
- Users can start from `/` without knowing route names.

## Validate

```bash
make test758
```

## Covered by smoke

- Command Center renders.
- Command Center API returns `socmint.command_center.v7_5_8`.
- Subject card renders and links toward Full Dossier v2.
- Job queue and worker status panel renders.
- Email + Sherlock/Maigret mismatch warning renders.
- `Process queued jobs now` action processes queued job.
- v7.5.7 retention UI regression still passes.
- Full Dossier v7.5 regression tests still pass.

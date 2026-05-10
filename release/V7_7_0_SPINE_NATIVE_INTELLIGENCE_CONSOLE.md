# SOCMINT v7.7.0 — Spine-Native Subject Intelligence Console + Dossier-First Review Pipeline

## Why

v7.6.x proved connector activation, but the review workflow split into two competing paths:

1. Legacy target/connector path:
   - `targets`
   - `connector_runs`
   - `findings`

2. Desired dossier path:
   - `spine_subjects`
   - `spine_seeds`
   - `spine_connector_runs`
   - `spine_raw_artifacts`
   - `spine_observations`
   - `spine_dossier_assertions`

The project goal is the Full Entity Profile Dossier, so v7.7.0 pivots the UI and review workflow back to Spine as the single source of truth.

## Added

- New Spine-native Subject Intelligence Console:
  - `/spine/subjects/<subject_id>/intelligence`
- New API payload:
  - `/api/v1/spine/subjects/<subject_id>/intelligence`
- Dossier-first subject workflow:
  - seeds
  - compatible connectors
  - Spine connector runs
  - raw artifacts
  - normalized observations
  - dossier assertions
  - validation states
- Run selected compatible connectors directly into Spine.
- Promote a Spine observation into a confirmed dossier assertion.
- Review assertion state from the intelligence console:
  - confirmed
  - rejected
  - suppressed
  - unreviewed
- Raw stdout/stderr/JSON viewer for Spine connector runs.
- Artifact checksum/metadata display.
- Dossier readiness metrics.
- Subject list links to Intelligence Console and Full Dossier v2.
- Global nav link to Spine Intelligence.
- Legacy enrichment review relabeled as Legacy Review.

## New routes

- `GET /spine/subjects/<subject_id>/intelligence`
- `POST /spine/subjects/<subject_id>/intelligence/run`
- `POST /spine/observations/<observation_id>/promote`
- `POST /spine/intelligence/assertions/<assertion_id>/review`
- `GET /api/v1/spine/subjects/<subject_id>/intelligence`
- `POST /api/v1/spine/subjects/<subject_id>/intelligence/run`
- `POST /api/v1/spine/observations/<observation_id>/promote`
- `POST /api/v1/spine/intelligence/assertions/<assertion_id>/review`

## Validate

```bash
bash scripts/test_v7_7_0.sh
```

## Smoke coverage

- Creates a Spine subject with username/email/phone/url seeds.
- Verifies connector compatibility options.
- Runs selected connectors into Spine.
- Verifies Spine connector runs, artifacts, observations, and assertions.
- Promotes an observation into a confirmed assertion.
- Reviews assertions as rejected and confirmed.
- Opens the Intelligence Console UI.
- Verifies raw output sections render.
- Verifies API payloads and actions.
- Verifies subject list links to Intelligence Console and Full Dossier v2.
- Runs v7.6.1 connector runtime repair regression.
- Runs Full Dossier regression.

## Strategic change

v7.7.0 intentionally avoids expanding the legacy `/connectors/runs` and `/connectors/findings` path. The primary analyst path is now:

```text
/spine → /spine/subjects/<id>/intelligence → /spine/subjects/<id>/dossier
```

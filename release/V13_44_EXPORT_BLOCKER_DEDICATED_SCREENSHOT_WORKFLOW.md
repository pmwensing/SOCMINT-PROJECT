# v13.44 - Export Blocker Dedicated Screenshot Workflow

## Scope

This build adds a dedicated screenshot capture workflow, stricter manifest validation, and operator-facing manifest access.

## Included

- Dedicated GitHub workflow: `.github/workflows/export-blocker-screenshots.yml`
- Manifest refresh fails when required screenshot files are missing
- Export Blockers manifest JSON API
- Export Blockers manifest download route
- Export Blockers UI links to the manifest routes
- Regression tests for workflow wiring, manifest validation, manifest API, download route, and UI links

## Operator Result

Operators can run a dedicated screenshot workflow, fail fast on missing screenshot artifacts, and retrieve the screenshot artifact manifest from the Export Blockers page.

## Workflow Artifact

- Workflow: `.github/workflows/export-blocker-screenshots.yml`
- Artifact name: `export-blocker-screenshots-${{ github.run_id }}`
- Manifest: `release/V13_42_EXPORT_BLOCKER_SCREENSHOT_ARTIFACT_MANIFEST.json`
- Runtime screenshots: `runtime_screenshots_v13_40/**`

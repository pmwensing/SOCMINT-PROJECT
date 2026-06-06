# v13.42 - Export Blocker Artifact Manifest and Smoke

## Scope

This build documents the export blocker screenshot artifacts and adds pre-capture route smoke coverage for the screenshot target pages.

## Included

- Release artifact manifest: `release/V13_42_EXPORT_BLOCKER_SCREENSHOT_ARTIFACT_MANIFEST.json`
- Runbook section for `make export-blocker-runtime-screenshots`
- UI smoke tests for the allowed and denied Export Blockers screenshot target URLs
- Regression test coverage for the release artifact manifest

## Operator Result

Operators have a documented workflow and manifest for the export blocker screenshots, and tests verify the target pages return successfully before browser capture.

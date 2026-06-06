# v13.45 - Export Blocker Workflow Docs and Route Health

## Scope

This build documents the dedicated export blocker screenshot workflow and adds support-bundle route-health coverage for the screenshot manifest routes.

## Included

- Runbook instructions for the GitHub **Export Blocker Screenshots** workflow
- Release note artifact reference for `export-blocker-screenshots-${{ github.run_id }}`
- Support bundle route health entries for screenshot manifest JSON and download routes
- Regression tests for runbook documentation, release artifact references, and route-health resolution

## Operator Result

Operators can find the screenshot workflow instructions in the runbook, identify the uploaded artifact from release notes, and verify manifest route registration through the support bundle.

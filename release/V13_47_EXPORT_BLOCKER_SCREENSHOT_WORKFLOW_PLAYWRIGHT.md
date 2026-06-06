# V13.47 Export Blocker Screenshot Workflow Playwright Install

## Summary

- Fixed the dedicated Export Blocker Screenshots workflow by installing the Python Playwright package before invoking `python -m playwright install --with-deps chromium`.
- Added a workflow guard assertion so the Playwright package install stays present in the dedicated workflow.

## Triggered Run

- Initial run `27052059614` failed in `Install dependencies` because `python -m playwright` was unavailable.
- The workflow should be rerun after this fix is pushed.

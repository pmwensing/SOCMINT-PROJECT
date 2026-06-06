# V13.48 Export Blocker Screenshot Workflow Make Python

## Summary

- Fixed the dedicated Export Blocker Screenshots workflow capture step by passing `PYTHON=python` and `SCREENSHOT_PYTHON=python` to the Make target.
- Added a workflow guard assertion so GitHub Actions does not depend on a local `venv/bin/python` checkout layout during screenshot capture.

## Triggered Run

- Run `27052124885` passed dependency install and runtime startup, then failed in capture because the Make target used `venv/bin/python`.
- The workflow should be rerun after this fix is pushed.

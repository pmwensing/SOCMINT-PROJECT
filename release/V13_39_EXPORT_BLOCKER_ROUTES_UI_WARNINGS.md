# v13.39 - Export Blocker Routes, UI, and Warning Hygiene

## Scope

This build adds route-level coverage and an operator UI panel for export blockers, then quiets a known SQLite datetime adapter deprecation warning in pytest.

## Included

- Flask route tests for export pack summary blocker details
- Flask route tests for export gate decision verification summaries
- Operator UI page at `/dossier/export-blockers`
- Dossiers & Reports navigation entry for Export Blockers
- Narrow pytest warning filter for SQLAlchemy SQLite datetime adapter deprecation noise

## Operator Result

Operators can inspect export gate blockers from a browser page, and API route tests now verify that blocker details survive the HTTP layer.

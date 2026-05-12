# SOCMINT v8.0.1 - Browser Capture And Export Bundles

This milestone turns the v8.0.0 workflow layer into a stronger
evidence-first product surface.

## Browser Capture

- Browser capture mode now stores HTML, screenshot, PDF, MHTML, and manifest
  artifacts for a capture group.
- Capture artifacts use deterministic names, SHA-256 hashes, database records,
  and chain-of-custody events.
- Playwright is used when available; controlled imports and test environments
  use a deterministic fallback that still produces the same artifact classes.
- Capture manifests include actor, URL, case, subject, headers, cookies
  metadata, automation mode, and artifact hashes.

## Export Bundles

- High-end export bundles now produce signed ZIP packages.
- Bundle manifests include subject, case, redaction preset, supported formats,
  export blockers, file hashes, bundle hash, and signature hash.
- Bundle verification confirms expected files are present and reports the ZIP
  SHA-256.

## API Additions

```text
POST /api/v1/exports/builder/bundle
GET /api/v1/exports/builder/bundles/<name>/verify
```

## Validation

```bash
ruff check src tests scripts
pytest -q tests/test_high_end_workflows.py
```

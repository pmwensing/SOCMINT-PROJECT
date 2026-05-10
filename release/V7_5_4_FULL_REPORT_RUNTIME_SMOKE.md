# SOCMINT v7.5.4 — Full Report Runtime Smoke: Generate → Open → Verify Manifest Hashes

## Added

- Runtime smoke script for the full-report flow.
- End-to-end generation of a Full Entity Profile Dossier v2 export in a temporary workspace.
- Manifest SHA-256 verification for every exported artifact.
- Flask test-client browser flow checks for:
  - latest export API
  - export status panel
  - open latest HTML report redirect
  - HTML report rendering
  - manifest artifact rendering
- `make test754` and `make zip754`.

## Runtime smoke

The smoke test performs:

1. Generate full-report export.
2. Load and verify `*-export_manifest.json`.
3. Recompute SHA-256 for every manifest artifact.
4. Build a Flask app with full-report alias and browser-flow routes.
5. Simulate an authenticated admin session.
6. Open `/api/v1/spine/subjects/{subject_id}/full-report/latest`.
7. Open `/spine/subjects/{subject_id}/full-report/view`.
8. Open `/spine/subjects/{subject_id}/full-report/open`.
9. Follow the HTML report redirect.
10. View the manifest artifact in-browser.

## Validate

```bash
make test754
```

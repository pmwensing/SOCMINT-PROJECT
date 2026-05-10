# SOCMINT v7.5.3 — Full Report End-to-End Browser Flow + Export Open/View Panel

## Added

- Browser-facing full-report export panel.
- Open latest HTML report route.
- View manifest/artifact route for browser-readable export artifacts.
- Dossier page links for:
  - View Export Panel
  - Open Latest HTML Report
  - View Manifest
- `src/socmint/full_report_browser.py` browser-flow route module.
- WSGI registration for browser-flow routes.
- `make test753` and `make zip753`.

## New browser routes

- `GET /spine/subjects/{subject_id}/full-report/view`
- `GET /spine/subjects/{subject_id}/full-report/open`
- `GET /spine/subjects/{subject_id}/full-report/artifact?name={artifact_name}`

## Validate

```bash
make test753
```

## Expected analyst flow

1. Open `/spine/subjects/{subject_id}/dossier`.
2. Click **Run Full Report**.
3. Return to the dossier page.
4. Use **View Export Panel** or **Open Latest HTML Report**.
5. Use **View Manifest** to inspect SHA-256 export metadata in-browser.

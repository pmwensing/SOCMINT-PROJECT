# SOCMINT v7.5.6 — Full Report Retention + Pin Important Exports + Delete Old Exports

## Added

- Full-report retention planning.
- Pin/unpin support for important exports.
- Subject-scoped deletion of unpinned exports.
- Dry-run retention application.
- Browser-facing retention page.
- API routes for retention, pin, unpin, delete, and apply-retention.
- Dossier UI link for **Retention / Pins**.
- Runtime smoke covering retention behavior and delete safety.
- `make test756` and `make zip756`.

## New routes

- `GET /api/v1/spine/subjects/{subject_id}/full-report/retention`
- `POST /api/v1/spine/subjects/{subject_id}/full-report/pin`
- `POST /api/v1/spine/subjects/{subject_id}/full-report/unpin`
- `POST /api/v1/spine/subjects/{subject_id}/full-report/delete`
- `POST /api/v1/spine/subjects/{subject_id}/full-report/apply-retention`
- `GET /spine/subjects/{subject_id}/full-report/retention`

## Safety behavior

- Pinned exports are protected from deletion unless force is explicitly used.
- Delete actions are subject-scoped through export history lookup.
- Artifact deletion is based on the selected export result and its manifest-derived artifact list.
- Retention can run as dry-run before deleting any artifacts.

## Runtime smoke

The v7.5.6 smoke test performs:

1. Generate three full-report exports.
2. Pin an important baseline export.
3. Build a retention plan with `keep_latest=1`.
4. Confirm pinned and latest exports are retained.
5. Confirm older unpinned exports become delete candidates.
6. Confirm dry-run retention does not delete artifacts.
7. Confirm deletion of pinned export is blocked.
8. Delete an unpinned export and verify history updates.
9. Unpin export and verify pin count updates.
10. Verify retention API, pin API, delete API, and browser retention panel.
11. Run existing dossier regression tests.

## Validate

```bash
make test756
```

# SOCMINT v7.5.7 — Retention UI Action Buttons + CSRF Forms + Confirm Delete Dialog

## Added

- Browser UI action forms on the full-report retention page.
- CSRF-safe forms for:
  - pin important export
  - unpin export
  - dry-run retention
  - apply retention
  - delete individual export
- Exact filename confirmation field for delete actions.
- `APPLY` confirmation field before applying retention deletion.
- Status messages after browser actions.
- Human-equivalent UI action smoke test.
- `make test757` and `make zip757`.

## New UI routes

- `POST /spine/subjects/{subject_id}/full-report/pin`
- `POST /spine/subjects/{subject_id}/full-report/unpin`
- `POST /spine/subjects/{subject_id}/full-report/delete`
- `POST /spine/subjects/{subject_id}/full-report/apply-retention`

## Safety behavior

- Delete action requires typing the exact export filename.
- Pinned exports remain blocked from deletion even with exact UI confirmation.
- Applying retention deletion requires typing `APPLY`.
- Dry-run is available as a browser action before destructive retention.
- API force-delete remains excluded from the browser UI.

## Validate

```bash
make test757
```

## Human UI flow covered

1. Generate three reports.
2. Open retention page.
3. Confirm action buttons render.
4. Pin an older export from UI.
5. Try delete with wrong confirmation and confirm block.
6. Try delete pinned export with exact confirmation and confirm block.
7. Dry-run retention from UI.
8. Attempt apply retention without `APPLY` and confirm block.
9. Unpin export from UI.
10. Delete unpinned export with exact filename confirmation.
11. Confirm history updates.

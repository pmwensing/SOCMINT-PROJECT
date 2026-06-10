# v13.11 - Normalization Form Update

## Purpose

Document the normalization review update route hardening that lets the review UI submit ordinary form posts as well as JSON payloads.

## Added

- `normalization_update_payload()` helper for the v13 normalization review update route.
- JSON payload handling remains the first choice when a request body contains JSON.
- Form payload fallback uses `request.form` when JSON is absent.

## Verification

- Historical implementation commit: `6f5773f`
- Focused route coverage: `tests/test_normalization_review_update_routes_v13.py`

## Value

Operators can submit normalization review decisions from browser forms without requiring a JSON-only client path.

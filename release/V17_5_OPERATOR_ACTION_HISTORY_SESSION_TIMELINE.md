# v17.5 Operator Action History / Session Timeline

The v17.5 layer presents recent operator action receipts and receipt-verification results as a readable in-session timeline on the unified operator dashboard.

- Dashboard UI: `/operator/workflow-dashboard?case_id=<case_id>`
- History API: `GET /api/v1/operator/workflow-dashboard/<case_id>/actions/history`

## Session timeline behavior

- Every v17.2 action response appends its v17.3 receipt and v17.4 verification result to the authenticated Flask session.
- Dedicated receipt verification responses also update the same session timeline.
- Timeline entries are filtered by authenticated operator and case id.
- Entries are displayed newest first.
- Duplicate receipt ids replace the older session entry.
- Session history is capped at 20 entries to limit cookie/session growth.

## Dashboard presentation

The dashboard shows:

- total session events
- verified action count
- blocked action/verification count
- confirmation-required count
- timestamp, action, result, verification status, action target, and abbreviated receipt id

The timeline is explicitly marked `flask_session_only`. It is not written to the database and disappears when the login session is cleared or expires.

## Validation

- Focused regression coverage in `tests/test_v17_5_operator_action_session_timeline.py`.
- No database persistence, schema mutation, or migration is introduced.

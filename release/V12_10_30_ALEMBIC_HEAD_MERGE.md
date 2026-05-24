# v12.10.30 — Alembic Head Merge + True Clean Bootstrap

Target:
- Make `0017_v12_10_schema_reconciliation` part of the real Alembic migration chain.
- Ensure Alembic sees v12.10 schema reconciliation as the current head.
- Replace static-only validation with head/path validation.

Expected head:
`0017_v12_10_schema_reconciliation`

# v12.10.45 — identity_columns SQLite Smoke Repair

Purpose:
1. Target current v12.10.44 blocker: `identity_columns`.
2. Patch only the `identity_columns` create_table block in promoted 0018.
3. Remove duplicate column declarations.
4. Remove executable TODO placeholders.
5. Remove/neutralize FK args for temp SQLite smoke safety.
6. Preserve TODOs as comments.
7. Rerun v12.10.38, v12.10.39, v12.10.42, and v12.10.44.
8. Do not run real DB upgrade.
9. Do not touch production DB.

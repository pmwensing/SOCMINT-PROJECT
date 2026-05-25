# v12.10.45A — Missing Approved Table Block Detector + Repair Gate

Purpose:
- Correct v12.10.45 failure where locator identified `identity_columns`,
  but promoted 0018 had no `op.create_table("identity_columns")` block.
- Detect approved tables missing from the promoted migration file.
- Separate:
  - tables missing because upgrade failed before reaching them
  - tables missing because no create_table block exists
- Produce a safe repair report.
- Do not auto-create missing table blocks yet.
- Do not run real DB upgrade.
- Do not touch production DB.

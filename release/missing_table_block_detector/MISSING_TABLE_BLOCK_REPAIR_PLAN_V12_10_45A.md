# v12.10.45A Missing Table Block Repair Plan

Do not patch a nonexistent create_table block.

## Structural missing approved tables

- none

## v12.10.45B plan

If structural missing tables exist:

1. Read v12.10.33 candidate JSON for the missing tables.
2. Reconstruct create_table blocks from approved extracted column hints.
3. Insert missing create_table blocks into upgrade in approved-table order.
4. Insert missing drop_table calls into downgrade reverse order.
5. Validate static symmetry.
6. Rerun temp SQLite smoke.
7. Do not run real DB upgrade.

If no structural missing tables exist:

- Use the v12.10.42 failed table repair target and patch the existing block.
# v12.10.34 Migration Creation Refusal

This build refuses to create an executable Alembic migration.

Reasons:

1. v12.10.34 is a human review gate only.
2. The P0/P1 candidate list still requires explicit human approval.
3. Column definitions still contain TODO review items.
4. Tables marked REVIEW or PASS_WITH_REVIEW_NOTES require manual sign-off.
5. Schema mutation must not occur until `approved_migration_set.json` is reviewed.

Allowed outputs:

- Human review checklist
- Review queues
- Approval template
- `approved_migration_set.json` metadata after approval file is supplied

Forbidden in this build:

- Writing to `alembic/versions`
- Running `alembic revision`
- Running `alembic upgrade`
- Creating executable migration files
- Modifying database schema

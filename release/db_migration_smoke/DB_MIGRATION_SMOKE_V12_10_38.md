# v12.10.38 Dry-Run DB Migration Smoke Report

- **smoke_status**: `NO-GO`
- **schema_mutation**: `temp_sqlite_only`
- **production_db_touched**: `False`
- **real_config_upgrade_run**: `False`
- **approved_table_count**: `18`
- **tables_after_upgrade_count**: `52`
- **missing_after_upgrade**: `2`
- **lingering_after_downgrade**: `16`
- **version_after_upgrade**: `0017_v12_10_schema_reconciliation`
- **version_after_downgrade**: `0017_v12_10_schema_reconciliation`
- **temp_db_path**: `/tmp/socmint_v12_10_38_8zv6531k/dry_run.sqlite`

## Errors

- alembic upgrade head failed against temp SQLite DB

## Warnings

- none

## Step outputs

### alembic_heads_temp_config returncode=0

```text
0018_approved_model_migration (head)

```

### upgrade_head_temp_sqlite returncode=1

```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema, initial schema
INFO  [alembic.runtime.migration] Running upgrade 0001_initial_schema -> 0002_audit_logs_and_indexes, audit logs and rate-limit indexes
INFO  [alembic.runtime.migration] Running upgrade 0002_audit_logs_and_indexes -> 0003_user_status_and_constraints, user status and stricter constraints
INFO  [alembic.runtime.migration] Running upgrade 0003_user_status_and_constraints -> 0004_roles_and_scan_jobs, roles and scan jobs
INFO  [alembic.runtime.migration] Running upgrade 0004_roles_and_scan_jobs -> 0005_v7_1_model_sync, v7.1 model sync
INFO  [alembic.runtime.migration] Running upgrade 0005_v7_1_model_sync -> 0006_v7_2_1_review_decisions, v7.2.1 review decision persistence
INFO  [alembic.runtime.migration] Running upgrade 0006_v7_2_1_review_decisions -> 0007_v7_2_2_review_decision_audit, v7.2.2 review decision audit trail and bulk actions
INFO  [alembic.runtime.migration] Running upgrade 0007_v7_2_2_review_decision_audit -> 0008_high_end_socmint_workflows, high-end SOCMINT workflow tables
INFO  [alembic.runtime.migration] Running upgrade 0008_high_end_socmint_workflows -> 0009_account_discovery_ingest, account discovery ingest table
INFO  [alembic.runtime.migration] Running upgrade 0009_account_discovery_ingest -> 0010_membership_quotas, membership and quota tables
INFO  [alembic.runtime.migration] Running upgrade 0010_membership_quotas -> 0011_billing, billing tables
INFO  [alembic.runtime.migration] Running upgrade 0011_billing -> 0012_tor_status, tor status table
INFO  [alembic.runtime.migration] Running upgrade 0012_tor_status -> 0013_billing_customer_links, billing customer links
INFO  [alembic.runtime.migration] Running upgrade 0013_billing_customer_links -> 0014_case_access, case access tables
INFO  [alembic.runtime.migration] Running upgrade 0014_case_access -> 0017_v12_10_schema_reconciliation, v12.10.30 schema reconciliation command-center tables
INFO  [alembic.runtime.migration] Running upgrade 0017_v12_10_schema_reconciliation -> 0018_approved_model_migration, v12.10.37 APPROVED MODEL MIGRATION
Traceback (most recent call last):
  File "/home/pmwens/Projects/SOCMINT-PROJECT/var/venvs/v12_10_17/bin/alembic", line 6, in <module>
    sys.exit(main())
             ~~~~^^
  File "/home/pmwens/Projects/SOCMINT-PROJECT/var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/config.py", line 1047, in main
    CommandLine(prog=prog).main(argv=argv)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "/home/pmwens/Projects/SOCMINT-PROJECT/var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/config.py", line 1037, in main
    self.run_cmd(cfg, options)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "/home/pmwens/Projects/SOCMINT-PROJECT/var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/config.py", line 971, in run_cmd
    fn(
    ~~^
        config,
        ^^^^^^^
        *[getattr(options, k, None) for k in positional],
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        **{k: getattr(options, k, None) for k in kwarg},
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/home/pmwens/Projects/SOCMINT-PROJECT/var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/command.py", line 483, in upgrade
    script.run_env()
    ~~~~~~~~~~~~~~^^
  File "/home/pmwens/Projects/SOCMINT-PROJECT/var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/script/base.py", line 545, in run_env
    util.load_python_file(self.dir, "env.py")
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
  File "/home/pmwens/Projects/SOCMINT-PROJECT/var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/util/pyfiles.py", line 116, in load_python_file
    module = load_module_py(module_id, path)
  File "/home/pmwens/Projects/SOCMINT-PROJECT/var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/util/pyfiles.py", line 136, in load_module_py
    spec.loader.exec_module(module)  # type: ignore
    ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "<frozen importlib._bootstrap_external>", line 1023, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/home/pmwens/Projects/SOCMINT-PROJECT/migrations/env.py", line 53, in <module>
    run_migrations_online()
    ~~~~~~~~~~~~~~~~~~~~~^^
  File "/home/pmwens/Projects/SOCMINT-PROJECT/migrations/env.py", line 47, in run_migrations_online
    context.run_migrations()
    ~~~~~~~~~~~~~~~~~~~~~~^^
  File "<string>", line 8, in run_migrations
  File "/home/pmwens/Projects/SOCMINT-PROJECT/var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/runtime/environment.py", line 969, in run_migrations
    self.get_context().run_migrations(**kw)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/home/pmwens/Projects/SOCMINT-PROJECT/var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/runtime/migration.py", line 626, in run_migrations
    step.migration_fn(**kw)
    ~~~~~~~~~~~~~~~~~^^^^^^
  File "/home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0018_approved_model_migration.py", line 32, in upgrade
    sa.Column("connector_key", sa.String(length=TODO), nullable=False),  # TODO: confirm type/nullability/default
                                                ^^^^
NameError: name 'TODO' is not defined

```

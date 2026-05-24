# v12.10.31E Drift Lock Audit Report

Overall: **FAIL**

## Summary

- **overall_status**: `FAIL`
- **drift_lock**: `FAIL`
- **fail_count**: `1`
- **warn_count**: `1`
- **framework**: `flask`
- **primary_entrypoint**: `src/socmint/dashboard.py`
- **alembic_heads**: `0017_v12_10_schema_reconciliation`
- **missing_v12_routes**: `8`
- **dashboard_module_file**: `/home/pmwens/Projects/SOCMINT-PROJECT/src/socmint/dashboard.py`
- **route_lock_errors**: `0`
- **route_lock_registered**: ``
- **route_lock_skipped**: ``
- **model_tables_missing_migrations**: `202`
- **version_unique_count**: `1`
- **report_json**: `/home/pmwens/Projects/SOCMINT-PROJECT/release/drift_lock/DRIFT_LOCK_AUDIT_V12_10_31E.json`
- **report_md**: `/home/pmwens/Projects/SOCMINT-PROJECT/release/drift_lock/DRIFT_LOCK_AUDIT_V12_10_31E.md`

## Checks

### framework_detection: PASS

```json
{
  "fastapi_count": 0,
  "fastapi_hits": [],
  "flask_count": 112,
  "flask_hits": [
    ".connector-tools/venv/lib/python3.13/site-packages/flask/app.py",
    ".connector-tools/venv/lib/python3.13/site-packages/flask/ctx.py",
    ".connector-tools/venv/lib/python3.13/site-packages/flask/helpers.py",
    ".connector-tools/venv/lib/python3.13/site-packages/flask/sansio/app.py",
    ".connector-tools/venv/lib/python3.13/site-packages/flask/sessions.py",
    ".connector-tools/venv/lib/python3.13/site-packages/jedi/plugins/registry.py",
    ".connector-tools/venv/lib/python3.13/site-packages/maigret/web/app.py",
    "src/socmint/analyst_ux_routes.py",
    "src/socmint/assertion_trust_gate_routes_v12_8_1.py",
    "src/socmint/assertion_trust_routes_v12_8.py",
    "src/socmint/authenticity_integrity_routes_v12_7.py",
    "src/socmint/beta_readiness_routes.py",
    "src/socmint/billing_integration_routes.py",
    "src/socmint/billing_routes.py",
    "src/socmint/build_audit_routes.py",
    "src/socmint/case_access_routes.py",
    "src/socmint/certification_dashboard_routes.py",
    "src/socmint/certification_routes.py",
    "src/socmint/command_center_routes.py",
    "src/socmint/connector_runtime_routes.py",
    "src/socmint/connector_sdk_routes.py",
    "src/socmint/dashboard.py",
    "src/socmint/distribution_action_routes.py",
    "src/socmint/distribution_export_verification_routes.py",
    "src/socmint/distribution_handoff_packet_routes.py",
    "src/socmint/distribution_packet_export_routes.py",
    "src/socmint/distribution_release_ledger_routes.py",
    "src/socmint/dossier_builder_v3_routes.py",
    "src/socmint/dossier_certification_index_routes.py",
    "src/socmint/dossier_export_audit_routes.py",
    "src/socmint/dossier_export_certification_routes.py",
    "src/socmint/dossier_export_gate_routes.py",
    "src/socmint/dossier_export_index_routes.py",
    "src/socmint/dossier_export_pack_routes.py",
    "src/socmint/dossier_export_store_routes.py",
    "src/socmint/dossier_export_verification_routes.py",
    "src/socmint/dossier_finalization_certificate_bundle_routes_v7_5_5.py",
    "src/socmint/dossier_finalization_certificate_bundle_verify_routes_v7_5_6.py",
    "src/socmint/dossier_finalization_certificate_handoff_index_routes_v7_5_7.py",
    "src/socmint/dossier_finalization_certificate_routes_v7_5_4.py",
    "src/socmint/dossier_finalization_closeout_export_bundle_routes_v7_5_11.py",
    "src/socmint/dossier_finalization_closeout_export_verify_routes_v7_5_12.py",
    "src/socmint/dossier_finalization_closeout_report_routes_v7_5_10.py",
    "src/socmint/dossier_finalization_export_routes_v7_5_2.py",
    "src/socmint/dossier_finalization_export_verify_routes_v7_5_3.py",
    "src/socmint/dossier_finalization_handoff_export_bundle_routes_v7_5_8.py",
    "src/socmint/dossier_finalization_handoff_export_verify_routes_v7_5_9.py",
    "src/socmint/dossier_finalization_master_delivery_export_bundle_routes_v7_5_14.py",
    "src/socmint/dossier_finalization_master_delivery_index_routes_v7_5_13.py",
    "src/socmint/dossier_finalization_routes_v7_5_1.py"
  ],
  "framework": "flask"
}
```

### entrypoint_detection: PASS

```json
{
  "candidates": [
    {
      "notes": [
        "create_app",
        "Flask(",
        "register_blueprint"
      ],
      "path": "src/socmint/dashboard.py",
      "score": 10
    },
    {
      "notes": [
        "app.run"
      ],
      "path": "src/socmint/main.py",
      "score": 2
    },
    {
      "notes": [
        "Flask(",
        "app.run"
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/flask/app.py",
      "score": 5
    },
    {
      "notes": [
        "Flask(",
        "register_blueprint"
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/flask/sansio/app.py",
      "score": 5
    },
    {
      "notes": [
        "Flask(",
        "app.run"
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/maigret/web/app.py",
      "score": 5
    },
    {
      "notes": [
        "create_app"
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/prompt_toolkit/application/current.py",
      "score": 5
    },
    {
      "notes": [
        "Flask(",
        "app.run"
      ],
      "path": "var/venvs/v12_10_17/lib/python3.13/site-packages/flask/app.py",
      "score": 5
    },
    {
      "notes": [
        "Flask(",
        "register_blueprint"
      ],
      "path": "var/venvs/v12_10_17/lib/python3.13/site-packages/flask/sansio/app.py",
      "score": 5
    },
    {
      "notes": [
        "app.run"
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/prompt_toolkit/application/application.py",
      "score": 2
    },
    {
      "notes": [
        "Flask("
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/flask/sessions.py",
      "score": 3
    },
    {
      "notes": [
        "Flask("
      ],
      "path": "var/venvs/v12_10_17/lib/python3.13/site-packages/flask/sessions.py",
      "score": 3
    },
    {
      "notes": [
        "app.run"
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/flask/cli.py",
      "score": 2
    },
    {
      "notes": [
        "register_blueprint"
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/flask/sansio/blueprints.py",
      "score": 2
    },
    {
      "notes": [
        "app.run"
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/maigret/maigret.py",
      "score": 2
    },
    {
      "notes": [
        "app.run"
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/prompt_toolkit/shortcuts/progress_bar/base.py",
      "score": 2
    },
    {
      "notes": [
        "app.run"
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/prompt_toolkit/shortcuts/prompt.py",
      "score": 2
    },
    {
      "notes": [
        "app.run"
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/prompt_toolkit/shortcuts/utils.py",
      "score": 2
    },
    {
      "notes": [
        "app.run"
      ],
      "path": ".connector-tools/venv/lib/python3.13/site-packages/prompt_toolkit/widgets/toolbars.py",
      "score": 2
    },
    {
      "notes": [
        "app.run"
      ],
      "path": "var/venvs/v12_10_17/lib/python3.13/site-packages/flask/cli.py",
      "score": 2
    },
    {
      "notes": [
        "register_blueprint"
      ],
      "path": "var/venvs/v12_10_17/lib/python3.13/site-packages/flask/sansio/blueprints.py",
      "score": 2
    }
  ],
  "primary_guess": {
    "notes": [
      "create_app",
      "Flask(",
      "register_blueprint"
    ],
    "path": "src/socmint/dashboard.py",
    "score": 10
  }
}
```

### alembic_heads_and_chain: PASS

```json
{
  "duplicate_revisions": [],
  "heads": [
    "0017_v12_10_schema_reconciliation"
  ],
  "heads_command_ok": true,
  "history_command_ok": true,
  "history_excerpt": "sion ID: 0014_case_access\n    Revises: 0013_billing_customer_links\n    Create Date: 2026-05-12\n\nRev: 0013_billing_customer_links\nParent: 0012_tor_status\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0013_billing_customer_links.py\n\n    billing customer links\n    \n    Revision ID: 0013_billing_customer_links\n    Revises: 0012_tor_status\n    Create Date: 2026-05-12\n\nRev: 0012_tor_status\nParent: 0011_billing\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0012_tor_status.py\n\n    tor status table\n    \n    Revision ID: 0012_tor_status\n    Revises: 0011_billing\n    Create Date: 2026-05-12\n\nRev: 0011_billing\nParent: 0010_membership_quotas\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0011_billing.py\n\n    billing tables\n    \n    Revision ID: 0011_billing\n    Revises: 0010_membership_quotas\n    Create Date: 2026-05-12\n\nRev: 0010_membership_quotas\nParent: 0009_account_discovery_ingest\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0010_membership_quotas.py\n\n    membership and quota tables\n    \n    Revision ID: 0010_membership_quotas\n    Revises: 0009_account_discovery_ingest\n    Create Date: 2026-05-12\n\nRev: 0009_account_discovery_ingest\nParent: 0008_high_end_socmint_workflows\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0009_account_discovery_ingest.py\n\n    account discovery ingest table\n    \n    Revision ID: 0009_account_discovery_ingest\n    Revises: 0008_high_end_socmint_workflows\n    Create Date: 2026-05-11\n\nRev: 0008_high_end_socmint_workflows\nParent: 0007_v7_2_2_review_decision_audit\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0008_high_end_socmint_workflows.py\n\n    high-end SOCMINT workflow tables\n    \n    Revision ID: 0008_high_end_socmint_workflows\n    Revises: 0007_v7_2_2_review_decision_audit\n    Create Date: 2026-05-11\n\nRev: 0007_v7_2_2_review_decision_audit\nParent: 0006_v7_2_1_review_decisions\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0007_v7_2_2_review_decision_audit.py\n\n    v7.2.2 review decision audit trail and bulk actions\n    \n    Revision ID: 0007_v7_2_2_review_decision_audit\n    Revises: 0006_v7_2_1_review_decisions\n    Create Date: 2026-05-09\n\nRev: 0006_v7_2_1_review_decisions\nParent: 0005_v7_1_model_sync\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0006_v7_2_1_review_decisions.py\n\n    v7.2.1 review decision persistence\n    \n    Revision ID: 0006_v7_2_1_review_decisions\n    Revises: 0005_v7_1_model_sync\n    Create Date: 2026-05-09\n\nRev: 0005_v7_1_model_sync\nParent: 0004_roles_and_scan_jobs\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0005_v7_1_model_sync.py\n\n    v7.1 model sync\n    \n    Revision ID: 0005_v7_1_model_sync\n    Revises: 0004_roles_and_scan_jobs\n    Create Date: 2026-05-09\n\nRev: 0004_roles_and_scan_jobs\nParent: 0003_user_status_and_constraints\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0004_roles_and_scan_jobs.py\n\n    roles and scan jobs\n    \n    Revision ID: 0004_roles_and_scan_jobs\n    Revises: 0003_user_status_and_constraints\n    Create Date: 2026-05-07\n\nRev: 0003_user_status_and_constraints\nParent: 0002_audit_logs_and_indexes\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0003_user_status_and_constraints.py\n\n    user status and stricter constraints\n    \n    Revision ID: 0003_user_status_and_constraints\n    Revises: 0002_audit_logs_and_indexes\n    Create Date: 2026-05-07\n\nRev: 0002_audit_logs_and_indexes\nParent: 0001_initial_schema\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0002_audit_logs_and_indexes.py\n\n    audit logs and rate-limit indexes\n    \n    Revision ID: 0002_audit_logs_and_indexes\n    Revises: 0001_initial_schema\n    Create Date: 2026-05-06\n\nRev: 0001_initial_schema\nParent: <base>\nPath: /home/pmwens/Projects/SOCMINT-PROJECT/migrations/versions/0001_initial_schema.py\n\n    initial schema\n    \n    Revision ID: 0001_initial_schema\n    Revises:\n    Create Date: 2026-05-06\n\n",
  "migration_count": 15,
  "migration_files": [
    {
      "down_revision": null,
      "file": "migrations/versions/0001_initial_schema.py",
      "revision": "0001_initial_schema"
    },
    {
      "down_revision": "0001_initial_schema",
      "file": "migrations/versions/0002_audit_logs_and_indexes.py",
      "revision": "0002_audit_logs_and_indexes"
    },
    {
      "down_revision": "0002_audit_logs_and_indexes",
      "file": "migrations/versions/0003_user_status_and_constraints.py",
      "revision": "0003_user_status_and_constraints"
    },
    {
      "down_revision": "0003_user_status_and_constraints",
      "file": "migrations/versions/0004_roles_and_scan_jobs.py",
      "revision": "0004_roles_and_scan_jobs"
    },
    {
      "down_revision": "0004_roles_and_scan_jobs",
      "file": "migrations/versions/0005_v7_1_model_sync.py",
      "revision": "0005_v7_1_model_sync"
    },
    {
      "down_revision": "0005_v7_1_model_sync",
      "file": "migrations/versions/0006_v7_2_1_review_decisions.py",
      "revision": "0006_v7_2_1_review_decisions"
    },
    {
      "down_revision": "0006_v7_2_1_review_decisions",
      "file": "migrations/versions/0007_v7_2_2_review_decision_audit.py",
      "revision": "0007_v7_2_2_review_decision_audit"
    },
    {
      "down_revision": "0007_v7_2_2_review_decision_audit",
      "file": "migrations/versions/0008_high_end_socmint_workflows.py",
      "revision": "0008_high_end_socmint_workflows"
    },
    {
      "down_revision": "0008_high_end_socmint_workflows",
      "file": "migrations/versions/0009_account_discovery_ingest.py",
      "revision": "0009_account_discovery_ingest"
    },
    {
      "down_revision": "0009_account_discovery_ingest",
      "file": "migrations/versions/0010_membership_quotas.py",
      "revision": "0010_membership_quotas"
    },
    {
      "down_revision": "0010_membership_quotas",
      "file": "migrations/versions/0011_billing.py",
      "revision": "0011_billing"
    },
    {
      "down_revision": "0011_billing",
      "file": "migrations/versions/0012_tor_status.py",
      "revision": "0012_tor_status"
    },
    {
      "down_revision": "0012_tor_status",
      "file": "migrations/versions/0013_billing_customer_links.py",
      "revision": "0013_billing_customer_links"
    },
    {
      "down_revision": "0013_billing_customer_links",
      "file": "migrations/versions/0014_case_access.py",
      "revision": "0014_case_access"
    },
    {
      "down_revision": "0014_case_access",
      "file": "migrations/versions/0017_v12_10_schema_reconciliation.py",
      "revision": "0017_v12_10_schema_reconciliation"
    }
  ],
  "orphan_down_revisions": [],
  "raw_heads": "0017_v12_10_schema_reconciliation (head)\n",
  "script_location": "migrations",
  "sole_expected_head": true,
  "versions_dir": "migrations/versions"
}
```

### models_vs_migrations: WARN

```json
{
  "migrations": {
    "migration_files": [
      {
        "file": "migrations/versions/0001_initial_schema.py",
        "tables": [
          "media",
          "profiles",
          "rate_limit_attempts",
          "results",
          "targets",
          "tools",
          "users"
        ]
      },
      {
        "file": "migrations/versions/0002_audit_logs_and_indexes.py",
        "tables": [
          "audit_logs"
        ]
      },
      {
        "file": "migrations/versions/0004_roles_and_scan_jobs.py",
        "tables": [
          "scan_jobs"
        ]
      },
      {
        "file": "migrations/versions/0006_v7_2_1_review_decisions.py",
        "tables": [
          "review_decisions"
        ]
      },
      {
        "file": "migrations/versions/0007_v7_2_2_review_decision_audit.py",
        "tables": [
          "review_decision_audit"
        ]
      },
      {
        "file": "migrations/versions/0008_high_end_socmint_workflows.py",
        "tables": [
          "case_events",
          "case_records",
          "evidence_captures",
          "responsible_use_scope"
        ]
      },
      {
        "file": "migrations/versions/0009_account_discovery_ingest.py",
        "tables": [
          "account_discoveries"
        ]
      },
      {
        "file": "migrations/versions/0010_membership_quotas.py",
        "tables": [
          "membership_plans",
          "quota_overrides",
          "usage_counters",
          "usage_events",
          "user_memberships"
        ]
      },
      {
        "file": "migrations/versions/0011_billing.py",
        "tables": [
          "billing_events",
          "checkout_sessions"
        ]
      },
      {
        "file": "migrations/versions/0012_tor_status.py",
        "tables": [
          "hidden_service_status"
        ]
      },
      {
        "file": "migrations/versions/0013_billing_customer_links.py",
        "tables": [
          "billing_customer_links"
        ]
      },
      {
        "file": "migrations/versions/0014_case_access.py",
        "tables": [
          "case_assignments",
          "team_memberships"
        ]
      },
      {
        "file": "migrations/versions/0017_v12_10_schema_reconciliation.py",
        "tables": [
          "analyst_decisions",
          "continuous_monitoring_events",
          "dossier_exports",
          "evidence_hash_events",
          "intel_runs",
          "strategic_risk_scores"
        ]
      }
    ],
    "table_count": 33,
    "tables": [
      "account_discoveries",
      "analyst_decisions",
      "audit_logs",
      "billing_customer_links",
      "billing_events",
      "case_assignments",
      "case_events",
      "case_records",
      "checkout_sessions",
      "continuous_monitoring_events",
      "dossier_exports",
      "evidence_captures",
      "evidence_hash_events",
      "hidden_service_status",
      "intel_runs",
      "media",
      "membership_plans",
      "profiles",
      "quota_overrides",
      "rate_limit_attempts",
      "responsible_use_scope",
      "results",
      "review_decision_audit",
      "review_decisions",
      "scan_jobs",
      "strategic_risk_scores",
      "targets",
      "team_memberships",
      "tools",
      "usage_counters",
      "usage_events",
      "user_memberships",
      "users"
    ]
  },
  "models": {
    "model_files": [
      {
        "file": ".connector-tools/venv/lib/python3.13/site-packages/pip/_vendor/rich/default_styles.py",
        "tables": [
          "Name"
        ]
      },
      {
        "file": ".connector-tools/venv/lib/python3.13/site-packages/pip/_vendor/rich/live.py",
        "tables": [
          "foo"
        ]
      },
      {
        "file": ".connector-tools/venv/lib/python3.13/site-packages/pip/_vendor/rich/markup.py",
        "tables": [
          "Markup"
        ]
      },
      {
        "file": ".connector-tools/venv/lib/python3.13/site-packages/pip/_vendor/rich/palette.py",
        "tables": [
          "index"
        ]
      },
      {
        "file": ".connector-tools/venv/lib/python3.13/site-packages/pip/_vendor/rich/progress.py",
        "tables": [
          "foo"
        ]
      },
      {
        "file": ".connector-tools/venv/lib/python3.13/site-packages/rich/default_styles.py",
        "tables": [
          "Name"
        ]
      },
      {
        "file": ".connector-tools/venv/lib/python3.13/site-packages/rich/live.py",
        "tables": [
          "foo"
        ]
      },
      {
        "file": ".connector-tools/venv/lib/python3.13/site-packages/rich/markup.py",
        "tables": [
          "Markup"
        ]
      },
      {
        "file": ".connector-tools/venv/lib/python3.13/site-packages/rich/palette.py",
        "tables": [
          "index"
        ]
      },
      {
        "file": ".connector-tools/venv/lib/python3.13/site-packages/rich/progress.py",
        "tables": [
          "foo"
        ]
      },
      {
        "file": "src/socmint/database.py",
        "tables": [
          "account_discoveries",
          "audit_logs",
          "case_events",
          "case_records",
          "connector_runs",
          "dossier_exports",
          "evidence_captures",
          "findings",
          "identity_edges",
          "identity_graphs",
          "identity_merge_candidates",
          "identity_nodes",
          "media",
          "media_profile_enrichments",
          "policy_gate_events",
          "profiles",
          "rate_limit_attempts",
          "responsible_use_scope",
          "results",
          "retention_runs",
          "review_decision_audit",
          "review_decisions",
          "scan_jobs",
          "spine_connector_runs",
          "spine_contradictions",
          "spine_dossier_assertions",
          "spine_observations",
          "spine_raw_artifacts",
          "spine_seeds",
          "spine_subjects",
          "spine_validation_events",
          "targets",
          "tools",
          "users",
          "workbench_jobs"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/autogenerate/api.py",
        "tables": [
          "bar",
          "bat",
          "foo"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/fixtures.py",
        "tables": [
          "x"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py",
        "tables": [
          "address",
          "extra",
          "item",
          "order",
          "unnamed_sqlite",
          "user",
          "x1",
          "x2",
          "x3",
          "x4",
          "x5",
          "x6"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_comments.py",
        "tables": [
          "some_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_computed.py",
        "tables": [
          "user"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_diffs.py",
        "tables": [
          "a"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_fks.py",
        "tables": [
          "ref",
          "ref_a",
          "ref_b",
          "some_table",
          "t",
          "user"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_identity.py",
        "tables": [
          "user"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/pip/_vendor/rich/default_styles.py",
        "tables": [
          "Name"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/pip/_vendor/rich/live.py",
        "tables": [
          "foo"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/pip/_vendor/rich/markup.py",
        "tables": [
          "Markup"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/pip/_vendor/rich/palette.py",
        "tables": [
          "index"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/pip/_vendor/rich/progress.py",
        "tables": [
          "foo"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/base.py",
        "tables": [
          "account",
          "my_table",
          "mytable",
          "some_table",
          "t",
          "test"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py",
        "tables": [
          "COLUMNS",
          "CONSTRAINT_COLUMN_USAGE",
          "KEY_COLUMN_USAGE",
          "REFERENTIAL_CONSTRAINTS",
          "SCHEMATA",
          "SEQUENCES",
          "TABLES",
          "TABLE_CONSTRAINTS",
          "VIEWS",
          "columns",
          "computed_columns",
          "default_constraints",
          "extended_properties",
          "identity_columns",
          "types"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mysql/base.py",
        "tables": [
          "mytable",
          "testtable",
          "ts_test"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/base.py",
        "tables": [
          "MYTABLE",
          "MyTable",
          "my_table",
          "mytable",
          "some_table",
          "t",
          "t1"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py",
        "tables": [
          "all_col_comments",
          "all_cons_columns",
          "all_constraints",
          "all_db_links",
          "all_ind_columns",
          "all_ind_expressions",
          "all_indexes",
          "all_mview_comments",
          "all_mviews",
          "all_objects",
          "all_sequences",
          "all_synonyms",
          "all_tab_cols",
          "all_tab_comments",
          "all_tab_identity_cols",
          "all_tables",
          "all_users",
          "all_views"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/array.py",
        "tables": [
          "mytable"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/base.py",
        "tables": [
          "data",
          "fktable",
          "foo",
          "mytable",
          "referring",
          "some_table",
          "sometable",
          "t",
          "testtbl"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/ext.py",
        "tables": [
          "some_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/hstore.py",
        "tables": [
          "data_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/json.py",
        "tables": [
          "data_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/named_types.py",
        "tables": [
          "sometable",
          "sometable_one",
          "sometable_two"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py",
        "tables": [
          "pg_am",
          "pg_attrdef",
          "pg_attribute",
          "pg_class",
          "pg_collation",
          "pg_constraint",
          "pg_description",
          "pg_enum",
          "pg_index",
          "pg_namespace",
          "pg_opclass",
          "pg_sequence",
          "pg_type"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/sqlite/base.py",
        "tables": [
          "my_table",
          "some_table",
          "sometable",
          "testtbl"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/engine/reflection.py",
        "tables": [
          "user"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/asyncio/session.py",
        "tables": [
          "a",
          "b"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/automap.py",
        "tables": [
          "address",
          "employee",
          "engineer",
          "table_b",
          "user",
          "user_order"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/compiler.py",
        "tables": [
          "event",
          "foo"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/declarative/extensions.py",
        "tables": [
          "company",
          "employee",
          "manager",
          "myothertable",
          "mytable",
          "yetanothertable"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/hybrid.py",
        "tables": [
          "account",
          "interval",
          "searchword",
          "user"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/indexable.py",
        "tables": [
          "person"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/mutable.py",
        "tables": [
          "my_data",
          "mytable",
          "vertices"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/orderinglist.py",
        "tables": [
          "bullet",
          "slide"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/_orm_constructors.py",
        "tables": [
          "my_table",
          "unit_price"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/base.py",
        "tables": [
          "user"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/decl_api.py",
        "tables": [
          "employee",
          "my_table",
          "relationships",
          "some_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/mapper.py",
        "tables": [
          "employee"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/query.py",
        "tables": [
          "part"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/base.py",
        "tables": [
          "sometable"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/ddl.py",
        "tables": [
          "mytable",
          "users"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/dml.py",
        "tables": [
          "user_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/elements.py",
        "tables": [
          "t"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/events.py",
        "tables": [
          "my_table",
          "some_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/functions.py",
        "tables": [
          "venue"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/schema.py",
        "tables": [
          "foo",
          "mytable",
          "remote_table",
          "some_table",
          "sometable",
          "square",
          "user"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/selectable.py",
        "tables": [
          "edge",
          "orders",
          "parts",
          "visitors"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/sqltypes.py",
        "tables": [
          "data",
          "data_table",
          "my_table",
          "mytable",
          "t"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/type_api.py",
        "tables": [
          "foo",
          "some_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/util.py",
        "tables": [
          "someothertable",
          "sometable"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/config.py",
        "tables": [
          "thing"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/fixtures/base.py",
        "tables": [
          "test"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/fixtures/sql.py",
        "tables": [
          "computed_column_table",
          "computed_default_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_cte.py",
        "tables": [
          "some_other_table",
          "some_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_ddl.py",
        "tables": [
          "_test_table",
          "a_things_with_stuff",
          "b_related_things_of_value",
          "test_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_deprecations.py",
        "tables": [
          "some_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_dialect.py",
        "tables": [
          "manual_pk",
          "mytable",
          "some_table",
          "t"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_insert.py",
        "tables": [
          "autoinc_pk",
          "d_t",
          "includes_defaults",
          "manual_pk",
          "no_implicit_returning"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py",
        "tables": [
          "comment_test",
          "dingalings",
          "email_addresses",
          "empty",
          "empty_v",
          "local_table",
          "new_table",
          "no_constraints",
          "noncol_idx_test_nopk",
          "noncol_idx_test_pk",
          "other",
          "quote ",
          "related",
          "remote_table",
          "remote_table_2",
          "sa_cc",
          "sa_multi_index",
          "some_table",
          "t",
          "t1",
          "t2",
          "table",
          "tb1",
          "tb2",
          "test_table",
          "test_table_2",
          "test_table_s",
          "testtbl",
          "unicode_comments",
          "user",
          "user_orders",
          "users",
          "users_ref",
          "x"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_results.py",
        "tables": [
          "has_dates",
          "percent%table",
          "plain_pk",
          "test_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_rowcount.py",
        "tables": [
          "employees"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_select.py",
        "tables": [
          "a",
          "b",
          "bitwise",
          "is_distinct_test",
          "some_table",
          "square",
          "stuff",
          "tbl",
          "tbl_a",
          "tbl_b"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_sequence.py",
        "tables": [
          "seq_no_returning",
          "seq_no_returning_sch",
          "seq_opt_pk",
          "seq_pk",
          "user_id_table",
          "x"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_types.py",
        "tables": [
          "array_table",
          "binary_table",
          "boolean_table",
          "data_table",
          "date_table",
          "enum_table",
          "foo",
          "integer_table",
          "interval_table",
          "t",
          "text_table",
          "unicode_table",
          "uuid_table"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_unicode_ddl.py",
        "tables": [
          "Unit\u00e9ble2",
          "\\u6e2c\\u8a66",
          "unitable1",
          "\u6e2c\u8a66"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_update_delete.py",
        "tables": [
          "plain_pk"
        ]
      },
      {
        "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/util/_collections.py",
        "tables": [
          "users"
        ]
      }
    ],
    "table_count": 219,
    "tables": [
      "COLUMNS",
      "CONSTRAINT_COLUMN_USAGE",
      "KEY_COLUMN_USAGE",
      "MYTABLE",
      "Markup",
      "MyTable",
      "Name",
      "REFERENTIAL_CONSTRAINTS",
      "SCHEMATA",
      "SEQUENCES",
      "TABLES",
      "TABLE_CONSTRAINTS",
      "Unit\u00e9ble2",
      "VIEWS",
      "\\u6e2c\\u8a66",
      "_test_table",
      "a",
      "a_things_with_stuff",
      "account",
      "account_discoveries",
      "address",
      "all_col_comments",
      "all_cons_columns",
      "all_constraints",
      "all_db_links",
      "all_ind_columns",
      "all_ind_expressions",
      "all_indexes",
      "all_mview_comments",
      "all_mviews",
      "all_objects",
      "all_sequences",
      "all_synonyms",
      "all_tab_cols",
      "all_tab_comments",
      "all_tab_identity_cols",
      "all_tables",
      "all_users",
      "all_views",
      "array_table",
      "audit_logs",
      "autoinc_pk",
      "b",
      "b_related_things_of_value",
      "bar",
      "bat",
      "binary_table",
      "bitwise",
      "boolean_table",
      "bullet",
      "case_events",
      "case_records",
      "columns",
      "comment_test",
      "company",
      "computed_column_table",
      "computed_columns",
      "computed_default_table",
      "connector_runs",
      "d_t",
      "data",
      "data_table",
      "date_table",
      "default_constraints",
      "dingalings",
      "dossier_exports",
      "edge",
      "email_addresses",
      "employee",
      "employees",
      "empty",
      "empty_v",
      "engineer",
      "enum_table",
      "event",
      "evidence_captures",
      "extended_properties",
      "extra",
      "findings",
      "fktable",
      "foo",
      "has_dates",
      "identity_columns",
      "identity_edges",
      "identity_graphs",
      "identity_merge_candidates",
      "identity_nodes",
      "includes_defaults",
      "index",
      "integer_table",
      "interval",
      "interval_table",
      "is_distinct_test",
      "item",
      "local_table",
      "manager",
      "manual_pk",
      "media",
      "media_profile_enrichments",
      "my_data",
      "my_table",
      "myothertable",
      "mytable",
      "new_table",
      "no_constraints",
      "no_implicit_returning",
      "noncol_idx_test_nopk",
      "noncol_idx_test_pk",
      "order",
      "orders",
      "other",
      "part",
      "parts",
      "percent%table",
      "person",
      "pg_am",
      "pg_attrdef",
      "pg_attribute",
      "pg_class",
      "pg_collation",
      "pg_constraint",
      "pg_description",
      "pg_enum",
      "pg_index",
      "pg_namespace",
      "pg_opclass",
      "pg_sequence",
      "pg_type",
      "plain_pk",
      "policy_gate_events",
      "profiles",
      "quote ",
      "rate_limit_attempts",
      "ref",
      "ref_a",
      "ref_b",
      "referring",
      "related",
      "relationships",
      "remote_table",
      "remote_table_2",
      "responsible_use_scope",
      "results",
      "retention_runs",
      "review_decision_audit",
      "review_decisions",
      "sa_cc",
      "sa_multi_index",
      "scan_jobs",
      "searchword",
      "seq_no_returning",
      "seq_no_returning_sch",
      "seq_opt_pk",
      "seq_pk",
      "slide",
      "some_other_table",
      "some_table",
      "someothertable",
      "sometable",
      "sometable_one",
      "sometable_two",
      "spine_connector_runs",
      "spine_contradictions",
      "spine_dossier_assertions",
      "spine_observations",
      "spine_raw_artifacts",
      "spine_seeds",
      "spine_subjects",
      "spine_validation_events",
      "square",
      "stuff",
      "t",
      "t1",
      "t2",
      "table",
      "table_b",
      "targets",
      "tb1",
      "tb2",
      "tbl",
      "tbl_a",
      "tbl_b",
      "test",
      "test_table",
      "test_table_2",
      "test_table_s",
      "testtable",
      "testtbl",
      "text_table",
      "thing",
      "tools",
      "ts_test",
      "types",
      "unicode_comments",
      "unicode_table",
      "unit_price",
      "unitable1",
      "unnamed_sqlite",
      "user",
      "user_id_table",
      "user_order",
      "user_orders",
      "user_table",
      "users",
      "users_ref",
      "uuid_table",
      "venue",
      "vertices",
      "visitors",
      "workbench_jobs",
      "x",
      "x1",
      "x2",
      "x3",
      "x4",
      "x5",
      "x6",
      "yetanothertable",
      "\u6e2c\u8a66"
    ]
  },
  "models_covered_by_migrations": false,
  "tables_in_migrations_not_models": [
    "analyst_decisions",
    "billing_customer_links",
    "billing_events",
    "case_assignments",
    "checkout_sessions",
    "continuous_monitoring_events",
    "evidence_hash_events",
    "hidden_service_status",
    "intel_runs",
    "membership_plans",
    "quota_overrides",
    "strategic_risk_scores",
    "team_memberships",
    "usage_counters",
    "usage_events",
    "user_memberships"
  ],
  "tables_in_models_not_migrations": [
    "COLUMNS",
    "CONSTRAINT_COLUMN_USAGE",
    "KEY_COLUMN_USAGE",
    "MYTABLE",
    "Markup",
    "MyTable",
    "Name",
    "REFERENTIAL_CONSTRAINTS",
    "SCHEMATA",
    "SEQUENCES",
    "TABLES",
    "TABLE_CONSTRAINTS",
    "Unit\u00e9ble2",
    "VIEWS",
    "\\u6e2c\\u8a66",
    "_test_table",
    "a",
    "a_things_with_stuff",
    "account",
    "address",
    "all_col_comments",
    "all_cons_columns",
    "all_constraints",
    "all_db_links",
    "all_ind_columns",
    "all_ind_expressions",
    "all_indexes",
    "all_mview_comments",
    "all_mviews",
    "all_objects",
    "all_sequences",
    "all_synonyms",
    "all_tab_cols",
    "all_tab_comments",
    "all_tab_identity_cols",
    "all_tables",
    "all_users",
    "all_views",
    "array_table",
    "autoinc_pk",
    "b",
    "b_related_things_of_value",
    "bar",
    "bat",
    "binary_table",
    "bitwise",
    "boolean_table",
    "bullet",
    "columns",
    "comment_test",
    "company",
    "computed_column_table",
    "computed_columns",
    "computed_default_table",
    "connector_runs",
    "d_t",
    "data",
    "data_table",
    "date_table",
    "default_constraints",
    "dingalings",
    "edge",
    "email_addresses",
    "employee",
    "employees",
    "empty",
    "empty_v",
    "engineer",
    "enum_table",
    "event",
    "extended_properties",
    "extra",
    "findings",
    "fktable",
    "foo",
    "has_dates",
    "identity_columns",
    "identity_edges",
    "identity_graphs",
    "identity_merge_candidates",
    "identity_nodes",
    "includes_defaults",
    "index",
    "integer_table",
    "interval",
    "interval_table",
    "is_distinct_test",
    "item",
    "local_table",
    "manager",
    "manual_pk",
    "media_profile_enrichments",
    "my_data",
    "my_table",
    "myothertable",
    "mytable",
    "new_table",
    "no_constraints",
    "no_implicit_returning",
    "noncol_idx_test_nopk",
    "noncol_idx_test_pk",
    "order",
    "orders",
    "other",
    "part",
    "parts",
    "percent%table",
    "person",
    "pg_am",
    "pg_attrdef",
    "pg_attribute",
    "pg_class",
    "pg_collation",
    "pg_constraint",
    "pg_description",
    "pg_enum",
    "pg_index",
    "pg_namespace",
    "pg_opclass",
    "pg_sequence",
    "pg_type",
    "plain_pk",
    "policy_gate_events",
    "quote ",
    "ref",
    "ref_a",
    "ref_b",
    "referring",
    "related",
    "relationships",
    "remote_table",
    "remote_table_2",
    "retention_runs",
    "sa_cc",
    "sa_multi_index",
    "searchword",
    "seq_no_returning",
    "seq_no_returning_sch",
    "seq_opt_pk",
    "seq_pk",
    "slide",
    "some_other_table",
    "some_table",
    "someothertable",
    "sometable",
    "sometable_one",
    "sometable_two",
    "spine_connector_runs",
    "spine_contradictions",
    "spine_dossier_assertions",
    "spine_observations",
    "spine_raw_artifacts",
    "spine_seeds",
    "spine_subjects",
    "spine_validation_events",
    "square",
    "stuff",
    "t",
    "t1",
    "t2",
    "table",
    "table_b",
    "tb1",
    "tb2",
    "tbl",
    "tbl_a",
    "tbl_b",
    "test",
    "test_table",
    "test_table_2",
    "test_table_s",
    "testtable",
    "testtbl",
    "text_table",
    "thing",
    "ts_test",
    "types",
    "unicode_comments",
    "unicode_table",
    "unit_price",
    "unitable1",
    "unnamed_sqlite",
    "user",
    "user_id_table",
    "user_order",
    "user_orders",
    "user_table",
    "users_ref",
    "uuid_table",
    "venue",
    "vertices",
    "visitors",
    "workbench_jobs",
    "x",
    "x1",
    "x2",
    "x3",
    "x4",
    "x5",
    "x6",
    "yetanothertable",
    "\u6e2c\u8a66"
  ]
}
```

### static_route_scan: PASS

```json
{
  "route_count": 448,
  "route_files": [
    {
      "file": ".connector-tools/venv/lib/python3.13/site-packages/flask/ctx.py",
      "routes": [
        "/"
      ]
    },
    {
      "file": ".connector-tools/venv/lib/python3.13/site-packages/flask/helpers.py",
      "routes": [
        "/stream",
        "/uploads/<path:name>"
      ]
    },
    {
      "file": ".connector-tools/venv/lib/python3.13/site-packages/flask/sansio/scaffold.py",
      "routes": [
        "/"
      ]
    },
    {
      "file": ".connector-tools/venv/lib/python3.13/site-packages/maigret/web/app.py",
      "routes": [
        "/",
        "/reports/<path:filename>",
        "/results/<session_id>",
        "/search",
        "/status/<timestamp>"
      ]
    },
    {
      "file": "src/socmint/analyst_ux_routes.py",
      "routes": [
        "/analyst/launchpad",
        "/api/v1/analyst/launchpad",
        "/api/v1/analyst/launchpad/compact"
      ]
    },
    {
      "file": "src/socmint/beta_readiness_routes.py",
      "routes": [
        "/api/v1/admin/beta/readiness",
        "/api/v1/admin/beta/readiness/summary",
        "/api/v1/beta/onboarding"
      ]
    },
    {
      "file": "src/socmint/billing_integration_routes.py",
      "routes": [
        "/api/v1/admin/billing/customer-links/<username>",
        "/api/v1/admin/billing/provider-config",
        "/api/v1/admin/billing/provider-events"
      ]
    },
    {
      "file": "src/socmint/billing_routes.py",
      "routes": [
        "/api/v1/account/billing",
        "/api/v1/account/billing/checkout",
        "/api/v1/admin/billing/events",
        "/api/v1/billing/webhook"
      ]
    },
    {
      "file": "src/socmint/case_access_routes.py",
      "routes": [
        "/api/v1/account/case-access",
        "/api/v1/admin/case-access/<int:case_id>",
        "/api/v1/admin/teams/<team_key>/members",
        "/api/v1/cases/<int:case_id>/access/check"
      ]
    },
    {
      "file": "src/socmint/certification_dashboard_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/certification-dashboard/<case_id>",
        "/dossier/certification-dashboard"
      ]
    },
    {
      "file": "src/socmint/certification_routes.py",
      "routes": [
        "/api/v1/admin/certification/report",
        "/api/v1/admin/certification/summary"
      ]
    },
    {
      "file": "src/socmint/connector_sdk_routes.py",
      "routes": [
        "/api/v1/connectors/sdk/catalog",
        "/api/v1/connectors/sdk/fixture-run",
        "/api/v1/connectors/sdk/marketplace",
        "/api/v1/connectors/sdk/validate"
      ]
    },
    {
      "file": "src/socmint/dashboard.py",
      "routes": [
        "/",
        "/about",
        "/account/password",
        "/admin/audit",
        "/admin/users",
        "/admin/users/<int:user_id>",
        "/analyst/console",
        "/api/v1/analyst/workbench",
        "/api/v1/cases",
        "/api/v1/cases/<case_key>",
        "/api/v1/connectors/marketplace",
        "/api/v1/dossier/<subject_id>/quality-gate",
        "/api/v1/dossier/<subject_id>/traceability",
        "/api/v1/evidence/attachment-map",
        "/api/v1/evidence/capture",
        "/api/v1/evidence/captures",
        "/api/v1/evidence/captures/<capture_id>/verify",
        "/api/v1/evidence/custody",
        "/api/v1/evidence/custody/report",
        "/api/v1/evidence/intake",
        "/api/v1/evidence/integrity",
        "/api/v1/evidence/integrity/pack",
        "/api/v1/evidence/links",
        "/api/v1/evidence/links/delete",
        "/api/v1/evidence/verify",
        "/api/v1/exports/builder",
        "/api/v1/exports/builder/bundle",
        "/api/v1/exports/builder/bundles/<path:name>/verify",
        "/api/v1/jobs/<int:job_id>/cancel",
        "/api/v1/jobs/<int:job_id>/requeue",
        "/api/v1/jobs/health",
        "/api/v1/product/actions/export-control-snapshot",
        "/api/v1/product/actions/write-reports",
        "/api/v1/product/artifact-export-manifest",
        "/api/v1/product/artifact-export-manifest/write",
        "/api/v1/product/artifact-review-audit",
        "/api/v1/product/artifact-review-state",
        "/api/v1/product/artifacts",
        "/api/v1/product/artifacts/review",
        "/api/v1/product/build-status",
        "/api/v1/product/final",
        "/api/v1/product/final-gate",
        "/api/v1/product/final-gate/signoff",
        "/api/v1/product/final-gate/signoff-audit",
        "/api/v1/product/final-gate/write",
        "/api/v1/product/final-release",
        "/api/v1/product/final-release/archive/<release_name>",
        "/api/v1/product/final-release/archive/<release_name>/create",
        "/api/v1/product/final-release/archives",
        "/api/v1/product/final-release/distribution",
        "/api/v1/product/final-release/distribution/audit",
        "/api/v1/product/final-release/distribution/decision",
        "/api/v1/product/final-release/distribution/write",
        "/api/v1/product/final-release/publish",
        "/api/v1/product/final-release/verify",
        "/api/v1/product/final/handoff",
        "/api/v1/product/final/handoff/build",
        "/api/v1/product/final/self-test",
        "/api/v1/product/final/self-test/maintenance",
        "/api/v1/product/final/self-test/maintenance-audit",
        "/api/v1/product/final/self-test/write",
        "/api/v1/product/final/v10-bootstrap",
        "/api/v1/product/final/v10-bootstrap/audit",
        "/api/v1/product/final/v10-bootstrap/decision",
        "/api/v1/product/final/v10-bootstrap/write",
        "/api/v1/product/final/write",
        "/api/v1/product/operator-runbook",
        "/api/v1/product/release-candidate",
        "/api/v1/product/release-candidate/write",
        "/api/v1/product/release-package",
        "/api/v1/product/release-package/<package_name>/zip",
        "/api/v1/product/release-package/build",
        "/api/v1/product/release-packages",
        "/api/v1/product/release-readiness",
        "/api/v1/product/runtime-actions",
        "/api/v1/product/smoke-summary",
        "/api/v1/product/system-health",
        "/api/v1/product/write-reports",
        "/api/v1/reports/export-center",
        "/api/v1/reports/export-center/artifacts/<path:name>",
        "/api/v1/reports/export-center/attachments",
        "/api/v1/reports/export-center/attachments/zip",
        "/api/v1/reports/export-center/review-gated",
        "/api/v1/reports/export-center/zip",
        "/api/v1/reports/review/audit",
        "/api/v1/reports/review/bulk",
        "/api/v1/reports/review/items",
        "/api/v1/reports/review/items/<path:item_id>",
        "/api/v1/reports/review/summary",
        "/api/v1/reports/runs",
        "/api/v1/responsible-use/gate",
        "/api/v1/responsible-use/review",
        "/api/v1/responsible-use/scope",
        "/api/v1/spine/<int:subject_id>/graph/canvas",
        "/api/v1/spine/<int:subject_id>/resolution-lab",
        "/api/v1/spine/account-discovery/<int:discovery_id>/review",
        "/api/v1/spine/assertions/<int:assertion_id>",
        "/api/v1/spine/assertions/review-queue",
        "/api/v1/spine/connectors/quality",
        "/api/v1/spine/enrichment-review",
        "/api/v1/spine/enrichments/<int:enrichment_id>/findings/",
        "/api/v1/spine/subjects",
        "/api/v1/spine/subjects/<int:subject_id>/account-discovery",
        "/api/v1/spine/subjects/<int:subject_id>/account-discovery/ingest",
        "/api/v1/spine/subjects/<int:subject_id>/contradictions",
        "/api/v1/spine/subjects/<int:subject_id>/contradictions/run",
        "/api/v1/spine/subjects/<int:subject_id>/dossier",
        "/api/v1/spine/subjects/<int:subject_id>/dossier-v2",
        "/api/v1/spine/subjects/<int:subject_id>/dossier-v2/export",
        "/api/v1/spine/subjects/<int:subject_id>/exports",
        "/api/v1/spine/subjects/<int:subject_id>/exports/run",
        "/api/v1/spine/subjects/<int:subject_id>/graph",
        "/api/v1/spine/subjects/<int:subject_id>/media-profiles",
        "/api/v1/spine/subjects/<int:subject_id>/media-profiles/run",
        "/api/v1/spine/subjects/<int:subject_id>/run",
        "/api/v1/workbench/jobs",
        "/api/v1/workbench/jobs/<int:job_id>/run",
        "/api/v1/workbench/jobs/run-next",
        "/api/v1/workbench/policy/evaluate",
        "/api/v1/workbench/policy/events",
        "/api/v1/workbench/retention/run",
        "/api/v1/workbench/status",
        "/cases",
        "/cases/<case_key>",
        "/connectors/marketplace",
        "/evidence/capture",
        "/evidence/custody",
        "/evidence/intake",
        "/evidence/intake/add",
        "/evidence/intake/files/<path:name>/download",
        "/evidence/integrity",
        "/evidence/integrity/pack/run",
        "/evidence/integrity/packs/<path:name>/download",
        "/evidence/links",
        "/evidence/links/add",
        "/evidence/verify/run",
        "/exports/builder",
        "/healthz",
        "/jobs",
        "/login",
        "/logout",
        "/media/<int:media_id>/<path:filename>",
        "/product/actions/export-control-snapshot",
        "/product/actions/refresh-readiness",
        "/product/actions/write-reports",
        "/product/artifacts",
        "/product/artifacts/audit/<path:relpath>",
        "/product/artifacts/download/<path:relpath>",
        "/product/artifacts/export-manifest",
        "/product/artifacts/export-manifest/write",
        "/product/artifacts/review",
        "/product/artifacts/view/<path:relpath>",
        "/product/build-control",
        "/product/final",
        "/product/final-gate",
        "/product/final-gate/signoff",
        "/product/final-gate/write",
        "/product/final-release",
        "/product/final-release/archive",
        "/product/final-release/archive/<release_name>/create",
        "/product/final-release/archive/download/<path:filename>",
        "/product/final-release/distribution",
        "/product/final-release/distribution/decision",
        "/product/final-release/distribution/write",
        "/product/final-release/publish",
        "/product/final-release/verify",
        "/product/final/handoff",
        "/product/final/handoff/build",
        "/product/final/self-test",
        "/product/final/self-test/maintenance",
        "/product/final/self-test/write",
        "/product/final/v10-bootstrap",
        "/product/final/v10-bootstrap/decision",
        "/product/final/v10-bootstrap/write",
        "/product/final/write",
        "/product/operator-runbook",
        "/product/release-candidate",
        "/product/release-candidate/write",
        "/product/release-package",
        "/product/release-package/build",
        "/product/release-package/download/<package_name>",
        "/product/release-package/zip/<package_name>",
        "/readyz",
        "/reports/export-center",
        "/reports/export-center/artifacts/<path:name>/download",
        "/reports/export-center/bundles/<path:name>/download",
        "/reports/export-center/manifests/<path:name>",
        "/reports/export-center/review-gated/run",
        "/reports/export-center/zip/run",
        "/reports/review",
        "/reports/review/items/<path:item_id>/<status>",
        "/responsible-use",
        "/signup",
        "/spine",
        "/spine/<int:subject_id>",
        "/spine/<int:subject_id>/contradictions",
        "/spine/<int:subject_id>/contradictions/run",
        "/spine/<int:subject_id>/exports",
        "/spine/<int:subject_id>/exports/run",
        "/spine/<int:subject_id>/graph",
        "/spine/<int:subject_id>/graph/build",
        "/spine/<int:subject_id>/graph/canvas",
        "/spine/<int:subject_id>/media-profiles",
        "/spine/<int:subject_id>/media-profiles/run",
        "/spine/<int:subject_id>/resolution-lab",
        "/spine/<int:subject_id>/run",
        "/spine/account-discovery/<int:discovery_id>/review",
        "/spine/assertions/<int:assertion_id>",
        "/spine/assertions/<int:assertion_id>/validate",
        "/spine/connectors/quality",
        "/spine/contradictions/<int:contradiction_id>/resolve",
        "/spine/enrichment-review",
        "/spine/enrichments/<int:enrichment_id>/findings/<int:finding_index>/review",
        "/spine/merge-candidates/<int:candidate_id>/review",
        "/spine/subjects/<int:subject_id>/account-discovery",
        "/spine/subjects/<int:subject_id>/account-discovery/ingest",
        "/spine/subjects/<int:subject_id>/dossier",
        "/spine/subjects/<int:subject_id>/dossier-v2/export/<path:name>/download",
        "/spine/subjects/<int:subject_id>/dossier-v2/export/run",
        "/target/<int:target_id>",
        "/target/<int:target_id>/delete",
        "/target/<int:target_id>/export",
        "/target/run",
        "/workbench/jobs",
        "/workbench/jobs/<int:job_id>/run",
        "/workbench/jobs/run-next",
        "/workbench/policy",
        "/workbench/retention/run"
      ]
    },
    {
      "file": "src/socmint/distribution_action_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/distribution-actions/<case_id>/<subject_id>",
        "/api/v1/dossier-builder/v3/distribution-packet/<case_id>/<subject_id>",
        "/api/v1/dossier-builder/v3/distribution-packet/<case_id>/<subject_id>/markdown"
      ]
    },
    {
      "file": "src/socmint/distribution_export_verification_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/verify",
        "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/verify/markdown"
      ]
    },
    {
      "file": "src/socmint/distribution_handoff_packet_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/distribution-handoff/<case_id>",
        "/api/v1/dossier-builder/v3/distribution-handoff/<case_id>/markdown"
      ]
    },
    {
      "file": "src/socmint/distribution_packet_export_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>",
        "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/build",
        "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/download"
      ]
    },
    {
      "file": "src/socmint/distribution_release_ledger_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/distribution-release-ledger/<case_id>",
        "/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>",
        "/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>/markdown",
        "/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>/seal"
      ]
    },
    {
      "file": "src/socmint/dossier_builder_v3_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/build",
        "/api/v1/dossier-builder/v3/capabilities",
        "/api/v1/dossier-builder/v3/summary"
      ]
    },
    {
      "file": "src/socmint/dossier_certification_index_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/certification-index/<case_id>",
        "/api/v1/dossier-builder/v3/certification-index/<case_id>/<subject_id>",
        "/api/v1/dossier-builder/v3/certification-index/<case_id>/markdown",
        "/api/v1/dossier-builder/v3/certification-index/<case_id>/summary",
        "/api/v1/dossier-builder/v3/export-certification-index/<case_id>",
        "/api/v1/dossier-builder/v3/export-certification-index/<case_id>/review",
        "/api/v1/dossier-builder/v3/export-certification-index/<case_id>/summary"
      ]
    },
    {
      "file": "src/socmint/dossier_export_audit_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/export-audit",
        "/api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>",
        "/api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>/event",
        "/api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>/summary"
      ]
    },
    {
      "file": "src/socmint/dossier_export_certification_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>",
        "/api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>/statement",
        "/api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>/summary"
      ]
    },
    {
      "file": "src/socmint/dossier_export_gate_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>",
        "/api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>/decision",
        "/api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>/summary"
      ]
    },
    {
      "file": "src/socmint/dossier_export_index_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/export-download/<case_id>/<subject_id>/<filename>",
        "/api/v1/dossier-builder/v3/export-index",
        "/api/v1/dossier-builder/v3/export-index/<case_id>/<subject_id>"
      ]
    },
    {
      "file": "src/socmint/dossier_export_pack_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/export-pack",
        "/api/v1/dossier-builder/v3/export-pack/summary"
      ]
    },
    {
      "file": "src/socmint/dossier_export_store_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/export-store",
        "/api/v1/dossier-builder/v3/export-store/<case_id>/<subject_id>/manifest",
        "/api/v1/dossier-builder/v3/export-store/<case_id>/<subject_id>/summary"
      ]
    },
    {
      "file": "src/socmint/dossier_export_verification_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>",
        "/api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>/hashes",
        "/api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>/summary"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_certificate_bundle_routes_v7_5_5.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle",
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle.zip"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_certificate_bundle_verify_routes_v7_5_6.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify",
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify-zip"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_certificate_handoff_index_routes_v7_5_7.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index",
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/from-zip",
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/markdown"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_certificate_routes_v7_5_4.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate",
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/from-zip",
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/markdown"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_closeout_export_bundle_routes_v7_5_11.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export",
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export.zip"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_closeout_export_verify_routes_v7_5_12.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export/verify",
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export/verify-zip"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_closeout_report_routes_v7_5_10.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report",
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/from-zip",
        "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/markdown"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_export_routes_v7_5_2.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/export",
        "/api/v1/dossier-builder/v3/intelligence/finalization/export.zip"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_export_verify_routes_v7_5_3.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/export/verify",
        "/api/v1/dossier-builder/v3/intelligence/finalization/export/verify-zip"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_handoff_export_bundle_routes_v7_5_8.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export",
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export.zip"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_handoff_export_verify_routes_v7_5_9.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify",
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify-zip"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_master_delivery_export_bundle_routes_v7_5_14.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/export",
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/export.zip"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_master_delivery_index_routes_v7_5_13.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index",
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/from-bundle",
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/from-zip",
        "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/markdown"
      ]
    },
    {
      "file": "src/socmint/dossier_finalization_routes_v7_5_1.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/finalization",
        "/api/v1/dossier-builder/v3/intelligence/finalization/markdown"
      ]
    },
    {
      "file": "src/socmint/entity_profile_intelligence_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/build",
        "/api/v1/dossier-builder/v3/intelligence/markdown",
        "/api/v1/dossier-builder/v3/intelligence/summary"
      ]
    },
    {
      "file": "src/socmint/entity_profile_intelligence_ui_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/intelligence/sample",
        "/dossier/entity-profile-intelligence"
      ]
    },
    {
      "file": "src/socmint/export_quality_routes.py",
      "routes": [
        "/api/v1/spine/subjects/<int:subject_id>/export-quality",
        "/api/v1/spine/subjects/<int:subject_id>/export-quality/summary"
      ]
    },
    {
      "file": "src/socmint/hardening_routes.py",
      "routes": [
        "/api/v1/admin/gates/enforcement",
        "/api/v1/admin/gates/enforcement/summary",
        "/api/v1/admin/gates/matrix",
        "/api/v1/admin/gates/summary",
        "/api/v1/admin/security/checklist",
        "/api/v1/spine/subjects/<int:subject_id>/export-preflight",
        "/api/v1/spine/subjects/<int:subject_id>/export-preflight/summary"
      ]
    },
    {
      "file": "src/socmint/hidden_service_diagnostics_routes_v12_10_16.py",
      "routes": [
        "/api/v1/tor/diagnostics"
      ]
    },
    {
      "file": "src/socmint/membership_routes.py",
      "routes": [
        "/account/usage",
        "/admin/memberships",
        "/api/v1/account/gate",
        "/api/v1/account/membership",
        "/api/v1/admin/memberships",
        "/api/v1/admin/memberships/<username>",
        "/api/v1/admin/quota-overrides/<username>"
      ]
    },
    {
      "file": "src/socmint/operator_smoke_routes.py",
      "routes": [
        "/api/v1/admin/operator-smoke/matrix",
        "/api/v1/admin/operator-smoke/summary",
        "/api/v1/admin/operator-smoke/validate"
      ]
    },
    {
      "file": "src/socmint/product_artifacts.py",
      "routes": [
        "/api/v1/product/artifact-export-manifest",
        "/api/v1/product/artifact-review-audit",
        "/api/v1/product/artifact-review-state",
        "/api/v1/product/artifacts",
        "/api/v1/product/release-package",
        "/api/v1/product/release-packages",
        "/product/artifacts",
        "/product/release-package"
      ]
    },
    {
      "file": "src/socmint/product_post_release.py",
      "routes": [
        "/api/v1/product/final",
        "/api/v1/product/final/handoff",
        "/api/v1/product/final/self-test",
        "/api/v1/product/final/v10-bootstrap",
        "/api/v1/product/final/v10-bootstrap/audit",
        "/product/final",
        "/product/final/handoff",
        "/product/final/self-test",
        "/product/final/v10-bootstrap"
      ]
    },
    {
      "file": "src/socmint/product_registry.py",
      "routes": [
        "/api/v1/product/v10/action-route-readiness",
        "/api/v1/product/v10/action-route-readiness/write",
        "/api/v1/product/v10/blueprint-guardrails",
        "/api/v1/product/v10/blueprint-guardrails/write",
        "/api/v1/product/v10/blueprint-wave2",
        "/api/v1/product/v10/blueprint-wave2/write",
        "/api/v1/product/v10/migration-plan",
        "/api/v1/product/v10/migration-plan/write",
        "/api/v1/product/v10/module-health",
        "/api/v1/product/v10/module-health/write",
        "/api/v1/product/v10/modules",
        "/api/v1/product/v10/modules/write",
        "/api/v1/product/v10/route-ownership",
        "/product/v10/action-route-readiness",
        "/product/v10/blueprint-guardrails",
        "/product/v10/blueprint-wave2",
        "/product/v10/migration-plan",
        "/product/v10/module-health",
        "/product/v10/modules"
      ]
    },
    {
      "file": "src/socmint/product_release_flow.py",
      "routes": [
        "/api/v1/product/final-gate",
        "/api/v1/product/final-release",
        "/api/v1/product/final-release/verify",
        "/api/v1/product/release-candidate",
        "/product/final-gate",
        "/product/release-candidate"
      ]
    },
    {
      "file": "src/socmint/product_v10.py",
      "routes": [
        "/api/v1/product/v10/architecture",
        "/api/v1/product/v10/architecture/write",
        "/api/v1/product/v10/compatibility",
        "/product/v10",
        "/product/v10/bootstrap-compat"
      ]
    },
    {
      "file": "src/socmint/production_installer_routes.py",
      "routes": [
        "/api/v1/admin/installer/plan",
        "/api/v1/admin/installer/readiness",
        "/api/v1/admin/installer/readiness/summary"
      ]
    },
    {
      "file": "src/socmint/production_release_routes.py",
      "routes": [
        "/api/v1/production-release",
        "/api/v1/production-release/summary"
      ]
    },
    {
      "file": "src/socmint/release_integrity_routes.py",
      "routes": [
        "/api/v1/admin/release-integrity/report",
        "/api/v1/admin/release-integrity/routes",
        "/api/v1/admin/release-integrity/summary"
      ]
    },
    {
      "file": "src/socmint/release_ledger_dashboard_routes.py",
      "routes": [
        "/api/v1/dossier-builder/v3/release-ledger-dashboard/<case_id>",
        "/api/v1/dossier-builder/v3/release-ledger-dashboard/<case_id>/markdown",
        "/dossier/release-ledger-dashboard"
      ]
    },
    {
      "file": "src/socmint/release_mount_routes_v12_10_20.py",
      "routes": [
        "/api/v1/release/mounts",
        "/release/mounts"
      ]
    },
    {
      "file": "src/socmint/release_pipeline_routes.py",
      "routes": [
        "/api/v1/admin/release-pipeline",
        "/api/v1/admin/release-pipeline/summary",
        "/api/v1/admin/release-pipeline/workflow"
      ]
    },
    {
      "file": "src/socmint/release_runtime_routes_v12_10_21.py",
      "routes": [
        "/api/v1/release/runtime",
        "/release/runtime"
      ]
    },
    {
      "file": "src/socmint/release_status_routes_v12_10_17.py",
      "routes": [
        "/api/v1/release/gates/latest",
        "/api/v1/release/status"
      ]
    },
    {
      "file": "src/socmint/release_status_ui_routes_v12_10_18.py",
      "routes": [
        "/release/gates",
        "/release/status"
      ]
    },
    {
      "file": "src/socmint/security_audit_routes.py",
      "routes": [
        "/api/v1/admin/security/audit",
        "/api/v1/admin/security/cookies",
        "/api/v1/admin/security/headers",
        "/api/v1/admin/security/secret-key",
        "/api/v1/admin/security/secrets/scan"
      ]
    },
    {
      "file": "src/socmint/tor_routes.py",
      "routes": [
        "/api/v1/admin/tor/status",
        "/api/v1/tor/readiness",
        "/api/v1/tor/status",
        "/api/v1/tor/torrc"
      ]
    },
    {
      "file": "src/socmint/v10_24_final_delivery_workspace_routes.py",
      "routes": [
        "/api/v1/v10/final-delivery/export.zip",
        "/api/v1/v10/final-delivery/workspace"
      ]
    },
    {
      "file": "src/socmint/v10_25_final_delivery_operator_console_routes.py",
      "routes": [
        "/api/v1/v10/final-delivery/commands",
        "/api/v1/v10/final-delivery/console"
      ]
    },
    {
      "file": "src/socmint/v10_26_final_delivery_audit_trail_routes.py",
      "routes": [
        "/api/v1/v10/final-delivery/audit-receipt",
        "/api/v1/v10/final-delivery/audit-trail"
      ]
    },
    {
      "file": "src/socmint/v10_27_final_delivery_evidence_capsule_routes.py",
      "routes": [
        "/api/v1/v10/final-delivery/evidence-capsule",
        "/api/v1/v10/final-delivery/evidence-capsule/summary"
      ]
    },
    {
      "file": "src/socmint/v10_28_final_delivery_capsule_export_pack_routes.py",
      "routes": [
        "/api/v1/v10/final-delivery/evidence-capsule/export",
        "/api/v1/v10/final-delivery/evidence-capsule/export.zip"
      ]
    },
    {
      "file": "src/socmint/v10_29_final_delivery_dashboard_api_routes.py",
      "routes": [
        "/api/v1/v10/final-delivery/dashboard",
        "/api/v1/v10/final-delivery/dashboard/actions"
      ]
    },
    {
      "file": "src/socmint/v10_30_case_delivery_registry_routes.py",
      "routes": [
        "/api/v1/v10/final-delivery/cases/<case_id>/registry",
        "/api/v1/v10/final-delivery/cases/<case_id>/registry/delivery",
        "/api/v1/v10/final-delivery/cases/<case_id>/registry/summaries"
      ]
    },
    {
      "file": "src/socmint/v10_31_human_approval_gate_routes.py",
      "routes": [
        "/api/v1/v10/final-delivery/cases/<case_id>/approval-gate",
        "/api/v1/v10/final-delivery/cases/<case_id>/approval-gate/summary"
      ]
    },
    {
      "file": "src/socmint/v10_32_productization_ux_routes.py",
      "routes": [
        "/api/v1/v10/productization/cases/<case_id>/summary",
        "/api/v1/v10/productization/cases/<case_id>/ui"
      ]
    },
    {
      "file": "src/socmint/v10_38_productization_ux_routes.py",
      "routes": [
        "/api/v10.38/productization/cases/<case_id>/summary",
        "/api/v10.38/productization/cases/<case_id>/ui"
      ]
    },
    {
      "file": "src/socmint/v12_10_29_ui.py",
      "routes": [
        "/api/v12.10/ui/command-center",
        "/command-center"
      ]
    },
    {
      "file": "src/socmint/v12_10_command_center_routes.py",
      "routes": [
        "/api/v12.10/analyst/propagate/<case_id>",
        "/api/v12.10/command-center/cases/<case_id>/run-all",
        "/api/v12.10/dossier/run/<case_id>",
        "/api/v12.10/evidence/integrity/<case_id>",
        "/api/v12.10/monitoring/evolve/<case_id>",
        "/api/v12.10/risk/score/<case_id>",
        "/api/v12.10/runtime/mesh/<case_id>"
      ]
    },
    {
      "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/flask/ctx.py",
      "routes": [
        "/"
      ]
    },
    {
      "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/flask/helpers.py",
      "routes": [
        "/stream",
        "/uploads/<path:name>"
      ]
    },
    {
      "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/flask/sansio/scaffold.py",
      "routes": [
        "/"
      ]
    },
    {
      "file": "var/venvs/v12_10_17/lib/python3.13/site-packages/flask_httpauth.py",
      "routes": [
        "/",
        "/private"
      ]
    }
  ],
  "routes": [
    "/",
    "/about",
    "/account/password",
    "/account/usage",
    "/admin/audit",
    "/admin/memberships",
    "/admin/users",
    "/admin/users/<int:user_id>",
    "/analyst/console",
    "/analyst/launchpad",
    "/api/v1/account/billing",
    "/api/v1/account/billing/checkout",
    "/api/v1/account/case-access",
    "/api/v1/account/gate",
    "/api/v1/account/membership",
    "/api/v1/admin/beta/readiness",
    "/api/v1/admin/beta/readiness/summary",
    "/api/v1/admin/billing/customer-links/<username>",
    "/api/v1/admin/billing/events",
    "/api/v1/admin/billing/provider-config",
    "/api/v1/admin/billing/provider-events",
    "/api/v1/admin/case-access/<int:case_id>",
    "/api/v1/admin/certification/report",
    "/api/v1/admin/certification/summary",
    "/api/v1/admin/gates/enforcement",
    "/api/v1/admin/gates/enforcement/summary",
    "/api/v1/admin/gates/matrix",
    "/api/v1/admin/gates/summary",
    "/api/v1/admin/installer/plan",
    "/api/v1/admin/installer/readiness",
    "/api/v1/admin/installer/readiness/summary",
    "/api/v1/admin/memberships",
    "/api/v1/admin/memberships/<username>",
    "/api/v1/admin/operator-smoke/matrix",
    "/api/v1/admin/operator-smoke/summary",
    "/api/v1/admin/operator-smoke/validate",
    "/api/v1/admin/quota-overrides/<username>",
    "/api/v1/admin/release-integrity/report",
    "/api/v1/admin/release-integrity/routes",
    "/api/v1/admin/release-integrity/summary",
    "/api/v1/admin/release-pipeline",
    "/api/v1/admin/release-pipeline/summary",
    "/api/v1/admin/release-pipeline/workflow",
    "/api/v1/admin/security/audit",
    "/api/v1/admin/security/checklist",
    "/api/v1/admin/security/cookies",
    "/api/v1/admin/security/headers",
    "/api/v1/admin/security/secret-key",
    "/api/v1/admin/security/secrets/scan",
    "/api/v1/admin/teams/<team_key>/members",
    "/api/v1/admin/tor/status",
    "/api/v1/analyst/launchpad",
    "/api/v1/analyst/launchpad/compact",
    "/api/v1/analyst/workbench",
    "/api/v1/beta/onboarding",
    "/api/v1/billing/webhook",
    "/api/v1/cases",
    "/api/v1/cases/<case_key>",
    "/api/v1/cases/<int:case_id>/access/check",
    "/api/v1/connectors/marketplace",
    "/api/v1/connectors/sdk/catalog",
    "/api/v1/connectors/sdk/fixture-run",
    "/api/v1/connectors/sdk/marketplace",
    "/api/v1/connectors/sdk/validate",
    "/api/v1/dossier-builder/v3/build",
    "/api/v1/dossier-builder/v3/capabilities",
    "/api/v1/dossier-builder/v3/certification-dashboard/<case_id>",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>/<subject_id>",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>/markdown",
    "/api/v1/dossier-builder/v3/certification-index/<case_id>/summary",
    "/api/v1/dossier-builder/v3/distribution-actions/<case_id>/<subject_id>",
    "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>",
    "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/build",
    "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/download",
    "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/verify",
    "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/verify/markdown",
    "/api/v1/dossier-builder/v3/distribution-handoff/<case_id>",
    "/api/v1/dossier-builder/v3/distribution-handoff/<case_id>/markdown",
    "/api/v1/dossier-builder/v3/distribution-packet/<case_id>/<subject_id>",
    "/api/v1/dossier-builder/v3/distribution-packet/<case_id>/<subject_id>/markdown",
    "/api/v1/dossier-builder/v3/distribution-release-ledger/<case_id>",
    "/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>",
    "/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>/markdown",
    "/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>/seal",
    "/api/v1/dossier-builder/v3/export-audit",
    "/api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>",
    "/api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>/event",
    "/api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>/summary",
    "/api/v1/dossier-builder/v3/export-certification-index/<case_id>",
    "/api/v1/dossier-builder/v3/export-certification-index/<case_id>/review",
    "/api/v1/dossier-builder/v3/export-certification-index/<case_id>/summary",
    "/api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>",
    "/api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>/statement",
    "/api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>/summary",
    "/api/v1/dossier-builder/v3/export-download/<case_id>/<subject_id>/<filename>",
    "/api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>",
    "/api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>/decision",
    "/api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>/summary",
    "/api/v1/dossier-builder/v3/export-index",
    "/api/v1/dossier-builder/v3/export-index/<case_id>/<subject_id>",
    "/api/v1/dossier-builder/v3/export-pack",
    "/api/v1/dossier-builder/v3/export-pack/summary",
    "/api/v1/dossier-builder/v3/export-store",
    "/api/v1/dossier-builder/v3/export-store/<case_id>/<subject_id>/manifest",
    "/api/v1/dossier-builder/v3/export-store/<case_id>/<subject_id>/summary",
    "/api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>",
    "/api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>/hashes",
    "/api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>/summary",
    "/api/v1/dossier-builder/v3/intelligence/build",
    "/api/v1/dossier-builder/v3/intelligence/finalization",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle.zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify-zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/from-zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export.zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify-zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/from-zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/markdown",
    "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/markdown",
    "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report",
    "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export",
    "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export.zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export/verify",
    "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/export/verify-zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/from-zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/closeout-report/markdown",
    "/api/v1/dossier-builder/v3/intelligence/finalization/export",
    "/api/v1/dossier-builder/v3/intelligence/finalization/export.zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/export/verify",
    "/api/v1/dossier-builder/v3/intelligence/finalization/export/verify-zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/markdown",
    "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index",
    "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/export",
    "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/export.zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/from-bundle",
    "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/from-zip",
    "/api/v1/dossier-builder/v3/intelligence/finalization/master-delivery-index/markdown",
    "/api/v1/dossier-builder/v3/intelligence/markdown",
    "/api/v1/dossier-builder/v3/intelligence/sample",
    "/api/v1/dossier-builder/v3/intelligence/summary",
    "/api/v1/dossier-builder/v3/release-ledger-dashboard/<case_id>",
    "/api/v1/dossier-builder/v3/release-ledger-dashboard/<case_id>/markdown",
    "/api/v1/dossier-builder/v3/summary",
    "/api/v1/dossier/<subject_id>/quality-gate",
    "/api/v1/dossier/<subject_id>/traceability",
    "/api/v1/evidence/attachment-map",
    "/api/v1/evidence/capture",
    "/api/v1/evidence/captures",
    "/api/v1/evidence/captures/<capture_id>/verify",
    "/api/v1/evidence/custody",
    "/api/v1/evidence/custody/report",
    "/api/v1/evidence/intake",
    "/api/v1/evidence/integrity",
    "/api/v1/evidence/integrity/pack",
    "/api/v1/evidence/links",
    "/api/v1/evidence/links/delete",
    "/api/v1/evidence/verify",
    "/api/v1/exports/builder",
    "/api/v1/exports/builder/bundle",
    "/api/v1/exports/builder/bundles/<path:name>/verify",
    "/api/v1/jobs/<int:job_id>/cancel",
    "/api/v1/jobs/<int:job_id>/requeue",
    "/api/v1/jobs/health",
    "/api/v1/product/actions/export-control-snapshot",
    "/api/v1/product/actions/write-reports",
    "/api/v1/product/artifact-export-manifest",
    "/api/v1/product/artifact-export-manifest/write",
    "/api/v1/product/artifact-review-audit",
    "/api/v1/product/artifact-review-state",
    "/api/v1/product/artifacts",
    "/api/v1/product/artifacts/review",
    "/api/v1/product/build-status",
    "/api/v1/product/final",
    "/api/v1/product/final-gate",
    "/api/v1/product/final-gate/signoff",
    "/api/v1/product/final-gate/signoff-audit",
    "/api/v1/product/final-gate/write",
    "/api/v1/product/final-release",
    "/api/v1/product/final-release/archive/<release_name>",
    "/api/v1/product/final-release/archive/<release_name>/create",
    "/api/v1/product/final-release/archives",
    "/api/v1/product/final-release/distribution",
    "/api/v1/product/final-release/distribution/audit",
    "/api/v1/product/final-release/distribution/decision",
    "/api/v1/product/final-release/distribution/write",
    "/api/v1/product/final-release/publish",
    "/api/v1/product/final-release/verify",
    "/api/v1/product/final/handoff",
    "/api/v1/product/final/handoff/build",
    "/api/v1/product/final/self-test",
    "/api/v1/product/final/self-test/maintenance",
    "/api/v1/product/final/self-test/maintenance-audit",
    "/api/v1/product/final/self-test/write",
    "/api/v1/product/final/v10-bootstrap",
    "/api/v1/product/final/v10-bootstrap/audit",
    "/api/v1/product/final/v10-bootstrap/decision",
    "/api/v1/product/final/v10-bootstrap/write",
    "/api/v1/product/final/write",
    "/api/v1/product/operator-runbook",
    "/api/v1/product/release-candidate",
    "/api/v1/product/release-candidate/write",
    "/api/v1/product/release-package",
    "/api/v1/product/release-package/<package_name>/zip",
    "/api/v1/product/release-package/build",
    "/api/v1/product/release-packages",
    "/api/v1/product/release-readiness",
    "/api/v1/product/runtime-actions",
    "/api/v1/product/smoke-summary",
    "/api/v1/product/system-health",
    "/api/v1/product/v10/action-route-readiness",
    "/api/v1/product/v10/action-route-readiness/write",
    "/api/v1/product/v10/architecture",
    "/api/v1/product/v10/architecture/write",
    "/api/v1/product/v10/blueprint-guardrails",
    "/api/v1/product/v10/blueprint-guardrails/write",
    "/api/v1/product/v10/blueprint-wave2",
    "/api/v1/product/v10/blueprint-wave2/write",
    "/api/v1/product/v10/compatibility",
    "/api/v1/product/v10/migration-plan",
    "/api/v1/product/v10/migration-plan/write",
    "/api/v1/product/v10/module-health",
    "/api/v1/product/v10/module-health/write",
    "/api/v1/product/v10/modules",
    "/api/v1/product/v10/modules/write",
    "/api/v1/product/v10/route-ownership",
    "/api/v1/product/write-reports",
    "/api/v1/production-release",
    "/api/v1/production-release/summary",
    "/api/v1/release/gates/latest",
    "/api/v1/release/mounts",
    "/api/v1/release/runtime",
    "/api/v1/release/status",
    "/api/v1/reports/export-center",
    "/api/v1/reports/export-center/artifacts/<path:name>",
    "/api/v1/reports/export-center/attachments",
    "/api/v1/reports/export-center/attachments/zip",
    "/api/v1/reports/export-center/review-gated",
    "/api/v1/reports/export-center/zip",
    "/api/v1/reports/review/audit",
    "/api/v1/reports/review/bulk",
    "/api/v1/reports/review/items",
    "/api/v1/reports/review/items/<path:item_id>",
    "/api/v1/reports/review/summary",
    "/api/v1/reports/runs",
    "/api/v1/responsible-use/gate",
    "/api/v1/responsible-use/review",
    "/api/v1/responsible-use/scope",
    "/api/v1/spine/<int:subject_id>/graph/canvas",
    "/api/v1/spine/<int:subject_id>/resolution-lab",
    "/api/v1/spine/account-discovery/<int:discovery_id>/review",
    "/api/v1/spine/assertions/<int:assertion_id>",
    "/api/v1/spine/assertions/review-queue",
    "/api/v1/spine/connectors/quality",
    "/api/v1/spine/enrichment-review",
    "/api/v1/spine/enrichments/<int:enrichment_id>/findings/",
    "/api/v1/spine/subjects",
    "/api/v1/spine/subjects/<int:subject_id>/account-discovery",
    "/api/v1/spine/subjects/<int:subject_id>/account-discovery/ingest",
    "/api/v1/spine/subjects/<int:subject_id>/contradictions",
    "/api/v1/spine/subjects/<int:subject_id>/contradictions/run",
    "/api/v1/spine/subjects/<int:subject_id>/dossier",
    "/api/v1/spine/subjects/<int:subject_id>/dossier-v2",
    "/api/v1/spine/subjects/<int:subject_id>/dossier-v2/export",
    "/api/v1/spine/subjects/<int:subject_id>/export-preflight",
    "/api/v1/spine/subjects/<int:subject_id>/export-preflight/summary",
    "/api/v1/spine/subjects/<int:subject_id>/export-quality",
    "/api/v1/spine/subjects/<int:subject_id>/export-quality/summary",
    "/api/v1/spine/subjects/<int:subject_id>/exports",
    "/api/v1/spine/subjects/<int:subject_id>/exports/run",
    "/api/v1/spine/subjects/<int:subject_id>/graph",
    "/api/v1/spine/subjects/<int:subject_id>/media-profiles",
    "/api/v1/spine/subjects/<int:subject_id>/media-profiles/run",
    "/api/v1/spine/subjects/<int:subject_id>/run",
    "/api/v1/tor/diagnostics",
    "/api/v1/tor/readiness",
    "/api/v1/tor/status",
    "/api/v1/tor/torrc",
    "/api/v1/v10/final-delivery/audit-receipt",
    "/api/v1/v10/final-delivery/audit-trail",
    "/api/v1/v10/final-delivery/cases/<case_id>/approval-gate",
    "/api/v1/v10/final-delivery/cases/<case_id>/approval-gate/summary",
    "/api/v1/v10/final-delivery/cases/<case_id>/registry",
    "/api/v1/v10/final-delivery/cases/<case_id>/registry/delivery",
    "/api/v1/v10/final-delivery/cases/<case_id>/registry/summaries",
    "/api/v1/v10/final-delivery/commands",
    "/api/v1/v10/final-delivery/console",
    "/api/v1/v10/final-delivery/dashboard",
    "/api/v1/v10/final-delivery/dashboard/actions",
    "/api/v1/v10/final-delivery/evidence-capsule",
    "/api/v1/v10/final-delivery/evidence-capsule/export",
    "/api/v1/v10/final-delivery/evidence-capsule/export.zip",
    "/api/v1/v10/final-delivery/evidence-capsule/summary",
    "/api/v1/v10/final-delivery/export.zip",
    "/api/v1/v10/final-delivery/workspace",
    "/api/v1/v10/productization/cases/<case_id>/summary",
    "/api/v1/v10/productization/cases/<case_id>/ui",
    "/api/v1/workbench/jobs",
    "/api/v1/workbench/jobs/<int:job_id>/run",
    "/api/v1/workbench/jobs/run-next",
    "/api/v1/workbench/policy/evaluate",
    "/api/v1/workbench/policy/events",
    "/api/v1/workbench/retention/run",
    "/api/v1/workbench/status",
    "/api/v10.38/productization/cases/<case_id>/summary",
    "/api/v10.38/productization/cases/<case_id>/ui",
    "/api/v12.10/analyst/propagate/<case_id>",
    "/api/v12.10/command-center/cases/<case_id>/run-all",
    "/api/v12.10/dossier/run/<case_id>",
    "/api/v12.10/evidence/integrity/<case_id>",
    "/api/v12.10/monitoring/evolve/<case_id>",
    "/api/v12.10/risk/score/<case_id>",
    "/api/v12.10/runtime/mesh/<case_id>",
    "/api/v12.10/ui/command-center",
    "/cases",
    "/cases/<case_key>",
    "/command-center",
    "/connectors/marketplace",
    "/dossier/certification-dashboard",
    "/dossier/entity-profile-intelligence",
    "/dossier/release-ledger-dashboard",
    "/evidence/capture",
    "/evidence/custody",
    "/evidence/intake",
    "/evidence/intake/add",
    "/evidence/intake/files/<path:name>/download",
    "/evidence/integrity",
    "/evidence/integrity/pack/run",
    "/evidence/integrity/packs/<path:name>/download",
    "/evidence/links",
    "/evidence/links/add",
    "/evidence/verify/run",
    "/exports/builder",
    "/healthz",
    "/jobs",
    "/login",
    "/logout",
    "/media/<int:media_id>/<path:filename>",
    "/private",
    "/product/actions/export-control-snapshot",
    "/product/actions/refresh-readiness",
    "/product/actions/write-reports",
    "/product/artifacts",
    "/product/artifacts/audit/<path:relpath>",
    "/product/artifacts/download/<path:relpath>",
    "/product/artifacts/export-manifest",
    "/product/artifacts/export-manifest/write",
    "/product/artifacts/review",
    "/product/artifacts/view/<path:relpath>",
    "/product/build-control",
    "/product/final",
    "/product/final-gate",
    "/product/final-gate/signoff",
    "/product/final-gate/write",
    "/product/final-release",
    "/product/final-release/archive",
    "/product/final-release/archive/<release_name>/create",
    "/product/final-release/archive/download/<path:filename>",
    "/product/final-release/distribution",
    "/product/final-release/distribution/decision",
    "/product/final-release/distribution/write",
    "/product/final-release/publish",
    "/product/final-release/verify",
    "/product/final/handoff",
    "/product/final/handoff/build",
    "/product/final/self-test",
    "/product/final/self-test/maintenance",
    "/product/final/self-test/write",
    "/product/final/v10-bootstrap",
    "/product/final/v10-bootstrap/decision",
    "/product/final/v10-bootstrap/write",
    "/product/final/write",
    "/product/operator-runbook",
    "/product/release-candidate",
    "/product/release-candidate/write",
    "/product/release-package",
    "/product/release-package/build",
    "/product/release-package/download/<package_name>",
    "/product/release-package/zip/<package_name>",
    "/product/v10",
    "/product/v10/action-route-readiness",
    "/product/v10/blueprint-guardrails",
    "/product/v10/blueprint-wave2",
    "/product/v10/bootstrap-compat",
    "/product/v10/migration-plan",
    "/product/v10/module-health",
    "/product/v10/modules",
    "/readyz",
    "/release/gates",
    "/release/mounts",
    "/release/runtime",
    "/release/status",
    "/reports/<path:filename>",
    "/reports/export-center",
    "/reports/export-center/artifacts/<path:name>/download",
    "/reports/export-center/bundles/<path:name>/download",
    "/reports/export-center/manifests/<path:name>",
    "/reports/export-center/review-gated/run",
    "/reports/export-center/zip/run",
    "/reports/review",
    "/reports/review/items/<path:item_id>/<status>",
    "/responsible-use",
    "/results/<session_id>",
    "/search",
    "/signup",
    "/spine",
    "/spine/<int:subject_id>",
    "/spine/<int:subject_id>/contradictions",
    "/spine/<int:subject_id>/contradictions/run",
    "/spine/<int:subject_id>/exports",
    "/spine/<int:subject_id>/exports/run",
    "/spine/<int:subject_id>/graph",
    "/spine/<int:subject_id>/graph/build",
    "/spine/<int:subject_id>/graph/canvas",
    "/spine/<int:subject_id>/media-profiles",
    "/spine/<int:subject_id>/media-profiles/run",
    "/spine/<int:subject_id>/resolution-lab",
    "/spine/<int:subject_id>/run",
    "/spine/account-discovery/<int:discovery_id>/review",
    "/spine/assertions/<int:assertion_id>",
    "/spine/assertions/<int:assertion_id>/validate",
    "/spine/connectors/quality",
    "/spine/contradictions/<int:contradiction_id>/resolve",
    "/spine/enrichment-review",
    "/spine/enrichments/<int:enrichment_id>/findings/<int:finding_index>/review",
    "/spine/merge-candidates/<int:candidate_id>/review",
    "/spine/subjects/<int:subject_id>/account-discovery",
    "/spine/subjects/<int:subject_id>/account-discovery/ingest",
    "/spine/subjects/<int:subject_id>/dossier",
    "/spine/subjects/<int:subject_id>/dossier-v2/export/<path:name>/download",
    "/spine/subjects/<int:subject_id>/dossier-v2/export/run",
    "/status/<timestamp>",
    "/stream",
    "/target/<int:target_id>",
    "/target/<int:target_id>/delete",
    "/target/<int:target_id>/export",
    "/target/run",
    "/uploads/<path:name>",
    "/workbench/jobs",
    "/workbench/jobs/<int:job_id>/run",
    "/workbench/jobs/run-next",
    "/workbench/policy",
    "/workbench/retention/run"
  ]
}
```

### runtime_v12_route_registration: FAIL

```json
{
  "attempted": true,
  "dashboard_module_file": "/home/pmwens/Projects/SOCMINT-PROJECT/src/socmint/dashboard.py",
  "error": "PermissionError(13, 'Permission denied')",
  "missing_v12_route_count": 8,
  "missing_v12_routes": [
    "/api/v12.10/analyst/propagate/<case_id>",
    "/api/v12.10/command-center/cases/<case_id>/run-all",
    "/api/v12.10/dossier/run/<case_id>",
    "/api/v12.10/evidence/integrity/<case_id>",
    "/api/v12.10/monitoring/evolve/<case_id>",
    "/api/v12.10/risk/score/<case_id>",
    "/api/v12.10/runtime/mesh/<case_id>",
    "/api/v12.10/ui/command-center"
  ],
  "missing_v12_routes_before_lock": [
    "/api/v12.10/analyst/propagate/<case_id>",
    "/api/v12.10/command-center/cases/<case_id>/run-all",
    "/api/v12.10/dossier/run/<case_id>",
    "/api/v12.10/evidence/integrity/<case_id>",
    "/api/v12.10/monitoring/evolve/<case_id>",
    "/api/v12.10/risk/score/<case_id>",
    "/api/v12.10/runtime/mesh/<case_id>",
    "/api/v12.10/ui/command-center"
  ],
  "ok": false,
  "route_lock": {},
  "route_lock_errors": [],
  "route_lock_registered": [],
  "route_lock_skipped": [],
  "routes": [],
  "routes_after_lock": [],
  "routes_before_lock": []
}
```

### version_metadata: PASS

```json
{
  "expected_current": "12.10.31E",
  "historical_manifests": {
    "release/V12_10_29_RELEASE_MANIFEST.json": "12.10.29",
    "release/V12_10_31B_RELEASE_MANIFEST.json": "12.10.31B"
  },
  "items": {
    "pyproject.toml": "12.10.31E",
    "src/socmint/__init__.py": null
  },
  "metadata_consistent": true,
  "unique_versions": [
    "12.10.31E"
  ]
}
```

# v12.10.52 Final Release Readiness Report

- **release_status**: `HOLD`
- **runtime**: `hold`
- **route_lock**: `pass GO`
- **schema_lock**: `BASELINE_AWARE_DB_SMOKE_GO`
- **alembic_head**: `0018_approved_model_migration`
- **production_db_touched**: `False`
- **real_config_upgrade_run**: `False`

## Checks

- **PASS** `baseline_aware_status_go` — `GO`
- **PASS** `baseline_aware_release_pass_go` — `PASS GO`
- **PASS** `schema_lock_go` — `BASELINE_AWARE_DB_SMOKE_GO`
- **PASS** `production_db_not_touched` — `False`
- **PASS** `real_config_upgrade_not_run` — `False`
- **PASS** `approved_table_count_18` — `18`
- **PASS** `approved_baseline_table_count_16` — `16`
- **PASS** `owned_0018_table_count_2` — `2`
- **PASS** `missing_after_upgrade_zero` — `[]`
- **PASS** `owned_lingering_after_downgrade_zero` — `[]`
- **PASS** `baseline_missing_after_downgrade_zero` — `[]`
- **PASS** `version_after_upgrade_0018` — `0018_approved_model_migration`
- **PASS** `version_after_downgrade_0017` — `0017_v12_10_schema_reconciliation`
- **PASS** `promotion_ready_manifest_true` — `True`
- **PASS** `alembic_head_0018` — `0018_approved_model_migration (head)
`
- **PASS** `make_test121051` — `bash scripts/test_v12_10_51.sh
..                                                                       [100%]
2 passed in 2.54s
{
  "approved_baseline_table_count": 16,
  "approved_table_count": 18,
  "baseline_missing_after_downgrade_count": 0,
  "missing_after_upgrade_count": 0,
  "owned_0018_table_count": 2,
  "owned_lingering_after_downgrade_count": 0,
  "production_db_touched": false,
  "promotion_ready": "/home/pmwens/Projects/SOCMINT-PROJECT/release/baseline_aware_db_smoke/BASELINE_AWARE_PROMOTION_READY_V12_10_51.json",
  "real_config_upgrade_run": false,
  "release_status": "PASS GO",
  "report_json": "/home/pmwens/Projects/SOCMINT-PROJECT/release/baseline_aware_db_smoke/BASELINE_AWARE_DB_SMOKE_GATE_V12_10_51.json",
  "report_md": "/home/pmwens/Projects/SOCMINT-PROJECT/release/baseline_aware_db_smoke/BASELINE_AWARE_DB_SMOKE_GATE_V12_10_51.md",
  "schema_lock": "BASELINE_AWARE_DB_SMOKE_GO",
  "status": "GO",
  "version": "12.10.51",
  "version_after_downgrade": "0017_v12_10_schema_reconciliation",
  "version_after_upgrade": "0018_approved_model_migration"
}
[+] v12.10.51 baseline-aware DB smoke gate passed
`
- **PASS** `make_test121050` — `bash scripts/test_v12_10_50.sh
..                                                                       [100%]
2 passed in 1.76s
{
  "after_active_drop_count": 2,
  "approved_table_count": 18,
  "before_active_drop_count": 2,
  "change_count": 0,
  "missing_after_repair_count": 0,
  "owned_0018_table_count": 2,
  "production_db_touched": false,
  "real_config_upgrade_run": false,
  "repair_status": "GO",
  "report_json": "/home/pmwens/Projects/SOCMINT-PROJECT/release/downgrade_symmetry_repair/DOWNGRADE_SYMMETRY_REPAIR_V12_10_50.json",
  "report_md": "/home/pmwens/Projects/SOCMINT-PROJECT/release/downgrade_symmetry_repair/DOWNGRADE_SYMMETRY_REPAIR_V12_10_50.md",
  "schema_mutation": "none",
  "version": "12.10.50"
}
{
  "approved_table_count": 18,
  "error_count": 1,
  "lingering_after_downgrade_count": 16,
  "missing_after_upgrade_count": 0,
  "production_db_touched": false,
  "real_config_upgrade_run": false,
  "report_json": "/home/pmwens/Projects/SOCMINT-PROJECT/release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json",
  "report_md": "/home/pmwens/Projects/SOCMINT-PROJECT/release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.md",
  "smoke_status": "NO-GO",
  "tables_after_upgrade_count": 54,
  "temp_db_path": "/tmp/socmint_v12_10_38_ikm_pk_g/dry_run.sqlite",
  "version": "12.10.38",
  "version_after_downgrade": "0017_v12_10_schema_reconciliation",
  "version_after_upgrade": "0018_approved_model_migration",
  "warning_count": 0
}
{
  "db_smoke_go": false,
  "db_smoke_status": "NO-GO",
  "finding_count": 2,
  "production_db_touched": false,
  "promotion_ready_manifest": "/home/pmwens/Projects/SOCMINT-PROJECT/release/db_smoke_gate/PROMOTION_READY_MANIFEST_V12_10_39.json",
  "real_config_upgrade_run": false,
  "release_status": "HOLD",
  "repair_plan": "/home/pmwens/Projects/SOCMINT-PROJECT/release/db_smoke_gate/DB_SMOKE_REPAIR_PLAN_V12_10_39.md",
  "report_json": "/home/pmwens/Projects/SOCMINT-PROJECT/release/db_smoke_gate/DB_SMOKE_RESULT_GATE_V12_10_39.json",
  "report_md": "/home/pmwens/Projects/SOCMINT-PROJECT/release/db_smoke_gate/DB_SMOKE_RESULT_GATE_V12_10_39.md",
  "schema_lock": "DB_SMOKE_HOLD",
  "version": "12.10.39"
}
{
  "alembic_version_after_upgrade": "0018_approved_model_migration",
  "created_approved_table_count": 18,
  "exact_exception": null,
  "finding_count": 1,
  "full_sql_output": "/home/pmwens/Projects/SOCMINT-PROJECT/release/full_db_smoke_trace/ALEMBIC_UPGRADE_HEAD_SQL_MODE_V12_10_48.sql",
  "full_upgrade_output": "/home/pmwens/Projects/SOCMINT-PROJECT/release/full_db_smoke_trace/ALEMBIC_UPGRADE_HEAD_FULL_OUTPUT_V12_10_48.txt",
  "missing_approved_table_count": 0,
  "missing_approved_tables": [],
  "patch_decision": "/home/pmwens/Projects/SOCMINT-PROJECT/release/full_db_smoke_trace/NEXT_PATCH_DECISION_V12_10_48.md",
  "production_db_touched": false,
  "real_config_upgrade_run": false,
  "report_json": "/home/pmwens/Projects/SOCMINT-PROJECT/release/full_db_smoke_trace/FULL_DB_SMOKE_TRACE_CAPTURE_V12_10_48.json",
  "report_md": "/home/pmwens/Projects/SOCMINT-PROJECT/release/full_db_smoke_trace/FULL_DB_SMOKE_TRACE_CAPTURE_V12_10_48.md",
  "schema_mutation": "temp_sqlite_only",
  "upgrade_returncode": 0,
  "version": "12.10.48"
}
[+] v12.10.50 downgrade symmetry repair complete
[+] repair_status: GO
[+] smoke_status: NO-GO
[+] gate_release_status: HOLD
[+] lingering_after_downgrade: 16
[+] missing_after_upgrade: 0
[+] latest_exception: None
`
- **FAIL** `make_test121049` — `bash scripts/test_v12_10_49.sh
.F                                                                       [100%]
=================================== FAILURES ===================================
_______________________ test_collision_guard_runs_safely _______________________

    def test_collision_guard_runs_safely():
        result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr
    
        report = Path("release/existing_table_collision_guard/EXISTING_TABLE_COLLISION_GUARD_V12_10_49.json")
        assert report.exists()
    
        data = json.loads(report.read_text())
        assert data["schema_mutation"] == "none"
        assert data["production_db_touched"] is False
        assert data["real_config_upgrade_run"] is False
        assert data["guard_status"] == "GO"
>       assert "spine_connector_runs" in data["collision_tables"]
E       AssertionError: assert 'spine_connector_runs' in []

tests/test_v12_10_49_existing_table_collision_guard.py:38: AssertionError
=========================== short test summary info ============================
FAILED tests/test_v12_10_49_existing_table_collision_guard.py::test_collision_guard_runs_safely
1 failed, 1 passed in 1.82s
make: *** [Makefile:1015: test121049] Error 1
`

## Errors

- make_test121049: bash scripts/test_v12_10_49.sh
.F                                                                       [100%]
=================================== FAILURES ===================================
_______________________ test_collision_guard_runs_safely _______________________

    def test_collision_guard_runs_safely():
        result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr
    
        report = Path("release/existing_table_collision_guard/EXISTING_TABLE_COLLISION_GUARD_V12_10_49.json")
        assert report.exists()
    
        data = json.loads(report.read_text())
        assert data["schema_mutation"] == "none"
        assert data["production_db_touched"] is False
        assert data["real_config_upgrade_run"] is False
        assert data["guard_status"] == "GO"
>       assert "spine_connector_runs" in data["collision_tables"]
E       AssertionError: assert 'spine_connector_runs' in []

tests/test_v12_10_49_existing_table_collision_guard.py:38: AssertionError
=========================== short test summary info ============================
FAILED tests/test_v12_10_49_existing_table_collision_guard.py::test_collision_guard_runs_safely
1 failed, 1 passed in 1.82s
make: *** [Makefile:1015: test121049] Error 1


## Next action

fix failed readiness checks
# v12.10.54G Runtime App Discovery Report

- **status**: `GO`
- **verification_mode**: `isolated_probe`
- **endpoint_count**: `5`
- **expected_endpoint_count**: `5`
- **production_db_touched**: `False`
- **real_config_upgrade_run**: `False`
- **trace_file**: `/home/pmwens/Projects/SOCMINT-PROJECT/release/v12_10_54G/RUNTIME_APP_DISCOVERY_TRACE_V12_10_54G.txt`

## Endpoint results

- `/api/version`: `200`
- `/api/schema/status`: `200`
- `/api/schema/upgrade-guard`: `200`
- `/api/release/archive-integrity`: `200`
- `/api/schema/rollback/0018`: `200`

## Errors

- none

## Warnings

- dashboard runtime discovery failed; using isolated route probe fallback

## Tracebacks

```text
dashboard_runtime failed:
Traceback (most recent call last):
  File "/home/pmwens/Projects/SOCMINT-PROJECT/scripts/runtime_app_discovery_report_v12_10_54D.py", line 44, in get_dashboard_app
    return get_hardened_dashboard_app(), "dashboard_runtime", traces
           ~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/home/pmwens/Projects/SOCMINT-PROJECT/src/socmint/v12_10_54_app_adapter.py", line 51, in get_hardened_dashboard_app
    app = discover_dashboard_app()
  File "/home/pmwens/Projects/SOCMINT-PROJECT/src/socmint/v12_10_54_app_adapter.py", line 31, in discover_dashboard_app
    obj = factory()
  File "/home/pmwens/Projects/SOCMINT-PROJECT/src/socmint/dashboard.py", line 7017, in create_app
    app = _socmint_create_app_before_v12_10_31B(*args, **kwargs)
  File "/home/pmwens/Projects/SOCMINT-PROJECT/src/socmint/dashboard.py", line 6986, in create_app
    app = _socmint_original_create_app_v12_10_29(*args, **kwargs)
  File "/home/pmwens/Projects/SOCMINT-PROJECT/src/socmint/dashboard.py", line 2322, in create_app
    db.configure_database(settings.database_url, create_schema=settings.auto_create_db)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pmwens/Projects/SOCMINT-PROJECT/src/socmint/database.py", line 199, in configure_database
    engine = get_engine(database_url)
  File "/home/pmwens/Projects/SOCMINT-PROJECT/src/socmint/database.py", line 189, in get_engine
    os.makedirs(os.path.dirname(os.path.abspath(sqlite_path)), exist_ok=True)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen os>", line 228, in makedirs
PermissionError: [Errno 13] Permission denied: '/var/lib/socmint'

```
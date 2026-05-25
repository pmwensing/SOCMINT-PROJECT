# v12.10.55 Real Runtime Route Mount Report

- **status**: `GO`
- **selected_runtime**: `src.socmint.dashboard:create_app()`
- **verification_mode**: `real_runtime`
- **route_count**: `295`
- **v12_10_54_route_count**: `5`
- **production_db_touched**: `False`
- **real_config_upgrade_run**: `False`

## v12.10.54 routes mounted

- `/api/release/archive-integrity`
- `/api/schema/rollback/0018`
- `/api/schema/status`
- `/api/schema/upgrade-guard`
- `/api/version`

## Endpoint verification

- `/api/version`: `200`
- `/api/schema/status`: `200`
- `/api/schema/upgrade-guard`: `200`
- `/api/release/archive-integrity`: `200`
- `/api/schema/rollback/0018`: `200`

## Errors

- none

## Discovery attempts

- `src.socmint.dashboard:app` app_attr ok=False error=not a Flask app-like object
- `src.socmint.dashboard:application` app_attr ok=False error=not a Flask app-like object
- `src.socmint.dashboard:create_app` factory ok=True error=None
- `src.socmint.dashboard:make_app` factory ok=False error=not callable or missing
- `src.socmint.dashboard:get_app` factory ok=False error=not callable or missing
- `src.socmint.dashboard:build_app` factory ok=False error=not callable or missing
- `socmint.dashboard:app` app_attr ok=False error=not a Flask app-like object
- `socmint.dashboard:application` app_attr ok=False error=not a Flask app-like object
- `socmint.dashboard:create_app` factory ok=True error=None
- `socmint.dashboard:make_app` factory ok=False error=not callable or missing
- `socmint.dashboard:get_app` factory ok=False error=not callable or missing
- `socmint.dashboard:build_app` factory ok=False error=not callable or missing
- `src.socmint.app:src.socmint.app` module_import ok=False error=ModuleNotFoundError("No module named 'src.socmint.app'")
- `socmint.app:socmint.app` module_import ok=False error=ModuleNotFoundError("No module named 'socmint.app'")
- `src.socmint.main:app` app_attr ok=False error=not a Flask app-like object
- `src.socmint.main:application` app_attr ok=False error=not a Flask app-like object
- `src.socmint.main:create_app` factory ok=True error=None
- `src.socmint.main:make_app` factory ok=False error=not callable or missing
- `src.socmint.main:get_app` factory ok=False error=not callable or missing
- `src.socmint.main:build_app` factory ok=False error=not callable or missing
- `socmint.main:app` app_attr ok=False error=not a Flask app-like object
- `socmint.main:application` app_attr ok=False error=not a Flask app-like object
- `socmint.main:create_app` factory ok=True error=None
- `socmint.main:make_app` factory ok=False error=not callable or missing
- `socmint.main:get_app` factory ok=False error=not callable or missing
- `socmint.main:build_app` factory ok=False error=not callable or missing
- `src.socmint.wsgi:app` app_attr ok=True error=None
- `src.socmint.wsgi:application` app_attr ok=True error=None
- `src.socmint.wsgi:create_app` factory ok=True error=None
- `src.socmint.wsgi:make_app` factory ok=False error=not callable or missing
- `src.socmint.wsgi:get_app` factory ok=False error=not callable or missing
- `src.socmint.wsgi:build_app` factory ok=False error=not callable or missing
- `socmint.wsgi:app` app_attr ok=True error=None
- `socmint.wsgi:application` app_attr ok=True error=None
- `socmint.wsgi:create_app` factory ok=True error=None
- `socmint.wsgi:make_app` factory ok=False error=not callable or missing
- `socmint.wsgi:get_app` factory ok=False error=not callable or missing
- `socmint.wsgi:build_app` factory ok=False error=not callable or missing
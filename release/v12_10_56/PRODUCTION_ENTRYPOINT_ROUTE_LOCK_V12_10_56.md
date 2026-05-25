# v12.10.56A Production Entrypoint Route Lock

- **status**: `GO`
- **verification_mode**: `production_entrypoint`
- **selected_spec**: `src.socmint.wsgi:app`
- **selected_wsgi_mode**: `wsgi_guard_minimal`
- **selected_wsgi_source**: `dashboard_app_not_found`
- **production_db_touched**: `False`
- **real_config_upgrade_run**: `False`

## Selected v12.10.54 routes

- `/api/release/archive-integrity`
- `/api/schema/rollback/0018`
- `/api/schema/status`
- `/api/schema/upgrade-guard`
- `/api/version`

## Endpoint results

- `/api/release/archive-integrity`: `200`
- `/api/schema/rollback/0018`: `200`
- `/api/schema/status`: `200`
- `/api/schema/upgrade-guard`: `200`
- `/api/version`: `200`

## Errors

- none

## Warnings

- production WSGI shim used minimal guard app because dashboard runtime app was not discoverable

## Entrypoint attempts

- `src.socmint.wsgi:app` loaded=True verification_ok=True wsgi_mode=wsgi_guard_minimal source=dashboard_app_not_found error=None
- `src.socmint.wsgi:application` loaded=True verification_ok=True wsgi_mode=wsgi_guard_minimal source=dashboard_app_not_found error=None
- `src.socmint.wsgi:create_app` loaded=True verification_ok=True wsgi_mode=wsgi_guard_minimal source=dashboard_app_not_found error=None
- `src.socmint.dashboard:app` loaded=False verification_ok=None wsgi_mode=None source=None error=src.socmint.dashboard:app is not Flask-like and not callable factory
- `src.socmint.dashboard:create_app` loaded=False verification_ok=None wsgi_mode=None source=None error=factory src.socmint.dashboard:create_app failed: PermissionError(13, 'Permission denied')
- `src.socmint.dashboard:application` loaded=False verification_ok=None wsgi_mode=None source=None error=src.socmint.dashboard:application is not Flask-like and not callable factory
- `socmint.dashboard:app` loaded=False verification_ok=None wsgi_mode=None source=None error=socmint.dashboard:app is not Flask-like and not callable factory
- `socmint.dashboard:create_app` loaded=False verification_ok=None wsgi_mode=None source=None error=factory socmint.dashboard:create_app failed: PermissionError(13, 'Permission denied')
- `socmint.dashboard:application` loaded=False verification_ok=None wsgi_mode=None source=None error=socmint.dashboard:application is not Flask-like and not callable factory

## Runtime lines

### `Dockerfile`
- `HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/readyz', timeout=3).read()"`
- `CMD ["gunicorn", "--bind", "127.0.0.1:5000", "src.socmint.wsgi:app"]`
### `docker-compose.yml`
- `GUNICORN_TIMEOUT: ${GUNICORN_TIMEOUT:-180}`
- `command: sh -c "alembic upgrade head && exec gunicorn --timeout $${GUNICORN_TIMEOUT:-180} --bind 0.0.0.0:5000 src.socmint.wsgi:app"`
- `test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/readyz', timeout=3).read()"]`
- `command: >`
### `Makefile`
- `./venv/bin/gunicorn --bind 127.0.0.1:5000 src.socmint.wsgi:app`
- `@echo 'Production entrypoint: release/v12_10_56/PRODUCTION_ENTRYPOINT_ROUTE_LOCK_V12_10_56.md'`
- `@echo 'Production entrypoint: release/v12_10_56/PRODUCTION_ENTRYPOINT_ROUTE_LOCK_V12_10_56.md'`
- `@echo 'Production entrypoint: release/v12_10_56/PRODUCTION_ENTRYPOINT_ROUTE_LOCK_V12_10_56.md'`
### `pyproject.toml`
- `"flask",`
- `"flask-cors",`
- `"flask-sqlalchemy",`
- `"flask-httpauth",`
- `"gunicorn",`
### `src/socmint/wsgi.py`
- `from flask import Flask`
- `def _looks_like_flask_app(obj):`
- `if _looks_like_flask_app(obj):`
- `if _looks_like_flask_app(obj):`
- `"""Production WSGI app entrypoint.`
- `app = Flask("socmint_wsgi_guard_runtime")`
- `app.config["SOCMINT_WSGI_MODE"] = "wsgi_guard_minimal"`
- `app.config["SOCMINT_WSGI_SOURCE"] = source`
- `app.config["SOCMINT_WSGI_MODE"] = "dashboard_runtime"`
- `app.config["SOCMINT_WSGI_SOURCE"] = source`
### `src/socmint/dashboard.py`
- `from flask import (`
- `Flask,`
- `app = Flask(__name__, template_folder="templates", static_folder="static")`
- `from flask import send_file`
- `from flask import send_file`
- `from flask import send_file`
- `# are registered on the actual runtime Flask app returned by create_app().`
- `# v12.10 Command Center blueprints are registered on the actual Flask app`
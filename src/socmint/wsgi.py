from __future__ import annotations

from flask import Flask


def _looks_like_flask_app(obj):
    return hasattr(obj, "test_client") and hasattr(obj, "url_map") and hasattr(obj, "register_blueprint")


def _load_dashboard_app():
    """Best-effort discovery of the existing dashboard runtime app."""
    try:
        from . import dashboard
    except Exception:
        return None, "dashboard_import_failed"

    for name in ("app", "application"):
        obj = getattr(dashboard, name, None)
        if _looks_like_flask_app(obj):
            return obj, f"dashboard.{name}"

    for name in ("create_app", "make_app", "get_app", "build_app"):
        factory = getattr(dashboard, name, None)
        if not callable(factory):
            continue
        try:
            obj = factory()
        except TypeError:
            continue
        except Exception:
            continue
        if _looks_like_flask_app(obj):
            return obj, f"dashboard.{name}()"

    return None, "dashboard_app_not_found"


def create_app():
    """Production WSGI app entrypoint.

    This function intentionally does not run Alembic or any DB upgrade. It only
    mounts runtime guard/status routes needed after v12.10.53.
    """
    app, source = _load_dashboard_app()

    if app is None:
        app = Flask("socmint_wsgi_guard_runtime")
        app.config["SOCMINT_WSGI_MODE"] = "wsgi_guard_minimal"
        app.config["SOCMINT_WSGI_SOURCE"] = source
    else:
        app.config["SOCMINT_WSGI_MODE"] = "dashboard_runtime"
        app.config["SOCMINT_WSGI_SOURCE"] = source

    from .v12_10_54_runtime_guard_routes import register_v12_10_54_routes

    register_v12_10_54_routes(app)
    return app


app = create_app()
application = app

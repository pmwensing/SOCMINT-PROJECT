from __future__ import annotations

from typing import Any, Callable


def _looks_like_flask_app(obj: Any) -> bool:
    return hasattr(obj, "test_client") and hasattr(obj, "url_map")


def discover_dashboard_app() -> Any:
    """Return the runtime Flask app without assuming a module-level `app`.

    Discovery order:
    1. dashboard.app
    2. dashboard.application
    3. dashboard.create_app()
    4. dashboard.make_app()
    5. dashboard.get_app()
    """
    from . import dashboard

    for name in ("app", "application"):
        obj = getattr(dashboard, name, None)
        if _looks_like_flask_app(obj):
            return obj

    for name in ("create_app", "make_app", "get_app"):
        factory = getattr(dashboard, name, None)
        if callable(factory):
            try:
                obj = factory()
            except TypeError:
                continue
            if _looks_like_flask_app(obj):
                return obj

    raise RuntimeError(
        "Could not discover Flask app from src.socmint.dashboard. "
        "Expected app/application or create_app()/make_app()/get_app()."
    )


def ensure_v12_10_54_routes(app: Any) -> Any:
    from .v12_10_54_runtime_guard_routes import register_v12_10_54_routes

    register_v12_10_54_routes(app)
    return app


def get_hardened_dashboard_app() -> Any:
    app = discover_dashboard_app()
    return ensure_v12_10_54_routes(app)

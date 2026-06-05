from __future__ import annotations

from typing import Any

from werkzeug.exceptions import MethodNotAllowed, NotFound

from . import support_bundle_v13_34 as support_bundle


def route_health_summary_with_dynamic_paths(app) -> list[dict[str, Any]]:
    """Resolve concrete smoke-test paths against Flask's URL map.

    The support bundle displays operator-facing concrete paths such as
    /spine/subjects/4/dossier. Flask stores those routes using variable rules
    such as /spine/subjects/<int:subject_id>/dossier, so exact string lookup
    marks healthy dynamic routes as missing. URL-map matching fixes that without
    making live HTTP requests or bypassing login protection.
    """
    adapter = app.url_map.bind("")
    results: list[dict[str, Any]] = []

    for route in support_bundle.SUPPORT_BUNDLE_ROUTES:
        endpoint = None
        registered = False
        status = "missing"

        try:
            endpoint, _values = adapter.match(route, method="GET")
            registered = True
            status = "registered"
        except MethodNotAllowed as exc:
            registered = True
            endpoint = ",".join(sorted(exc.valid_methods or []))
            status = "registered_method_mismatch"
        except NotFound:
            status = "missing"

        results.append(
            {
                "route": route,
                "registered": registered,
                "endpoint": endpoint,
                "status": status,
            }
        )

    return results


def install_support_bundle_route_health_fix_v13_34() -> None:
    support_bundle.route_health_summary = route_health_summary_with_dynamic_paths

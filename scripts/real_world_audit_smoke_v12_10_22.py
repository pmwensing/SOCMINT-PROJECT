#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

from socmint.build_audit_routes import register_build_audit_routes
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.real_world_audit import build_real_world_audit
from socmint.real_world_audit import register_real_world_audit_routes
from socmint.scope_lock_routes import register_scope_lock_routes


def main() -> int:
    app = create_app()
    register_full_report_aliases(app)
    register_scope_lock_routes(app)
    register_build_audit_routes(app)
    register_real_world_audit_routes(app)

    payload = build_real_world_audit(app)
    required = [
        "schema",
        "readiness",
        "capability_score",
        "what_works",
        "what_does_not",
        "value_assessment",
        "build_plan",
        "drift_summary",
        "audit_summary",
    ]
    missing = [key for key in required if key not in payload]
    route_rules = {rule.rule for rule in app.url_map.iter_rules()}
    route_missing = [
        route
        for route in [
            "/api/v1/workbench/real-world-audit",
            "/workbench/real-world-audit",
        ]
        if route not in route_rules
    ]

    result = {
        "status": "pass" if not missing and not route_missing else "fail",
        "schema": payload.get("schema"),
        "readiness": payload.get("readiness"),
        "capability_score": payload.get("capability_score"),
        "missing_payload_keys": missing,
        "missing_routes": route_missing,
        "build_plan_phases": [
            item.get("phase") for item in payload.get("build_plan", [])
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

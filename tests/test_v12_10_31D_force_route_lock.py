from pathlib import Path
import importlib.util
import sys


def load_auditor():
    p = Path("scripts/drift_lock_audit_v12_10_31A.py")
    assert p.exists()
    spec = importlib.util.spec_from_file_location("drift_lock_31D", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_force_route_lock_eliminates_missing_routes():
    mod = load_auditor()
    result = mod.runtime_flask_routes()

    assert result["attempted"] is True
    assert result["dashboard_module_file"].endswith("src/socmint/dashboard.py")
    assert result["missing_v12_routes"] == []
    assert result["ok"] is True

    routes = set(result["routes_after_lock"])
    for route in mod.EXPECTED_V12_ROUTES:
        assert route in routes


def test_force_route_lock_reports_diagnostics():
    mod = load_auditor()
    result = mod.runtime_flask_routes()

    assert "route_lock" in result
    assert isinstance(result["route_lock"].get("registered", []), list)
    assert isinstance(result["route_lock"].get("skipped", []), list)
    assert isinstance(result["route_lock"].get("errors", []), list)

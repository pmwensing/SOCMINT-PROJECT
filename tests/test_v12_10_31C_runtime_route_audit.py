from pathlib import Path
import importlib.util
import sys


def load_auditor():
    p = Path("scripts/drift_lock_audit_v12_10_31A.py")
    assert p.exists()
    spec = importlib.util.spec_from_file_location("drift_lock_31C", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_runtime_route_audit_reports_dashboard_file_and_routes():
    mod = load_auditor()
    result = mod.runtime_flask_routes()

    assert result["attempted"] is True
    assert result["dashboard_module_file"]
    assert result["dashboard_module_file"].endswith("src/socmint/dashboard.py")
    assert result["ok"] is True
    assert result["missing_v12_routes"] == []

    routes = set(result["routes"])
    assert "/api/v12.10/dossier/run/<case_id>" in routes
    assert "/api/v12.10/ui/command-center" in routes


def test_route_lock_diagnostic_fields_exist():
    mod = load_auditor()
    result = mod.runtime_flask_routes()

    assert "routes_before_lock" in result
    assert "routes_after_lock" in result
    assert "missing_v12_routes_before_lock" in result
    assert "route_lock" in result

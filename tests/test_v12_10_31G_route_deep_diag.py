from pathlib import Path
import importlib.util
import sys


def load_auditor():
    p = Path("scripts/drift_lock_audit_v12_10_31A.py")
    assert p.exists()
    spec = importlib.util.spec_from_file_location("drift_lock_31G", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_route_snapshot_contains_endpoint_suffixes():
    mod = load_auditor()
    result = mod.runtime_v12_route_smoke()

    assert result["dashboard_module_file"].endswith("src/socmint/dashboard.py")
    assert "v12_like_rules_after_lock" in result
    assert "v12_like_endpoints_after_lock" in result
    assert "missing_v12_endpoint_suffixes" in result
    assert result["ok"] is True
    assert result["missing_v12_route_count"] == 0


def test_expected_endpoint_suffixes_present():
    mod = load_auditor()
    result = mod.runtime_v12_route_smoke()
    endpoints = set(e.rsplit(".", 1)[-1] for e in result["endpoints_after_lock"])

    for suffix in mod.EXPECTED_V12_ENDPOINT_SUFFIXES:
        assert suffix in endpoints

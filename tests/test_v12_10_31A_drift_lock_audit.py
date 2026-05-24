from pathlib import Path
import importlib.util
import json


def load_module():
    p = Path("scripts/drift_lock_audit_v12_10_31A.py")
    assert p.exists()
    spec = importlib.util.spec_from_file_location("drift_lock", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_drift_lock_module_loads():
    mod = load_module()
    assert hasattr(mod, "detect_framework")
    assert hasattr(mod, "alembic_info")
    assert hasattr(mod, "compare_models_migrations")
    assert hasattr(mod, "runtime_flask_routes")


def test_expected_v12_routes_declared():
    mod = load_module()
    assert "/api/v12.10/dossier/run/<case_id>" in mod.EXPECTED_V12_ROUTES
    assert "/api/v12.10/ui/command-center" in mod.EXPECTED_V12_ROUTES


def test_release_doc_exists():
    assert Path("release/V12_10_31A_DRIFT_LOCK_AUDIT.md").exists()

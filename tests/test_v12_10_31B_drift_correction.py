from pathlib import Path
import importlib.util
import sys


def load_auditor():
    p = Path("scripts/drift_lock_audit_v12_10_31A.py")
    assert p.exists()
    spec = importlib.util.spec_from_file_location("drift_lock_31B", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_auditor_does_not_pick_itself_as_primary_entrypoint():
    mod = load_auditor()
    info = mod.identify_entrypoints()
    primary = info["primary_guess"]
    assert primary is not None
    assert primary["path"] != "scripts/drift_lock_audit_v12_10_31A.py"
    assert primary["path"].startswith("src/")


def test_runtime_routes_are_locked_on_flask_app():
    mod = load_auditor()
    result = mod.runtime_flask_routes()
    assert result["ok"] is True
    assert result["missing_v12_routes"] == []


def test_active_version_metadata_consistent():
    mod = load_auditor()
    versions = mod.version_metadata()
    assert versions["metadata_consistent"] is True

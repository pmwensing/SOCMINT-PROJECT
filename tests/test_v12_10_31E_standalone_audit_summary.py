from pathlib import Path
import importlib.util
import json
import subprocess
import sys


def load_auditor():
    p = Path("scripts/drift_lock_audit_v12_10_31A.py")
    assert p.exists()
    spec = importlib.util.spec_from_file_location("drift_lock_31E", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_runtime_v12_route_smoke_is_source_of_truth():
    mod = load_auditor()
    result = mod.runtime_v12_route_smoke()

    assert result["ok"] is True
    assert result["missing_v12_route_count"] == 0
    assert result["missing_v12_routes"] == []
    assert result["dashboard_module_file"].endswith("src/socmint/dashboard.py")


def test_standalone_report_uses_route_smoke_summary():
    subprocess.run(
        [sys.executable, "scripts/drift_lock_audit_v12_10_31A.py"],
        check=False,
    )

    p = Path("release/drift_lock/DRIFT_LOCK_AUDIT_V12_10_31E.json")
    assert p.exists()

    data = json.loads(p.read_text())
    summary = data["summary"]

    assert summary["primary_entrypoint"] == "src/socmint/dashboard.py"
    assert summary["missing_v12_routes"] == 0
    assert summary["version_unique_count"] == 1
    assert summary["alembic_heads"] == "0017_v12_10_schema_reconciliation"

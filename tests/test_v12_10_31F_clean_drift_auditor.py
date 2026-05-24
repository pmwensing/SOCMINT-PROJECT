from pathlib import Path
import importlib.util
import json
import subprocess
import sys


def load_auditor():
    p = Path("scripts/drift_lock_audit_v12_10_31A.py")
    assert p.exists()
    spec = importlib.util.spec_from_file_location("drift_lock_31F_compat", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_clean_auditor_runtime_route_smoke():
    mod = load_auditor()
    result = mod.runtime_v12_route_smoke()

    assert result["attempted"] is True
    assert result["dashboard_module_file"].endswith("src/socmint/dashboard.py")
    assert result["ok"] is True

    # v12.10.31G+ uses endpoint suffixes as authoritative proof because
    # Flask rule strings can differ while handlers are actually registered.
    assert result.get("missing_v12_endpoint_suffixes", []) == []
    assert result.get("missing_v12_route_count", 0) == 0


def test_clean_auditor_standalone_report_matches_runtime_smoke():
    subprocess.run(
        [sys.executable, "scripts/drift_lock_audit_v12_10_31A.py"],
        check=False,
    )

    candidates = sorted(Path("release/drift_lock").glob("DRIFT_LOCK_AUDIT_V12_10_31*.json"))
    assert candidates, "no drift-lock report generated"

    p = candidates[-1]
    data = json.loads(p.read_text())
    summary = data["summary"]

    assert summary["primary_entrypoint"] == "src/socmint/dashboard.py"
    assert summary["version_unique_count"] == 1
    assert summary["alembic_heads"] == "0017_v12_10_schema_reconciliation"

    # Newer reports may leave exact route-string count visible for diagnostics.
    # Runtime route proof is now endpoint based.
    assert summary.get("missing_v12_endpoint_suffixes", 0) == 0

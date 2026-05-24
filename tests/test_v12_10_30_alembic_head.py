from pathlib import Path
import configparser
import importlib.util
import subprocess


def active_migration():
    cfg = configparser.ConfigParser()
    cfg.read("alembic.ini")
    loc = cfg.get("alembic", "script_location", fallback="alembic")
    return Path(loc) / "versions" / "0017_v12_10_schema_reconciliation.py"


def load_migration():
    p = active_migration()
    assert p.exists(), f"missing active migration at {p}"
    spec = importlib.util.spec_from_file_location("mig0017", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return p, mod


def test_0017_is_active_alembic_migration():
    _, mod = load_migration()
    assert mod.revision == "0017_v12_10_schema_reconciliation"
    assert isinstance(mod.down_revision, str)
    assert len(mod.down_revision) > 0


def test_0017_is_sole_alembic_head():
    out = subprocess.check_output(["alembic", "heads"], text=True)
    heads = [line.split()[0] for line in out.splitlines() if line.strip()]
    assert heads == ["0017_v12_10_schema_reconciliation"]


def test_0017_contains_required_v12_tables():
    p, _ = load_migration()
    text = p.read_text()
    for table in [
        "dossier_exports",
        "evidence_hash_events",
        "intel_runs",
        "analyst_decisions",
        "strategic_risk_scores",
        "continuous_monitoring_events",
    ]:
        assert table in text

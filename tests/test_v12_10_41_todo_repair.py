from pathlib import Path
import configparser
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/repair_0018_todo_placeholders_v12_10_41.py")


def active_promoted_path() -> Path:
    cfg = configparser.ConfigParser()
    cfg.read("alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="alembic")
    return Path(script_location) / "versions" / "0018_approved_model_migration.py"


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("repair_v12_10_41", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "repair_text")
    assert hasattr(mod, "executable_todo_lines")


def test_repair_removes_executable_todo_without_real_db_upgrade():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/db_smoke_repair/TODO_PLACEHOLDER_REPAIR_V12_10_41.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "none"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["repair_status"] == "GO"
    assert data["remaining_executable_todo"] == []

    promoted = active_promoted_path()
    assert promoted.exists()

    text = promoted.read_text()
    for line in text.splitlines():
        before_comment = line.split("#", 1)[0]
        assert "TODO" not in before_comment

    subprocess.run([sys.executable, "-m", "py_compile", str(promoted)], check=True)


def test_alembic_still_sees_0018_head():
    result = subprocess.run(["alembic", "heads"], text=True, capture_output=True)
    assert result.returncode == 0
    assert "0018_approved_model_migration" in result.stdout

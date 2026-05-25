from pathlib import Path
import importlib.util
import subprocess
import sys
import json


SCRIPT = Path("scripts/repair_blocked_identity_tables_v12_10_45B.py")


def load_module():
    spec = importlib.util.spec_from_file_location("repair45b", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_multiline_create_table_block_finder():
    mod = load_module()
    lines = [
        "def upgrade():",
        "    op.create_table(",
        '        "identity_columns",',
        '        sa.Column("id", sa.String(255)),',
        "    )",
    ]
    start, end = mod.find_create_table_block(lines, "identity_columns")
    assert start == 1
    assert end == 4


def test_one_line_create_table_block_finder_still_works():
    mod = load_module()
    lines = [
        "def upgrade():",
        '    op.create_table("identity_columns",',
        '        sa.Column("id", sa.String(255)),',
        "    )",
    ]
    start, end = mod.find_create_table_block(lines, "identity_columns")
    assert start == 1
    assert end == 3


def test_45b_repair_now_finds_identity_blocks_safely():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/blocked_identity_table_repair/BLOCKED_IDENTITY_TABLE_REPAIR_V12_10_45B.json")
    data = json.loads(report.read_text())

    assert data["schema_mutation"] == "none"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["found_tables"]["all_tab_identity_cols"] is True
    assert data["found_tables"]["identity_columns"] is True
    assert data["repair_status"] == "GO"

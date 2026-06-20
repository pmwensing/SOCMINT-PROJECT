import ast
from pathlib import Path


def test_v26_7_release_note_and_no_migration():
    note = Path("release/V26_7_PRODUCT_REVIEW_BROWSER_E2E_CHECKPOINT.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "complete collaboration journey",
        "browser E2E",
        "case access scope",
        "append-only",
        "Mentions do not grant access",
        "acknowledgement does not equal completion",
        "v26_closed",
        "begin_v27",
        "no migration",
    ):
        assert phrase in note
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v26_7*")
    ]
    assert migrations == []


def test_v26_7_browser_runner_has_stable_secret_and_driver_discovery():
    path = Path("scripts/run_v26_7_collaboration_browser_e2e.py")
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    secrets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if any(
                isinstance(target, ast.Subscript)
                and isinstance(target.slice, ast.Constant)
                and target.slice.value == "SOCMINT_SECRET_KEY"
                for target in node.targets
            ):
                secrets.append(str(node.value.value))
    assert secrets and all(len(value) >= 32 for value in secrets)
    for phrase in (
        "SOCMINT_CHROME_BINARY",
        "SOCMINT_CHROMEDRIVER",
        "chromium",
        "chromedriver",
        "ChromeService",
    ):
        assert phrase in text

import ast
from pathlib import Path


def test_v27_7_browser_e2e_uses_valid_secret_length():
    source = Path("scripts/run_v27_7_search_reporting_browser_e2e.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    values = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Subscript) or not isinstance(target.value, ast.Attribute):
                continue
            if not (isinstance(target.value.value, ast.Name) and target.value.value.id == "os" and target.value.attr == "environ"):
                continue
            key = ast.literal_eval(target.slice)
            if key == "SOCMINT_SECRET_KEY":
                values.append(ast.literal_eval(node.value))
    assert values
    assert all(isinstance(value, str) and len(value) >= 32 for value in values)


def test_v27_7_browser_e2e_discovers_local_chromium_and_driver():
    source = Path("scripts/run_v27_7_search_reporting_browser_e2e.py").read_text(encoding="utf-8")
    for phrase in (
        "SOCMINT_CHROME_BINARY", "SOCMINT_CHROMEDRIVER",
        'shutil.which("chromium")', 'shutil.which("chromium-browser")',
        'shutil.which("google-chrome")', 'shutil.which("chromedriver")',
        "options.binary_location = binary", "ChromeService(executable_path=executable)",
    ):
        assert phrase in source

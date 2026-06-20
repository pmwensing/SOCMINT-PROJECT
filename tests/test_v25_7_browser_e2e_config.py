import ast
from pathlib import Path


def test_v25_7_browser_e2e_uses_valid_secret_length():
    source = Path("scripts/run_v25_7_cross_case_browser_e2e.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    values = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Subscript):
                continue
            if not isinstance(target.value, ast.Attribute):
                continue
            if not (
                isinstance(target.value.value, ast.Name)
                and target.value.value.id == "os"
                and target.value.attr == "environ"
            ):
                continue
            key = ast.literal_eval(target.slice)
            if key == "SOCMINT_SECRET_KEY":
                values.append(ast.literal_eval(node.value))

    assert values
    assert all(isinstance(value, str) and len(value) >= 32 for value in values)


def test_v25_7_browser_e2e_discovers_local_chromium_and_driver():
    source = Path("scripts/run_v25_7_cross_case_browser_e2e.py").read_text(encoding="utf-8")

    assert "SOCMINT_CHROME_BINARY" in source
    assert "SOCMINT_CHROMEDRIVER" in source
    for executable in ("chromium", "chromium-browser", "google-chrome", "chromedriver"):
        double_quoted = f'shutil.which("{executable}")'
        single_quoted = f"shutil.which('{executable}')"
        assert double_quoted in source or single_quoted in source
    assert "options.binary_location = chromium" in source
    assert "ChromeService(driver_path) if driver_path else None" in source

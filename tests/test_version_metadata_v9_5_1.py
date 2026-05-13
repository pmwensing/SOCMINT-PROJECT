from importlib import metadata
from pathlib import Path
import re

import src.socmint as socmint


EXPECTED_VERSION = "10.1.2"


def _pyproject_text() -> str:
    return Path("pyproject.toml").read_text(encoding="utf-8")


def test_module_version_metadata_is_synced():
    assert socmint.__version__ == EXPECTED_VERSION


def test_pyproject_version_metadata_is_synced():
    match = re.search(r'^version = "([^"]+)"', _pyproject_text(), re.MULTILINE)
    assert match
    assert match.group(1) == EXPECTED_VERSION


def test_installed_package_version_matches_expected_when_available():
    try:
        installed_version = metadata.version("socmint")
    except metadata.PackageNotFoundError:
        installed_version = EXPECTED_VERSION

    assert installed_version == EXPECTED_VERSION

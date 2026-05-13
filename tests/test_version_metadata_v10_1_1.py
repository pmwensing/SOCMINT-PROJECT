from pathlib import Path

import socmint

EXPECTED_VERSION = "10.1.1"


def test_package_version_is_10_1_1():
    assert socmint.__version__ == EXPECTED_VERSION


def test_pyproject_version_matches_package_version():
    pyproject = Path("pyproject.toml").read_text()
    assert f'version = "{EXPECTED_VERSION}"' in pyproject
    assert socmint.__version__ in pyproject


def test_v10_1_1_release_note_exists():
    release_note = Path("release/V10_1_1_VERSION_SYNC.md")
    assert release_note.exists()
    text = release_note.read_text()
    assert EXPECTED_VERSION in text
    assert "Version Metadata Sync" in text

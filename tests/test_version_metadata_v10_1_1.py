from pathlib import Path


def test_v10_1_1_release_note_exists():
    release_note = Path("release/V10_1_1_VERSION_SYNC.md")
    assert release_note.exists()
    text = release_note.read_text()
    assert "10.1.1" in text
    assert "Version Metadata Sync" in text

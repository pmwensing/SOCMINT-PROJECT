from pathlib import Path

from socmint.evidence_repo.hash_manifest import HashEntry, parse_manifest_line, write_manifest
from socmint.evidence_repo.location_map import EvidenceLocation, LocationType, validate_location, write_location_map


def test_parse_manifest_line():
    entry = parse_manifest_line("a" * 64 + "  /tmp/example.txt")
    assert entry == HashEntry("a" * 64, "/tmp/example.txt")


def test_parse_manifest_ignores_comments():
    assert parse_manifest_line("# comment") is None
    assert parse_manifest_line("") is None


def test_write_manifest(tmp_path: Path):
    output = tmp_path / "HASH_MANIFEST.sha256"
    write_manifest([HashEntry("b" * 64, "file.txt")], output)
    assert output.read_text(encoding="utf-8") == "{}  file.txt\n".format("b" * 64)


def test_validate_location_accepts_valid_entry():
    entry = EvidenceLocation(
        evidence_id="46M-20251126-FIRE-001-PHOTO",
        location_type=LocationType.LOCAL_PRIMARY,
        location_id="LOCAL-PRIMARY-001",
        path_or_file_id="E:/46_Montreal_Evidence/example.jpg",
        sha256="c" * 64,
        verified=True,
    )
    validate_location(entry)


def test_validate_location_rejects_bad_hash():
    entry = EvidenceLocation(
        evidence_id="46M-TEST",
        location_type=LocationType.CLOUD_PRIMARY_OR_BACKUP,
        location_id="CLOUD-GDRIVE-001",
        path_or_file_id="/46_Montreal_Evidence/example.pdf",
        sha256="not-a-hash",
    )
    try:
        validate_location(entry)
    except ValueError as exc:
        assert "sha256" in str(exc)
    else:
        raise AssertionError("Expected invalid hash to fail")


def test_write_location_map(tmp_path: Path):
    output = tmp_path / "EVIDENCE_LOCATION_MAP.csv"
    entry = EvidenceLocation(
        evidence_id="46M-TEST",
        location_type=LocationType.GITHUB_DERIVATIVE,
        location_id="GITHUB-PRIVATE-001",
        path_or_file_id="99_redacted_public/example.pdf",
        sha256="d" * 64,
        verified=False,
        notes="redacted copy",
    )
    write_location_map([entry], output)
    text = output.read_text(encoding="utf-8")
    assert "evidence_id,location_type,location_id" in text
    assert "46M-TEST" in text
    assert "github_derivative" in text

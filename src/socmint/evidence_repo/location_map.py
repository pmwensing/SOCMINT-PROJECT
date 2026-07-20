from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class LocationType(StrEnum):
    LOCAL_PRIMARY = "local_primary"
    LOCAL_EXTERNAL_BACKUP = "local_external_backup"
    CLOUD_PRIMARY_OR_BACKUP = "cloud_primary_or_backup"
    GITHUB_DERIVATIVE = "github_derivative"


@dataclass(frozen=True)
class EvidenceLocation:
    evidence_id: str
    location_type: LocationType
    location_id: str
    path_or_file_id: str
    sha256: str
    verified: bool = False
    notes: str = ""

    def to_csv_row(self) -> str:
        verified_text = "true" if self.verified else "false"
        values = (
            self.evidence_id,
            self.location_type.value,
            self.location_id,
            self.path_or_file_id,
            self.sha256,
            verified_text,
            self.notes,
        )
        return ",".join(_csv_escape(value) for value in values)


HEADER = "evidence_id,location_type,location_id,path_or_file_id,hash_sha256,verified,notes"


def _csv_escape(value: str) -> str:
    text = str(value)
    if any(char in text for char in [",", '"', "\n"]):
        return '"' + text.replace('"', '""') + '"'
    return text


def write_location_map(entries: list[EvidenceLocation], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        HEADER + "\n" + "".join(entry.to_csv_row() + "\n" for entry in entries),
        encoding="utf-8",
    )


def validate_location(entry: EvidenceLocation) -> None:
    if not entry.evidence_id:
        raise ValueError("evidence_id is required")
    if not entry.location_id:
        raise ValueError("location_id is required")
    if not entry.path_or_file_id:
        raise ValueError("path_or_file_id is required")
    if len(entry.sha256) != 64:
        raise ValueError("sha256 must be a 64-character hex digest")
    int(entry.sha256, 16)


def validate_locations(entries: list[EvidenceLocation]) -> None:
    for entry in entries:
        validate_location(entry)

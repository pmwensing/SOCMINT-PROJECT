from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HashEntry:
    sha256: str
    path: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path) -> list[Path]:
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Evidence root not found: {root}")
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
        and "node_modules" not in path.parts
    )


def build_manifest(root: Path) -> list[HashEntry]:
    return [HashEntry(sha256_file(path), path.as_posix()) for path in iter_files(root)]


def write_manifest(entries: list[HashEntry], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(f"{entry.sha256}  {entry.path}\n" for entry in entries),
        encoding="utf-8",
    )


def parse_manifest_line(line: str) -> HashEntry | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = stripped.split(None, 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid hash manifest line: {line!r}")
    return HashEntry(parts[0], parts[1].strip())


def read_manifest(path: Path) -> list[HashEntry]:
    return [
        entry
        for line in path.read_text(encoding="utf-8").splitlines()
        if (entry := parse_manifest_line(line)) is not None
    ]

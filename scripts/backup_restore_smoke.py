#!/usr/bin/env python3
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.socmint import database as db  # noqa: E402
from src.socmint.backup import create_backup, restore_backup  # noqa: E402


def main():
    if not shutil.which("openssl"):
        raise SystemExit("openssl is required for the encrypted backup smoke test")

    root = Path(os.getenv("SOCMINT_SMOKE_DIR", "/tmp/socmint-backup-smoke"))
    root.mkdir(parents=True, exist_ok=True)
    source_db = root / "source.db"
    restored_db = root / "restored.db"
    backup_path = root / "socmint.sqlite.enc"

    for path in (source_db, restored_db, backup_path):
        if path.exists():
            path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite:///{source_db}"
    os.environ["SOCMINT_DATA_DIR"] = str(root / "data")
    os.environ["SOCMINT_BACKUP_PASSPHRASE"] = os.getenv(
        "SOCMINT_BACKUP_PASSPHRASE", "BackupSmokePassphrase123!"
    )

    db.configure_database(f"sqlite:///{source_db}")
    db.save_dossier(
        {
            "target": "backup_smoke_operator",
            "type": "username",
            "data": {"smoke": {"ok": True}},
        }
    )
    create_backup(backup_path, encrypt=True)
    restore_backup(
        backup_path,
        destination_database_url=f"sqlite:///{restored_db}",
        encrypted=True,
    )

    db.configure_database(f"sqlite:///{restored_db}")
    dossier = db.get_dossier("backup_smoke_operator")
    if not dossier or dossier["data"]["smoke"]["ok"] is not True:
        raise SystemExit("restored dossier did not match the source dossier")

    print(f"Encrypted backup restore smoke passed: {backup_path}")


if __name__ == "__main__":
    main()

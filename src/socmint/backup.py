import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from .config import load_settings


def is_sqlite(database_url):
    return database_url.startswith("sqlite:///")


def sqlite_path(database_url):
    return database_url.replace("sqlite:///", "", 1)


def encrypt_file(source_path, output_path, passphrase):
    subprocess.run(
        [
            "openssl",
            "enc",
            "-aes-256-cbc",
            "-salt",
            "-pbkdf2",
            "-in",
            str(source_path),
            "-out",
            str(output_path),
            "-pass",
            f"pass:{passphrase}",
        ],
        check=True,
    )


def decrypt_file(source_path, output_path, passphrase):
    subprocess.run(
        [
            "openssl",
            "enc",
            "-d",
            "-aes-256-cbc",
            "-pbkdf2",
            "-in",
            str(source_path),
            "-out",
            str(output_path),
            "-pass",
            f"pass:{passphrase}",
        ],
        check=True,
    )


def backup_sqlite(database_url, destination):
    source = sqlite_path(database_url)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_conn = sqlite3.connect(source)
    try:
        dest_conn = sqlite3.connect(destination)
        try:
            source_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        source_conn.close()
    return destination


def backup_postgres(database_url, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "wb") as output:
        subprocess.run(["pg_dump", database_url], stdout=output, check=True)
    return destination


def create_backup(destination, encrypt=True):
    settings = load_settings(require_secret=False)
    destination = Path(destination)
    with tempfile.TemporaryDirectory() as temp_dir:
        raw_backup = Path(temp_dir) / (
            "socmint.sqlite" if is_sqlite(settings.database_url) else "socmint.pgsql"
        )
        if is_sqlite(settings.database_url):
            backup_sqlite(settings.database_url, raw_backup)
        else:
            backup_postgres(settings.database_url, raw_backup)

        if encrypt:
            if not settings.backup_passphrase:
                raise RuntimeError(
                    "SOCMINT_BACKUP_PASSPHRASE is required for encrypted backups."
                )
            encrypt_file(raw_backup, destination, settings.backup_passphrase)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(raw_backup, destination)
    return destination


def restore_backup(source, destination_database_url=None, encrypted=True):
    settings = load_settings(
        require_secret=False, database_url=destination_database_url
    )
    source = Path(source)
    with tempfile.TemporaryDirectory() as temp_dir:
        raw_backup = Path(temp_dir) / "socmint.restore"
        if encrypted:
            if not settings.backup_passphrase:
                raise RuntimeError(
                    "SOCMINT_BACKUP_PASSPHRASE is required to "
                    "restore encrypted backups."
                )
            decrypt_file(source, raw_backup, settings.backup_passphrase)
        else:
            raw_backup = source

        if is_sqlite(settings.database_url):
            target = Path(sqlite_path(settings.database_url))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(raw_backup, target)
        else:
            subprocess.run(
                ["psql", settings.database_url, "-f", str(raw_backup)], check=True
            )

    return settings.database_url

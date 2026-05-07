from src.socmint import database as db
from src.socmint.backup import create_backup, restore_backup


def test_sqlite_backup_and_restore_unencrypted(tmp_path, monkeypatch):
    source_db = tmp_path / 'source.db'
    restored_db = tmp_path / 'restored.db'
    backup_path = tmp_path / 'backup.sqlite'
    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{source_db}")

    db.configure_database(f"sqlite:///{source_db}")
    db.save_dossier({'target': 'operator_1', 'type': 'username'})

    create_backup(backup_path, encrypt=False)
    restore_backup(backup_path, destination_database_url=f"sqlite:///{restored_db}", encrypted=False)

    db.configure_database(f"sqlite:///{restored_db}")
    assert db.get_dossier('operator_1')['type'] == 'username'

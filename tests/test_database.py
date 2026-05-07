from src.socmint import database as db


def test_save_and_get_dossier_persists_results_profiles_and_media(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint-test.db'}")
    dossier = {
        "target": "operator_1",
        "type": "username",
        "data": {"sherlock": {"found": True}},
        "profiles": [
            {
                "url": "https://example.com/operator_1",
                "title": "Operator One",
                "description": "Profile",
                "site_name": "Example",
                "image": "https://example.com/image.jpg",
                "raw": {"html": "ok"},
            }
        ],
        "media": [
            {
                "url": "https://example.com/image.jpg",
                "path": "/tmp/image.jpg",
                "checksum": "abc123",
                "content_type": "image/jpeg",
            }
        ],
    }

    db.save_dossier(dossier)
    retrieved = db.get_dossier("operator_1")

    assert retrieved["target"] == "operator_1"
    assert retrieved["type"] == "username"
    assert retrieved["data"]["sherlock"] == {"found": True}
    assert retrieved["profiles"][0]["normalized"]["title"] == "Operator One"
    assert retrieved["media"][0]["checksum"] == "abc123"


def test_save_dossier_does_not_duplicate_media_for_same_source(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint-test.db'}")
    dossier = {
        "target": "operator_2",
        "type": "username",
        "media": [
            {
                "url": "https://example.com/image.jpg",
                "path": "/tmp/image.jpg",
                "checksum": "abc123",
                "content_type": "image/jpeg",
            }
        ],
    }

    db.save_dossier(dossier)
    db.save_dossier(dossier)
    retrieved = db.get_dossier("operator_2")

    assert len(retrieved["media"]) == 1


def test_get_dossier_returns_none_for_missing_target(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint-test.db'}")
    assert db.get_dossier("missing") is None


def test_record_audit_event_persists(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint-test.db'}")
    db.record_audit_event(
        "login_success", actor="operator", ip_address="127.0.0.1", details={"ok": True}
    )

    session = db.Session()
    event = session.query(db.AuditLog).first()
    session.close()

    assert event.action == "login_success"
    assert event.actor == "operator"
    assert '"ok": true' in event.details

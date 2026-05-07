import importlib
from pathlib import Path


def test_wsgi_imports_app_with_production_config(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "test-secret-key-with-enough-entropy")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "true")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'socmint-wsgi.db'}")
    module = importlib.import_module("src.socmint.wsgi")
    module = importlib.reload(module)

    assert module.app.name == "src.socmint.dashboard"


def test_deployment_assets_document_hidden_service_mapping():
    torrc = Path("deploy/tor/torrc.systemd.example").read_text()
    service = Path("deploy/systemd/socmint.service").read_text()
    compose = Path("docker-compose.yml").read_text()
    dockerfile = Path("Dockerfile").read_text()
    lockfile = Path("requirements.lock").read_text()
    makefile = Path("Makefile").read_text()
    workflow = Path(".github/workflows/ci.yml").read_text()

    assert "HiddenServicePort 80 127.0.0.1:5000" in torrc
    assert "gunicorn --workers 2 --bind 127.0.0.1:5000 src.socmint.wsgi:app" in service
    assert "ProtectHome=true" in service
    assert "MemoryDenyWriteExecute=true" in service
    assert "HiddenServicePort 80 127.0.0.1:5000" in Path("deploy/tor/torrc").read_text()
    assert "postgres:" in compose
    assert "context: ./deploy/tor" in compose
    assert "network_mode: service:tor" in compose
    assert "requirements.lock" in dockerfile
    assert "requirements.txt" not in dockerfile
    assert "FROM python:3.13-slim AS builder" in dockerfile
    assert "--no-index --find-links=/wheels" in dockerfile
    assert "pytest" not in lockfile
    assert Path("requirements-prod.txt").exists()
    assert Path("requirements-scanners.txt").exists()
    assert "backup-restore-smoke" in makefile
    assert "production-smoke" in makefile
    assert "production-docker-smoke" in makefile
    assert "secrets" in makefile
    assert "pip-audit -r requirements.lock" in workflow
    assert "python scripts/backup_restore_smoke.py" in workflow
    assert Path("deploy/systemd/socmint-backup.timer").exists()

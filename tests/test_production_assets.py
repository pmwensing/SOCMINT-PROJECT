import importlib
from pathlib import Path


def test_wsgi_imports_app_with_production_config(tmp_path, monkeypatch):
    monkeypatch.setenv('SOCMINT_SECRET_KEY', 'test-secret-key-with-enough-entropy')
    monkeypatch.setenv('SOCMINT_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('SOCMINT_AUTO_CREATE_DB', 'true')
    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{tmp_path / 'socmint-wsgi.db'}")
    module = importlib.import_module('src.socmint.wsgi')
    module = importlib.reload(module)

    assert module.app.name == 'src.socmint.dashboard'


def test_deployment_assets_document_hidden_service_mapping():
    torrc = Path('deploy/tor/torrc.systemd.example').read_text()
    service = Path('deploy/systemd/socmint.service').read_text()
    compose = Path('docker-compose.yml').read_text()

    assert 'HiddenServicePort 80 127.0.0.1:5000' in torrc
    assert 'gunicorn --workers 2 --bind 127.0.0.1:5000 src.socmint.wsgi:app' in service
    assert 'HiddenServicePort 80 127.0.0.1:5000' in Path('deploy/tor/torrc').read_text()
    assert 'postgres:' in compose
    assert 'context: ./deploy/tor' in compose
    assert 'network_mode: service:tor' in compose
    assert Path('deploy/systemd/socmint-backup.timer').exists()

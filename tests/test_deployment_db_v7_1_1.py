from pathlib import Path

from socmint.deployment_db import resolve_database_url, write_env_override


def test_sqlite_fallback_resolution(tmp_path, monkeypatch):
    monkeypatch.delenv("SOCMINT_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text("")

    result = resolve_database_url(str(env_file))

    assert result.source == "fallback_sqlite"
    assert result.mode == "sqlite"
    assert result.reachable is True
    assert result.resolved_url.startswith("sqlite:///")


def test_docker_dns_host_resolves_to_localhost(tmp_path, monkeypatch):
    monkeypatch.delenv("SOCMINT_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        'SOCMINT_DATABASE_URL="postgresql://socmint:pw@db:5432/socmint"\n'
    )

    result = resolve_database_url(str(env_file))

    assert result.source == ".env:SOCMINT_DATABASE_URL"
    assert "127.0.0.1" in result.resolved_url
    assert "db:5432" not in result.resolved_url
    assert result.safe_for_host_alembic is True


def test_write_env_override(tmp_path, monkeypatch):
    monkeypatch.delenv("SOCMINT_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text('SOCMINT_DATABASE_URL="sqlite:///tmp/test-socmint.db"\n')

    result = resolve_database_url(str(env_file))
    out = tmp_path / ".env.deployment.local"

    path = write_env_override(result, str(out))

    assert Path(path).exists()
    text = out.read_text()
    assert "SOCMINT_DATABASE_URL=" in text
    assert "DATABASE_URL=" in text

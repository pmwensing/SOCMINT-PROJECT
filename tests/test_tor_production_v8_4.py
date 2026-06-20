from src.socmint import database as db
from src.socmint.tor_production import deployment_check
from src.socmint.tor_production import hidden_service_status
from src.socmint.tor_production import production_env_template
from src.socmint.tor_production import production_readiness_report
from src.socmint.tor_production import torrc_snippet
from src.socmint.tor_production import upsert_hidden_service_status


def test_torrc_snippet_uses_v3_hidden_service():
    snippet = torrc_snippet(
        service_dir="/var/lib/tor/socmint", tor_port=80, target_port=5000
    )

    assert "HiddenServiceDir /var/lib/tor/socmint" in snippet
    assert "HiddenServicePort 80 127.0.0.1:5000" in snippet
    assert "HiddenServiceVersion 3" in snippet


def test_deployment_check_detects_onion_hostname_without_reading_secret(tmp_path):
    service_dir = tmp_path / "hidden_service"
    service_dir.mkdir()
    (service_dir / "hostname").write_text(
        "abcdefghijklmnopabcdefghijklmnopabcdefghijklmnopabcdefghijkl.onion"
    )
    (service_dir / "hs_ed25519_secret_key").write_text("do-not-read")

    check = deployment_check(str(service_dir))

    assert check["schema"] == "socmint.tor_production.v8_4_0"
    assert check["checks"]["service_dir_present"] is True
    assert check["checks"]["hostname_present"] is True
    assert check["checks"]["hostname_format_valid"] is True
    assert check["checks"]["private_key_detected_not_read"] is True
    assert "do-not-read" not in str(check)


def test_hidden_service_status_persists_readiness(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    service_dir = tmp_path / "hidden_service"
    service_dir.mkdir()
    onion = "abcdefghijklmnopabcdefghijklmnopabcdefghijklmnopabcdefghijkl.onion"

    status = upsert_hidden_service_status(
        enabled=True,
        onion_hostname=onion,
        service_dir=str(service_dir),
        actor="admin",
    )
    loaded = hidden_service_status()

    assert status["schema"] == "socmint.tor_production.v8_4_0"
    assert status["status"] == "ready"
    assert loaded["enabled"] is True
    assert loaded["onion_hostname"] == onion
    assert "HiddenServicePort" in loaded["torrc"]


def test_production_readiness_report_contains_required_controls(tmp_path):
    report = production_readiness_report(service_dir=str(tmp_path / "missing"))
    env_template = production_env_template()

    assert report["schema"] == "socmint.tor_production.v8_4_0"
    assert report["required_controls"]["metadata_minimization"] is True
    assert report["required_controls"]["responsible_use_gates_required"] is True
    assert "SOCMINT_TOR_HIDDEN_SERVICE=true" in env_template
    assert "change-me-outside-git" in env_template

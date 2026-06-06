from pathlib import Path


def test_support_bundle_module_defines_safe_schema_routes_and_redaction():
    source = Path("src/socmint/support_bundle_v13_34.py").read_text()

    assert "socmint.support_bundle.v13_34" in source
    assert "SUPPORT_BUNDLE_ROUTES" in source
    assert "redact_value" in source
    assert "SECRET_MARKERS" in source
    assert "<redacted:" in source
    assert "/api/v1/support/bundle/v13.34" in source
    assert "/support/bundle/v13.34" in source
    assert "/support/bundle/v13.34/download" in source


def test_wsgi_registers_support_bundle_routes():
    source = Path("src/socmint/wsgi.py").read_text()

    assert "from .support_bundle_v13_34 import register_support_bundle_routes_v13_34" in source
    assert "register_support_bundle_routes_v13_34(app)" in source


def test_support_bundle_script_and_docs_exist():
    script = Path("scripts/support_bundle_v13_34.sh").read_text()
    docs = Path("docs/TROUBLESHOOTING.md").read_text()
    release = Path("release/V13_34_SUPPORT_BUNDLE_DIAGNOSTICS.md").read_text()

    assert "support_bundle_v13_34" in script
    assert "support_bundle_api.json" in script
    assert "app_logs_tail.txt" in script
    assert "SOCMINT Troubleshooting" in docs
    assert "/support/bundle/v13.34" in docs
    assert "does not include plaintext secrets" in docs
    assert "Support Bundle Diagnostics" in release
    assert "scripts/support_bundle_v13_34.sh" in release


def test_support_bundle_payload_redacts_secret_values(monkeypatch):
    from socmint.support_bundle_v13_34 import redact_value

    assert redact_value("SOCMINT_ADMIN_PASSWORD", "secret-value") == "<redacted:12 chars>"
    assert redact_value("SOCMINT_SECRET_KEY", "abc") == "<redacted:3 chars>"
    assert redact_value("SOCMINT_DATA_DIR", "/tmp/data") == "/tmp/data"


def test_support_bundle_payload_points_to_latest_support_capture():
    from socmint.support_bundle_v13_34 import support_bundle_payload

    payload = support_bundle_payload()

    assert payload["acceptance_scripts"]["support_bundle_capture"] == "scripts/support_bundle_v13_34.sh"

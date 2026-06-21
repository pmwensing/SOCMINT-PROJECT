from src.socmint.security_audit import scan_text_for_secrets
from src.socmint.security_audit import security_header_expectations
from src.socmint.security_audit import session_cookie_expectations
from src.socmint.security_audit import validate_secret_value


def test_secret_scanner_detects_realistic_tokens():
    findings = scan_text_for_secrets(
        "STRIPE_SECRET=sk_test_1234567890abcdefABCDEF", "sample.env"
    )
    assert findings
    assert findings[0]["type"] in {"stripe_secret", "generic_password_assignment"}
    assert "sample.env" == findings[0]["path"]


def test_secret_scanner_ignores_documented_placeholders():
    findings = scan_text_for_secrets(
        "SOCMINT_SECRET_KEY=replace-with-a-long-random-secret", ".env.example"
    )
    assert findings == []


def test_secret_value_validator_blocks_short_or_placeholder():
    short = validate_secret_value("short")
    placeholder = validate_secret_value("replace-with-a-long-random-secret")
    strong = validate_secret_value("x" * 48)
    assert short["valid"] is False
    assert placeholder["valid"] is False
    assert strong["valid"] is True


def test_security_expectations_are_documented():
    headers = security_header_expectations()
    cookies = session_cookie_expectations(https_enabled=True)
    assert "Content-Security-Policy" in headers["headers"]
    assert cookies["expected"]["httponly"] is True
    assert cookies["expected"]["secure"] is True

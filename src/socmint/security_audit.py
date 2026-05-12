from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SECURITY_AUDIT_SCHEMA = "socmint.security_audit.v9_0_2"

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "stripe_secret": re.compile(r"sk_(live|test)_[A-Za-z0-9]{16,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "generic_password_assignment": re.compile(r"(?i)(password|secret|token|api[_-]?key)\s*=\s*['\"]?[^'\"\n]{12,}"),
}

ALLOWED_PLACEHOLDERS = (
    "replace-with-",
    "change-this-",
    "change-me-",
    "StrongPass123!",
    "LocalBackupPassphrase",
    "SOCMINT_SECRET_KEY",
    "SOCMINT_BACKUP_PASSPHRASE",
)

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


def looks_like_placeholder(value: str) -> bool:
    normalized = value.strip()
    return any(marker in normalized for marker in ALLOWED_PLACEHOLDERS)


def scan_text_for_secrets(text: str, path: str = "<memory>") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for name, pattern in SECRET_PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group(0)
            if looks_like_placeholder(value):
                continue
            findings.append(
                {
                    "type": name,
                    "path": path,
                    "start": match.start(),
                    "end": match.end(),
                    "redacted": value[:6] + "..." + value[-4:],
                }
            )
    return findings


def scan_repo_for_secrets(root: str | Path = ".") -> dict[str, Any]:
    root_path = Path(root)
    findings: list[dict[str, Any]] = []
    skipped_dirs = {".git", "venv", ".venv", "node_modules", "data", "exports", "backups", "__pycache__"}
    allowed_suffixes = {".py", ".md", ".txt", ".yml", ".yaml", ".env", ".example", ".toml", ".ini", ".sh"}
    for path in root_path.rglob("*"):
        if any(part in skipped_dirs for part in path.parts):
            continue
        if not path.is_file() or path.stat().st_size > 500_000:
            continue
        if path.suffix and path.suffix not in allowed_suffixes and path.name not in {"Makefile", ".env.example"}:
            continue
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue
        findings.extend(scan_text_for_secrets(text, str(path)))
    return {
        "schema": SECURITY_AUDIT_SCHEMA,
        "status": "ok" if not findings else "needs_review",
        "finding_count": len(findings),
        "findings": findings[:100],
    }


def security_header_expectations() -> dict[str, Any]:
    return {
        "schema": SECURITY_AUDIT_SCHEMA,
        "headers": SECURITY_HEADERS,
        "status": "documented",
    }


def session_cookie_expectations(https_enabled: bool = False) -> dict[str, Any]:
    return {
        "schema": SECURITY_AUDIT_SCHEMA,
        "expected": {
            "httponly": True,
            "samesite": "Lax",
            "secure": bool(https_enabled),
        },
        "status": "documented",
    }


def validate_secret_value(value: str | None, minimum_length: int = 32) -> dict[str, Any]:
    value = value or ""
    problems: list[str] = []
    if len(value) < minimum_length:
        problems.append(f"Secret must be at least {minimum_length} characters.")
    if looks_like_placeholder(value):
        problems.append("Secret appears to be a placeholder or documented example.")
    return {
        "schema": SECURITY_AUDIT_SCHEMA,
        "valid": not problems,
        "problems": problems,
    }


def security_audit_summary() -> dict[str, Any]:
    return {
        "schema": SECURITY_AUDIT_SCHEMA,
        "controls": {
            "secret_pattern_scanner": True,
            "security_header_expectations": True,
            "session_cookie_expectations": True,
            "secret_value_validator": True,
            "ci_recommendation": "Run scan_repo_for_secrets in pre-commit or CI for full enforcement.",
        },
    }

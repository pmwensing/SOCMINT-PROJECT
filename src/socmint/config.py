import logging
import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv


DEFAULT_DATA_DIR = "/var/lib/socmint"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATA_DIR}/socmint.db"
MIN_SECRET_LENGTH = 32
PLACEHOLDER_VALUES = {
    "replace-with-a-long-random-secret",
    "replace-with-a-strong-admin-password",
    "replace-with-a-long-backup-passphrase",
    "replace-with-a-private-invite-code",
    "change-this-postgres-password",
    "dev-secret",
    "changeme",
}


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    secret_key: str
    database_url: str
    data_dir: str
    media_dir: str
    allow_signup: bool
    https: bool
    tor_proxy: str | None
    log_level: str
    admin_user: str | None
    admin_password: str | None
    log_file: str | None
    auto_create_db: bool
    signup_invite_code: str | None
    backup_passphrase: str | None


def is_placeholder(value):
    if not value:
        return False
    normalized = value.strip().lower()
    return normalized in PLACEHOLDER_VALUES or normalized.startswith(
        ("replace-with-", "change-this-")
    )


def validate_secret(name, value):
    if is_placeholder(value):
        raise RuntimeError(f"{name} must not use a documented placeholder value.")
    if len(value) < MIN_SECRET_LENGTH:
        raise RuntimeError(f"{name} must be at least {MIN_SECRET_LENGTH} characters.")


def validate_password_strength(name, value):
    if is_placeholder(value):
        raise RuntimeError(f"{name} must not use a documented placeholder value.")
    if len(value) < 12:
        raise RuntimeError(f"{name} must be at least 12 characters.")


def validate_settings(settings, require_secret=True):
    if require_secret:
        if not settings.secret_key:
            raise RuntimeError(
                "SOCMINT_SECRET_KEY must be set to a stable, high-entropy value."
            )
        validate_secret("SOCMINT_SECRET_KEY", settings.secret_key)

    if settings.admin_user or settings.admin_password:
        if not settings.admin_user or not settings.admin_password:
            raise RuntimeError(
                "SOCMINT_ADMIN_USER and SOCMINT_ADMIN_PASSWORD must be set together."
            )
        validate_password_strength("SOCMINT_ADMIN_PASSWORD", settings.admin_password)

    if settings.allow_signup and not settings.signup_invite_code:
        raise RuntimeError(
            "SOCMINT_ALLOW_SIGNUP=true requires SOCMINT_SIGNUP_INVITE_CODE."
        )
    if settings.signup_invite_code:
        validate_password_strength(
            "SOCMINT_SIGNUP_INVITE_CODE", settings.signup_invite_code
        )

    if settings.backup_passphrase and is_placeholder(settings.backup_passphrase):
        raise RuntimeError(
            "SOCMINT_BACKUP_PASSPHRASE must not use a documented placeholder value."
        )


def load_settings(require_secret=True, database_url=None):
    load_dotenv()
    data_dir = os.getenv("SOCMINT_DATA_DIR", DEFAULT_DATA_DIR)
    secret_key = os.getenv("SOCMINT_SECRET_KEY", "")
    settings = Settings(
        secret_key=secret_key,
        database_url=database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        data_dir=data_dir,
        media_dir=os.path.join(data_dir, "media"),
        allow_signup=env_bool("SOCMINT_ALLOW_SIGNUP", False),
        https=env_bool("SOCMINT_HTTPS", False),
        tor_proxy=os.getenv("SOCMINT_TOR_PROXY") or None,
        log_level=os.getenv("SOCMINT_LOG_LEVEL", "INFO").upper(),
        admin_user=os.getenv("SOCMINT_ADMIN_USER") or None,
        admin_password=os.getenv("SOCMINT_ADMIN_PASSWORD") or None,
        log_file=os.getenv("SOCMINT_LOG_FILE") or None,
        auto_create_db=env_bool("SOCMINT_AUTO_CREATE_DB", False),
        signup_invite_code=os.getenv("SOCMINT_SIGNUP_INVITE_CODE") or None,
        backup_passphrase=os.getenv("SOCMINT_BACKUP_PASSPHRASE") or None,
    )
    validate_settings(settings, require_secret=require_secret)
    return settings


def configure_logging(settings=None):
    settings = settings or load_settings(require_secret=False)
    handlers = [logging.StreamHandler(sys.stdout)]
    if settings.log_file:
        handlers.append(logging.FileHandler(settings.log_file))

    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
        force=True,
    )

#!/usr/bin/env python3
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.socmint.main import generate_secrets  # noqa: E402


def write_env_file(path):
    values = generate_secrets()
    values.update(
        {
            "SOCMINT_ADMIN_USER": "admin",
            "SOCMINT_ADMIN_PASSWORD": values["SOCMINT_SECRET_KEY"][:24] + "Aa1!",
            "SOCMINT_ALLOW_SIGNUP": "false",
            "SOCMINT_AUTO_CREATE_DB": "false",
            "SOCMINT_BACKUP_PASSPHRASE": values["SOCMINT_BACKUP_PASSPHRASE"],
            "SOCMINT_DATA_DIR": "/var/lib/socmint",
            "SOCMINT_HTTPS": "false",
            "DATABASE_URL": "sqlite:////var/lib/socmint/socmint.db",
            "POSTGRES_DB": "socmint",
            "POSTGRES_PASSWORD": values["SOCMINT_BACKUP_PASSPHRASE"][:24] + "Aa1!",
            "POSTGRES_USER": "socmint",
        }
    )
    lines = [f"{key}={value}" for key, value in sorted(values.items())]
    path.write_text("\n".join(lines) + "\n")


def compose_command(env_file, *args):
    env = os.environ.copy()
    env["SOCMINT_ENV_FILE"] = str(env_file)
    return subprocess.run(
        ["docker", "compose", "--project-name", "socmint-smoke", *args],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
    )


def compose_check(env_file, *args):
    env = os.environ.copy()
    env["SOCMINT_ENV_FILE"] = str(env_file)
    return subprocess.run(
        ["docker", "compose", "--project-name", "socmint-smoke", *args],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_app(env_file, timeout_seconds=90):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = compose_check(
            env_file,
            "exec",
            "-T",
            "app",
            "python",
            "-c",
            (
                "import urllib.request; "
                "urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=2)"
            ),
        )
        if result.returncode == 0:
            return
        time.sleep(2)
    raise RuntimeError("app container did not become healthy")


def wait_for_tor_hostname(env_file, timeout_seconds=90):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = compose_check(
            env_file,
            "exec",
            "-T",
            "tor",
            "test",
            "-s",
            "/var/lib/tor/socmint/hostname",
        )
        if result.returncode == 0:
            return
        time.sleep(2)
    raise RuntimeError("tor hidden service hostname was not created")


def main():
    with tempfile.TemporaryDirectory(prefix="socmint-docker-smoke-") as temp_dir:
        env_file = Path(temp_dir) / "socmint.env"
        write_env_file(env_file)
        try:
            compose_command(env_file, "up", "--build", "-d", "app", "tor")
            wait_for_app(env_file)
            wait_for_tor_hostname(env_file)
        finally:
            compose_command(env_file, "down", "-v")
    print("Docker production stack smoke passed")


if __name__ == "__main__":
    main()

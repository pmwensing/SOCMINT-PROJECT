from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse, urlunparse

DOCKER_DNS_HOSTS = {"db", "postgres", "database"}
DEFAULT_SQLITE_URL = "sqlite:///var/lib/socmint/socmint.db"


@dataclass
class DbResolution:
    source: str
    original_url: str
    resolved_url: str
    dialect: str
    host: str | None
    port: int | None
    database: str | None
    mode: str
    reachable: bool
    safe_for_host_alembic: bool
    warnings: list[str]
    recommendations: list[str]


def read_env_file(path: str = ".env") -> dict[str, str]:
    env: dict[str, str] = {}
    p = Path(path)
    if not p.exists():
        return env

    for raw in p.read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def compose_port(service: str = "postgres", container_port: int = 5432) -> int | None:
    try:
        result = subprocess.run(
            ["docker", "compose", "port", service, str(container_port)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        return None

    out = result.stdout.strip()
    if not out or ":" not in out:
        return None

    try:
        return int(out.rsplit(":", 1)[1])
    except ValueError:
        return None


def tcp_reachable(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def normalize_url_for_host(url: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    parsed = urlparse(url)

    if parsed.scheme.startswith("sqlite"):
        return url, warnings

    host = parsed.hostname
    if host not in DOCKER_DNS_HOSTS:
        return url, warnings

    port = parsed.port or 5432
    published = compose_port(host, port)

    if published is None and host != "postgres":
        published = compose_port("postgres", port)

    target_port = published or port

    if "@" in parsed.netloc:
        auth, _host_part = parsed.netloc.rsplit("@", 1)
        new_netloc = f"{auth}@127.0.0.1:{target_port}"
    else:
        new_netloc = f"127.0.0.1:{target_port}"

    resolved = urlunparse(
        (
            parsed.scheme,
            new_netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )

    warnings.append(
        (f"Resolved Docker DNS host '{host}' to host-side 127.0.0.1:{target_port}.")
    )
    return resolved, warnings


def resolve_database_url(
    env_path: str = ".env",
    explicit_url: str | None = None,
    allow_sqlite_fallback: bool = True,
) -> DbResolution:
    file_env = read_env_file(env_path)

    candidates = [
        ("explicit", explicit_url),
        ("SOCMINT_DATABASE_URL", os.environ.get("SOCMINT_DATABASE_URL")),
        ("DATABASE_URL", os.environ.get("DATABASE_URL")),
        (".env:SOCMINT_DATABASE_URL", file_env.get("SOCMINT_DATABASE_URL")),
        (".env:DATABASE_URL", file_env.get("DATABASE_URL")),
    ]

    source = "missing"
    original = ""

    for candidate_source, candidate_value in candidates:
        if candidate_value:
            source = candidate_source
            original = candidate_value
            break

    warnings: list[str] = []
    recommendations: list[str] = []

    if not original:
        if allow_sqlite_fallback:
            source = "fallback_sqlite"
            original = DEFAULT_SQLITE_URL
            warnings.append("No DB URL configured; using local SQLite fallback.")
            recommendations.append(
                "Set SOCMINT_DATABASE_URL for deployment migrations."
            )

    resolved, normalize_warnings = normalize_url_for_host(original)
    warnings.extend(normalize_warnings)

    parsed = urlparse(resolved)
    dialect = parsed.scheme
    host = parsed.hostname
    port = parsed.port
    database = parsed.path.lstrip("/") if parsed.path else None

    mode = "network"
    reachable = False
    safe_for_host = True

    if dialect.startswith("sqlite"):
        mode = "sqlite"
        sqlite_path = Path(resolved.replace("sqlite:///", "", 1))
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        reachable = True
        recommendations.append("SQLite is suitable for local rehearsal only.")
    else:
        if host in DOCKER_DNS_HOSTS:
            safe_for_host = False
            warnings.append(
                f"Host '{host}' is Docker-network scoped and may fail from host shell."
            )
        if host and port:
            reachable = tcp_reachable(host, port)
            if not reachable:
                warnings.append(f"Could not reach {host}:{port}.")
                recommendations.append(
                    "Start database or use 127.0.0.1:<published-port> from host."
                )
        else:
            warnings.append("Database URL has no host/port.")

    return DbResolution(
        source=source,
        original_url=original,
        resolved_url=resolved,
        dialect=dialect,
        host=host,
        port=port,
        database=database,
        mode=mode,
        reachable=reachable,
        safe_for_host_alembic=safe_for_host,
        warnings=warnings,
        recommendations=recommendations,
    )


def write_env_override(
    resolution: DbResolution, path: str = ".env.deployment.local"
) -> str:
    p = Path(path)
    p.write_text(
        "\n".join(
            [
                "# Generated by SOCMINT v7.1.1 deployment DB resolver.",
                "# Review before production use.",
                f'SOCMINT_DATABASE_URL="{resolution.resolved_url}"',
                f'DATABASE_URL="{resolution.resolved_url}"',
                "",
            ]
        )
    )
    return str(p)


def run_alembic(resolution: DbResolution, dry_run: bool = False) -> int:
    env = os.environ.copy()
    env["SOCMINT_DATABASE_URL"] = resolution.resolved_url
    env["DATABASE_URL"] = resolution.resolved_url
    env["PYTHONPATH"] = f"{Path.cwd() / 'src'}:{env.get('PYTHONPATH', '')}"

    if dry_run:
        print("[dry-run] Would run: python3 -m alembic upgrade head")
        print("[dry-run] SOCMINT_DATABASE_URL=" + resolution.resolved_url)
        return 0

    return subprocess.call(
        [sys.executable, "-m", "alembic", "upgrade", "head"], env=env
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m socmint.deployment_db",
        description="Resolve deployment DB URL and safely run Alembic migrations.",
    )
    parser.add_argument(
        "command",
        choices=["resolve", "write-env", "dry-run", "migrate"],
    )
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--url", default=None)
    parser.add_argument("--output", default=".env.deployment.local")
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    resolution = resolve_database_url(args.env_file, args.url)

    if args.command == "resolve":
        if args.json:
            print(json.dumps(asdict(resolution), indent=2, sort_keys=True))
        else:
            print("source:", resolution.source)
            print("original:", resolution.original_url)
            print("resolved:", resolution.resolved_url)
            print("mode:", resolution.mode)
            print("reachable:", resolution.reachable)
            print("safe_for_host_alembic:", resolution.safe_for_host_alembic)
            for warning in resolution.warnings:
                print("warning:", warning)
            for recommendation in resolution.recommendations:
                print("recommendation:", recommendation)
        return 0

    if args.command == "write-env":
        print(write_env_override(resolution, args.output))
        return 0

    if args.command == "dry-run":
        return run_alembic(resolution, dry_run=True)

    if args.command == "migrate":
        if not resolution.reachable:
            print("ERROR: resolved database target is not reachable.")
            print(json.dumps(asdict(resolution), indent=2, sort_keys=True))
            return 2
        return run_alembic(resolution, dry_run=False)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

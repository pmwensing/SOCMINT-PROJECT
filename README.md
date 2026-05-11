# SOCMINT Project

SOCMINT builds local dossiers from open-source intelligence tools and serves the results through an authenticated Flask dashboard. It can run locally for research or behind a Tor v3 hidden service for private operator access.

## Safety

- Use only on targets you are authorized to investigate.
- The dashboard requires a stable `SOCMINT_SECRET_KEY`; startup fails if it is missing, too short, or still set to a documented placeholder.
- Production signup is disabled by default. If you enable it, you must also set `SOCMINT_SIGNUP_INVITE_CODE`.
- Onion services normally use HTTP inside Tor. Leave `SOCMINT_HTTPS=false` unless you also terminate HTTPS.
- Optional Tor egress only affects HTTP enrichment and media downloads. Scanner subprocesses are not force-proxied.
- Enrichment and media downloads reject localhost, private, link-local, reserved, and unsafe redirect targets.

## Configuration

Copy `.env.example` to `.env` for local or Docker usage, or place the same values in `/etc/socmint/socmint.env` for systemd.

Required production values:

```bash
SOCMINT_SECRET_KEY=replace-with-a-long-random-secret
SOCMINT_ADMIN_USER=admin
SOCMINT_ADMIN_PASSWORD=replace-with-a-strong-admin-password
DATABASE_URL=sqlite:////var/lib/socmint/socmint.db
SOCMINT_DATA_DIR=/var/lib/socmint
SOCMINT_ALLOW_SIGNUP=false
SOCMINT_HTTPS=false
SOCMINT_LOG_FORMAT=json
SOCMINT_LOG_FILE=/var/log/socmint/socmint.log
```

Optional outbound Tor proxy for enrichment/media HTTP requests:

```bash
SOCMINT_TOR_PROXY=socks5h://127.0.0.1:9050
```

For Docker Compose, use `socks5h://tor:9050`.

Optional invite-code signup mode keeps signup enabled while requiring a shared code:

```bash
SOCMINT_ALLOW_SIGNUP=true
SOCMINT_SIGNUP_INVITE_CODE=generate-a-private-invite-code
```

Generate secrets with a local password manager or commands such as:

```bash
make secrets
python -c "import secrets; print(secrets.token_urlsafe(48))"
openssl rand -base64 48
```

## Local Development

```bash
make install
make lint
make format
make test
SOCMINT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))") SOCMINT_DATA_DIR=$PWD/data DATABASE_URL=sqlite:///$PWD/data/socmint.db make serve
```

Enable Git hooks before you start working locally (the helper will init Git if needed):

```bash
make precommit-install
pre-commit run --all-files
```

Run the full local CI suite with:

```bash
make ci
make production-smoke
make production-docker-smoke
make backup-restore-smoke
```

`make production-docker-smoke` is the deployment rehearsal: it builds and boots
the app/Tor stack, waits for readiness, confirms the hidden-service hostname,
logs in as the bootstrap admin, queues and processes a scan job, verifies the
saved dossier, and tears everything down.

Generate and retrieve dossiers:

```bash
python -m src.socmint.main john_doe --tools sherlock,maigret
python -m src.socmint.main john_doe --retrieve
python -m src.socmint.main john_doe --no-enrich --output-json --export exports/john_doe.json
```

Spine subjects also expose an Ultimate Entity/Human dossier package through the
authenticated dashboard:

```text
/spine/subjects/<id>/ultimate-dossier
/api/v1/spine/subjects/<id>/ultimate-dossier
/api/v1/spine/subjects/<id>/ultimate-dossier?redacted=1
/api/v1/spine/subjects/<id>/ultimate-dossier/manifest
/spine/subjects/<id>/ultimate-dossier/assertions.csv
```

Create an admin manually:

```bash
python -m src.socmint.main init-admin admin 'StrongPass123!'
```

Create and restore encrypted backups:

```bash
SOCMINT_BACKUP_PASSPHRASE='long backup passphrase' python -m src.socmint.main backup backups/socmint.db.enc
SOCMINT_BACKUP_PASSPHRASE='long backup passphrase' python -m src.socmint.main restore backups/socmint.db.enc
```

## Production With systemd and Tor

Before first boot:

- Replace every `replace-with-*` and `change-this-*` value.
- Use a `SOCMINT_SECRET_KEY` of at least 32 random characters.
- Use a strong `SOCMINT_ADMIN_PASSWORD`.
- Keep `SOCMINT_ALLOW_SIGNUP=false`, or set a strong `SOCMINT_SIGNUP_INVITE_CODE`.
- Set `SOCMINT_BACKUP_PASSPHRASE` and store it outside the server.
- Run migrations before starting Gunicorn.
- Confirm `/var/lib/socmint` is owned by the `socmint` service user.
- Run a backup and restore drill before storing real investigation data.

1. Install the app under `/opt/socmint`, create a virtualenv, and install dependencies.
2. Create `/var/lib/socmint` owned by the `socmint` service user.
3. Copy `.env.example` to `/etc/socmint/socmint.env` and replace every placeholder.
4. Run migrations:

   ```bash
   /opt/socmint/venv/bin/alembic -c /opt/socmint/alembic.ini upgrade head
   ```

5. Install `deploy/systemd/socmint.service` to `/etc/systemd/system/socmint.service`.
6. Add the contents of `deploy/tor/torrc.systemd.example` to Tor's configuration.
7. Start services:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now socmint tor
   sudo cat /var/lib/tor/socmint/hostname
   ```

Gunicorn listens only on `127.0.0.1:5000`; Tor maps onion port `80` to that local socket.

Install the optional backup timer:

```bash
sudo cp deploy/systemd/socmint-backup.service /etc/systemd/system/
sudo cp deploy/systemd/socmint-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now socmint-backup.timer
```

The timer writes `/var/backups/socmint/socmint-latest.enc` daily and prunes `socmint-*.enc` files older than 30 days.

## Production With Docker Compose

```bash
cp .env.example .env
$EDITOR .env
docker compose up --build -d app tor
docker compose exec tor cat /var/lib/tor/socmint/hostname
```

Replace every placeholder in `.env` before starting the containers. The app refuses to boot with placeholder secrets, open signup without an invite code, or weak bootstrap credentials.

The Compose Tor service is built from `deploy/tor/Dockerfile`, so Tor is installed at image build time rather than on every service start. The app image installs the audited production dependency set from `requirements.lock`. The app shares the Tor container network namespace and binds `127.0.0.1:5000`, allowing Tor to map onion port `80` to the local Gunicorn socket.

SQLite is the default. For Postgres, set `DATABASE_URL=postgresql+psycopg://socmint:...@postgres:5432/socmint`, set the matching `POSTGRES_*` values, and start with:

```bash
docker compose --profile postgres up --build -d
```

The app service runs `alembic upgrade head` before Gunicorn on container startup. Dashboard scan requests are queued as jobs; run a worker alongside the web service to execute them:

```bash
python -m src.socmint.main process-jobs --max-jobs 1
```

For Docker deployments, run the dedicated worker profile:

```bash
docker compose --profile worker up -d worker
```

For systemd deployments, install and enable
`deploy/systemd/socmint-worker.service` plus
`deploy/systemd/socmint-worker.timer`.

## Backup And Restore Drills

SQLite drill:

1. Set `SOCMINT_BACKUP_PASSPHRASE` in the service environment.
2. Run `python -m src.socmint.main backup /var/backups/socmint/socmint.sqlite.enc`.
3. Copy the encrypted backup off-host.
4. Restore into a staging database with `DATABASE_URL=sqlite:////tmp/socmint-restore.db python -m src.socmint.main restore /var/backups/socmint/socmint.sqlite.enc`.
5. Start the dashboard against the restored DB and confirm login, target listing, export, and media links.

Postgres drill:

1. Set `DATABASE_URL=postgresql+psycopg://...` and `SOCMINT_BACKUP_PASSPHRASE`.
2. Ensure `pg_dump`, `psql`, and `openssl` are installed.
3. Run `python -m src.socmint.main backup /var/backups/socmint/socmint.pgsql.enc`.
4. Restore to a staging database with the same `restore` command after pointing `DATABASE_URL` at staging.
5. Run `alembic current` and perform the same dashboard checks.

Admin users can export/delete dossiers, manage users at `/admin/users`, assign `viewer`, `analyst`, or `admin` roles, and review filtered/paginated events at `/admin/audit`. Analysts can queue dashboard scan jobs but cannot manage users or export/delete dossiers. All users can rotate their own password at `/account/password`. Job status is available at `/jobs`.

Operational review APIs include `/api/v1/spine/assertions/review-queue`,
`/api/v1/spine/connectors/quality`, and `/api/v1/jobs/health`. Admin users can
requeue or cancel scan jobs through `/api/v1/jobs/<id>/requeue` and
`/api/v1/jobs/<id>/cancel`.

High-end analyst workflow surfaces include:

```text
/analyst/console
/cases
/evidence/capture
/connectors/marketplace
/responsible-use
/exports/builder
/spine/<id>/graph/canvas
/spine/<id>/resolution-lab
/api/v1/analyst/workbench
/api/v1/evidence/capture
/api/v1/evidence/captures
/api/v1/cases
/api/v1/connectors/marketplace
/api/v1/responsible-use/scope
/api/v1/responsible-use/gate
/api/v1/exports/builder
```

These surfaces are database-backed through the v8 workflow tables for cases,
case events, evidence captures, and responsible-use scope. Capture artifacts are
stored under the evidence directory, hashed with SHA-256, and recorded in the
chain-of-custody ledger.

## Observability

- `/healthz` confirms the Flask process is alive.
- `/readyz` confirms Flask can reach the configured database.
- Health and readiness endpoints are local-only.
- Every response includes `X-Request-ID`; incoming `X-Request-ID` values are preserved.
- Set `SOCMINT_LOG_FORMAT=json` for structured request logs with method, path,
  status, duration, remote address, and request ID.
- Set `SOCMINT_LOG_FILE=/var/log/socmint/socmint.log` when you want file logs;
  install `deploy/logrotate/socmint` as `/etc/logrotate.d/socmint`.
- For systemd file logs, install `deploy/tmpfiles/socmint.conf` as
  `/etc/tmpfiles.d/socmint.conf` to create `/var/log/socmint`.
- See `RUNBOOK.md` for deployment, rollback, backup, and incident procedures.

## Dependency And CI Checks

Dependencies are intentionally split:

- `requirements.lock` pins the audited production dashboard/deployment set.
- `requirements-prod.txt` installs only the production set.
- `requirements-scanners.txt` installs optional Kali/operator scanner integrations.
- `requirements-dev.txt` installs production, scanner, test, lint, and audit tooling.
- `requirements.txt` remains a backwards-compatible local development alias.

CI runs:

- `ruff check src tests scripts`
- `pytest -q`
- Docker Compose config validation
- Alembic migration smoke test
- `pip-audit -r requirements.lock`
- Encrypted SQLite backup/restore smoke via `make backup-restore-smoke`
- Local production boot and Compose config smoke via `make production-smoke`
- Full app/Tor container boot smoke via `make production-docker-smoke`

## Makefile Commands

- `make install` - install project dependencies into `./venv`
- `make install-prod` - install only production dashboard dependencies
- `make install-scanners` - install optional scanner integrations
- `make secrets` - generate safe environment values
- `make production-smoke` - run local production boot and Compose config checks
- `make production-docker-smoke` - build, boot, verify, and tear down app/Tor containers
- `make backup-restore-smoke` - run encrypted SQLite backup/restore verification
- `make test` - run the test suite
- `make migrate` - run Alembic migrations
- `make serve` - launch the Flask development dashboard
- `make serve-prod` - launch Gunicorn on `127.0.0.1:5000`
- `make process-jobs` - process queued scan jobs; set `MAX_JOBS=5` to process more
- `make clean` - remove Python caches

## Release Notes

See `CHANGELOG.md` for the current production candidate notes.

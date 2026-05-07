# SOCMINT Project

SOCMINT builds local dossiers from open-source intelligence tools and serves the results through an authenticated Flask dashboard. It can run locally for research or behind a Tor v3 hidden service for private operator access.

## Safety

- Use only on targets you are authorized to investigate.
- The dashboard requires a stable `SOCMINT_SECRET_KEY`; startup fails without one.
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
SOCMINT_ALLOW_SIGNUP=true
SOCMINT_HTTPS=false
```

Optional outbound Tor proxy for enrichment/media HTTP requests:

```bash
SOCMINT_TOR_PROXY=socks5h://127.0.0.1:9050
```

For Docker Compose, use `socks5h://tor:9050`.

Optional invite-code signup mode keeps signup enabled while requiring a shared code:

```bash
SOCMINT_ALLOW_SIGNUP=true
SOCMINT_SIGNUP_INVITE_CODE=replace-with-a-private-invite-code
```

## Local Development

```bash
make install
make lint
make format
make test
SOCMINT_SECRET_KEY=dev-secret SOCMINT_DATA_DIR=$PWD/data DATABASE_URL=sqlite:///$PWD/data/socmint.db make serve
```

Enable Git hooks before you start working locally (the helper will init Git if needed):

```bash
make precommit-install
pre-commit run --all-files
```

Generate and retrieve dossiers:

```bash
python -m src.socmint.main john_doe --tools sherlock,maigret
python -m src.socmint.main john_doe --retrieve
python -m src.socmint.main john_doe --no-enrich --output-json --export exports/john_doe.json
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
docker compose up --build -d app tor
docker compose exec tor cat /var/lib/tor/socmint/hostname
```

The Compose Tor service is built from `deploy/tor/Dockerfile`, so Tor is installed at image build time rather than on every service start. The app shares the Tor container network namespace and binds `127.0.0.1:5000`, allowing Tor to map onion port `80` to the local Gunicorn socket.

SQLite is the default. For Postgres, set `DATABASE_URL=postgresql+psycopg://socmint:...@postgres:5432/socmint`, set the matching `POSTGRES_*` values, and start with:

```bash
docker compose --profile postgres up --build -d
```

The app service runs `alembic upgrade head` before Gunicorn on container startup.

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

Admin users can export or delete dossiers from the target detail page and review recent events at `/admin/audit`. These actions, plus login and signup activity, are written to the `audit_logs` table.

## Dependency And CI Checks

`requirements.lock` pins the production dashboard/deployment dependency set used by `pip-audit`. The full Kali scanner dependency list remains in `requirements.txt`.

CI runs:

- `ruff check src tests`
- `pytest -q`
- Docker Compose config validation
- Alembic migration smoke test
- `pip-audit -r requirements.lock`

## Makefile Commands

- `make install` - install project dependencies into `./venv`
- `make test` - run the test suite
- `make migrate` - run Alembic migrations
- `make serve` - launch the Flask development dashboard
- `make serve-prod` - launch Gunicorn on `127.0.0.1:5000`
- `make clean` - remove Python caches

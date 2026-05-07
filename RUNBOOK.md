# SOCMINT Production Runbook

## Release Gate

Before deploying a release candidate:

1. Confirm the working tree is clean.
2. Run `make ci`.
3. Run `make production-docker-smoke`.
4. Run `make backup-restore-smoke`.
5. Confirm every production secret differs from `.env.example`.
6. Confirm `CHANGELOG.md` includes the release candidate notes.

`make production-docker-smoke` is the deployment rehearsal. It builds the app and
Tor images, boots the Compose stack, waits for `/readyz`, verifies the Tor hidden
service hostname, logs in as the bootstrap admin, queues a scan, processes the
queued job, verifies the dossier was saved, and tears the stack down with volumes
removed.

## Deploy

For Docker Compose:

1. Generate values with `make secrets`.
2. Write the values into `.env` or another file referenced by `SOCMINT_ENV_FILE`.
3. Run `docker compose up --build -d app tor`.
4. Run `docker compose exec app alembic current`.
5. Run `docker compose exec tor cat /var/lib/tor/socmint/hostname`.
6. Visit the onion URL, log in as the bootstrap admin, and rotate the password.
7. Start a worker with `docker compose --profile worker up -d worker`.

For systemd:

1. Install the checkout at `/opt/socmint`.
2. Install production dependencies into `/opt/socmint/venv`.
3. Write `/etc/socmint/socmint.env`.
4. Run `/opt/socmint/venv/bin/alembic -c /opt/socmint/alembic.ini upgrade head`.
5. Install `deploy/systemd/socmint.service`.
6. Install the Tor hidden-service configuration.
7. Install `deploy/systemd/socmint-worker.service` and
   `deploy/systemd/socmint-worker.timer`.
8. Install `deploy/tmpfiles/socmint.conf` to `/etc/tmpfiles.d/socmint.conf` and
   run `sudo systemd-tmpfiles --create /etc/tmpfiles.d/socmint.conf`.
9. Install `deploy/logrotate/socmint` to `/etc/logrotate.d/socmint`.
10. Run `sudo systemctl daemon-reload`.
11. Run `sudo systemctl enable --now socmint socmint-worker.timer tor`.

## Rollback

1. Stop job workers first so no scan is mid-write.
2. Create a fresh encrypted backup.
3. Stop the app service.
4. Restore the previous release checkout or image tag.
5. Restore the previous database backup if the failed release ran migrations that
   are not backward compatible.
6. Start the app and workers.
7. Check `/readyz`, login, `/jobs`, `/admin/audit`, and a dossier detail page.

## Backups

Set `SOCMINT_BACKUP_PASSPHRASE` and store it outside the server.

Create a backup:

```bash
python -m src.socmint.main backup /var/backups/socmint/socmint-latest.enc
```

Restore into staging first:

```bash
DATABASE_URL=sqlite:////tmp/socmint-restore.db \
python -m src.socmint.main restore /var/backups/socmint/socmint-latest.enc
```

After restore, run `alembic current`, log in, inspect target listings, export a
dossier, and verify media links.

## Operations

- `/healthz` verifies the Flask process is responding.
- `/readyz` verifies the Flask process and database are ready.
- Both endpoints are only exposed to local requests.
- Responses include `X-Request-ID`; incoming `X-Request-ID` is preserved.
- Set `SOCMINT_LOG_FORMAT=json` for structured logs.
- Set `SOCMINT_LOG_FILE=/var/log/socmint/socmint.log` for file logs; otherwise
  rely on journald or container logs.
- Use `SOCMINT_LOG_LEVEL=INFO` in production and `DEBUG` only during targeted
  troubleshooting.
- Review `/admin/audit` after admin changes, exports, deletes, failed logins, and
  signup activity.
- Process queued scans with `python -m src.socmint.main process-jobs --max-jobs=1`.
- For Docker, keep `docker compose --profile worker up -d worker` running.
- For systemd, keep `socmint-worker.timer` enabled.
- Tune worker cadence with `SOCMINT_WORKER_INTERVAL` for Docker and
  `OnUnitActiveSec` in `deploy/systemd/socmint-worker.timer` for systemd.

## Incident Checklist

1. Preserve logs and note request IDs.
2. Disable signup by setting `SOCMINT_ALLOW_SIGNUP=false`.
3. Rotate the admin password and any exposed invite code.
4. Stop workers if scan output integrity is in question.
5. Create an encrypted backup before modifying data.
6. Review `/admin/audit` for exports, deletes, user changes, and login failures.
7. Restore to staging and compare critical records before restoring production.

# SOCMINT v10.2 Production Deployment Pack

## Required files

- `scripts/install_production.sh`
- `.env.production.example`
- `docs/LOCAL_REBUILD_V10_2.md`
- `docs/PRODUCTION_DEPLOYMENT_PACK.md`

## Deployment checklist

1. Clone the repository.
2. Copy `.env.production.example` to `.env.production`.
3. Replace all placeholder secrets.
4. Run `bash scripts/install_production.sh`.
5. Confirm migrations complete.
6. Confirm backup/restore smoke passes.
7. Confirm production boot smoke passes.
8. Review release integrity and certification endpoints.
9. Start the app using the configured service manager or `make serve` for local testing.

## Notes

The installer is intentionally conservative. It validates local readiness and smoke tests but does not replace operator review of hosting, TLS, Tor, firewall, logging, backups, and retention policy.

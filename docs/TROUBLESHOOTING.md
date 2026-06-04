# SOCMINT Troubleshooting

## Support bundle

v13.34 adds a supportability-first diagnostics bundle for clean-install and runtime troubleshooting.

### Runtime page

- `/support/bundle/v13.34`

### JSON API

- `/api/v1/support/bundle/v13.34`

### Download ZIP

- `/support/bundle/v13.34/download`

### CLI helper

```bash
bash scripts/support_bundle_v13_34.sh
```

The support bundle is designed to be safe by default. It redacts environment values whose names include secret markers such as password, secret, token, key, passphrase, or invite.

## What the bundle contains

- Release/runtime diagnostic schema
- Redacted SOCMINT environment/config summary
- Data directory, dossier root, and support bundle root writability
- Locked route registration summary
- Latest Full Report export artifact summary
- Recent application error summary when `SOCMINT_LOG_FILE` is available
- Pointers to acceptance scripts

## What the bundle does not do

- It does not run migrations.
- It does not add investigative features.
- It does not expand connectors.
- It does not include plaintext secrets by design.

## Clean install troubleshooting

Run the final release clean install acceptance path first:

```bash
WORK_ROOT=/tmp/socmint-clean-install-$(date -u +%Y%m%d%H%M%S) \
BRANCH=v13.33 \
bash scripts/clean_install_acceptance_v13_33.sh
```

If a previous temp directory contains Docker-owned files, use a fresh `WORK_ROOT` or intentionally force cleanup with:

```bash
CLEAN_INSTALL_FORCE=1 WORK_ROOT=/tmp/old-socmint-clean-install bash scripts/clean_install_acceptance_v13_33.sh
```

## Runtime acceptance troubleshooting

```bash
bash scripts/runtime_acceptance_v13_33.sh
```

Expected checks:

- app container healthy
- locked routes return non-500 responses
- controlled Full Report export creates ZIP, Manifest, HTML, Markdown, and JSON
- final RC status payload remains available
- app logs do not show server errors

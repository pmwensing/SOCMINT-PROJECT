# v13.34 - Support Bundle Diagnostics

## Scope

This build adds a safe, redacted diagnostics bundle for post-release support and clean-install troubleshooting.

## Included

- Runtime support page: `/support/bundle/v13.34`
- JSON diagnostics API: `/api/v1/support/bundle/v13.34`
- Downloadable support ZIP: `/support/bundle/v13.34/download`
- CLI capture helper: `scripts/support_bundle_v13_34.sh`
- Dynamic Flask route-health resolution for concrete operator smoke-test paths
- Static regression tests for bundle schema, redaction, route registration, docs, and route-health matching

## Safety Notes

The bundle redacts environment and config values whose names include secret markers such as password, secret, token, key, passphrase, or invite. It is diagnostic-only and does not run migrations, expand connectors, or add investigative collection behavior.

## Operator Result

After v13.34, operators can generate a support bundle from the UI, JSON API, download route, or CLI helper and use it to confirm route registration, filesystem writability, export artifact presence, and recent application error signals.

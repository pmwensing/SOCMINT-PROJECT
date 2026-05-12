# SOCMINT Branch Inventory — v9.6 Cleanup Pass

## Current baseline

- default branch: `master`
- current release line: `v9.5.1`
- v9.6 branch: `release/v9.6-operator-ux-smoke-cleanup`

## Active / review before pruning

- `smoke/v9-6-operator-ux` — stale source branch; operator smoke files ported into v9.6 branch. Delete after v9.6 merges.
- `feat/v8.5`
- `feat/v8.4`
- `feat/v8.3`
- `feat/v8.2.0-membership-quotas`
- `feat/v7.8.0-ultimate-entity-human-dossier`
- `feat/v7.7.0-spine-native-intelligence-console`
- `feat/v7.6.2-connector-run-detail-finding-promotion`
- `feat/v7.6.1-connector-runtime-repair-diagnostics`
- `feat/v7.6.0-connector-runtime-installer-toolchain`
- `feat/v7.5.9-connector-runtime-health-normalizers`
- `feat/v7.5.8-command-center-enrichment-ux`
- `feat/v7.5.7-retention-ui-actions-confirm-delete`
- `feat/v7.5.6-full-report-retention-pin-delete`
- `feat/v7.5.5-full-report-history-compare`
- `feat/v7.5.4-full-report-runtime-smoke`
- `feat/v7.5.3-full-report-browser-flow-open-view`
- `feat/v7.5.2-full-report-ui-panel-manifest-button`
- `feat/v7.5.1-full-report-alias-manifest-polish`
- `feat/v7.1-drift-audit-full-report`
- `feat/v7.0-production-intelligence-workbench`
- `feat/connectors-sdk`
- `feat/export-plus`
- `fix/legacy-enrich-dossier-import`

## Likely merged v9 branches to prune after confirmation

These branch lines have already been merged through PRs into `master` and can likely be deleted after release confirmation:

- `release/v9.5.1-validation-metadata-sync`
- `cert/v9-5-release-certification`
- `beta/v9-public-readiness`
- `release/v9-docker-pipeline`
- `access/v9-team-case-control`
- `billing/v9-real-billing`
- `hardening/v9-route-enforcement`
- `hardening/v9-security-tests`
- `hardening/v9-audit`
- `release/v9.0`

## Manual prune commands

The current connector can create and update refs but does not expose a safe delete-branch action. Use local git or GitHub UI after v9.6 merges:

```bash
git push origin --delete release/v9.5.1-validation-metadata-sync
git push origin --delete cert/v9-5-release-certification
git push origin --delete beta/v9-public-readiness
git push origin --delete release/v9-docker-pipeline
git push origin --delete access/v9-team-case-control
git push origin --delete billing/v9-real-billing
git push origin --delete hardening/v9-route-enforcement
git push origin --delete hardening/v9-security-tests
git push origin --delete hardening/v9-audit
git push origin --delete release/v9.0
```

After v9.6 merges and is verified, also prune:

```bash
git push origin --delete smoke/v9-6-operator-ux
git push origin --delete release/v9.6-operator-ux-smoke-cleanup
```

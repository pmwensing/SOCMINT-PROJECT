
# SOCMINT v7.4.2 — Evidence Chain-of-Custody Ledger + Hash Verification Report

## Added

- Chain-of-custody ledger
- Custody event recording for:
  - intake
  - link
  - unlink
  - export attachment
  - manual review
  - hash verification
- Hash verification report JSON
- Hash verification report Markdown
- Chain-of-custody report JSON
- Chain-of-custody report Markdown
- Custody Ledger UI page
- `make test742`

## Routes

- `GET /evidence/custody`
- `GET /api/v1/evidence/custody`
- `POST /api/v1/evidence/custody`
- `GET /api/v1/evidence/verify`
- `POST /evidence/verify/run`
- `GET /api/v1/evidence/custody/report`

## Validate

`make test742`


# SOCMINT v7.4.3 — Evidence Integrity Dashboard + Custody Export Pack

## Added

- Evidence Integrity Dashboard
- Integrity summary metrics
- Missing evidence file detection
- Recent verification report listing
- Custody export ZIP pack builder
- Custody pack download endpoint
- Custody pack contents:
  - README
  - evidence manifest
  - evidence links manifest
  - chain-of-custody ledger
  - hash verification report
  - custody report
  - integrity dashboard snapshot
- `make test743`

## Routes

- `GET /evidence/integrity`
- `GET /api/v1/evidence/integrity`
- `POST /api/v1/evidence/integrity/pack`
- `POST /evidence/integrity/pack/run`
- `GET /evidence/integrity/packs/{name}/download`

## Validate

`make test743`

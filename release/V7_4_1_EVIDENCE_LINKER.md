
# SOCMINT v7.4.1 — Evidence Linker + Review Item Attachment Mapping

## Added

- Evidence Linker page
- Evidence-to-review-item link manifest
- Link relations:
  - `supports`
  - `contradicts`
  - `source`
  - `context`
  - `attachment`
- Review item attachment map API
- Automatic inclusion of linked evidence in export attachment ZIPs
- Evidence link delete API
- `make test741`

## Routes

- `GET /evidence/links`
- `GET /api/v1/evidence/links`
- `POST /api/v1/evidence/links`
- `POST /api/v1/evidence/links/delete`
- `POST /evidence/links/add`
- `GET /api/v1/evidence/attachment-map`

## Validate

`make test741`

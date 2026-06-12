# v16.8 Delivery Recovery Closure Audit Package

The v16.8 layer packages the verified v16 delivery recovery closure artifacts into a deterministic audit package.

- `POST /api/v1/case-delivery/<case_id>/recovery-closure-audit-package`

The package requires v16.7 closure verification to pass, creates a manifest for the recovery, receipt, closure, and closure verification artifacts, and emits a deterministic `audit_package_id`.

## Package checks

- Required artifacts must be present.
- v16.7 closure verification must be verified.
- Receipt, closure, and queue linkage must be consistent.
- Each manifest row includes artifact name, schema, case id, status, SHA-256 hash, presence flag, and manifest id.
- Blocked verification or linkage mismatch prevents package issuance.

## Validation

- Focused regression coverage in `tests/test_v16_8_case_delivery_recovery_closure_audit_package.py`.
- No database schema mutation or migration is introduced.

# v16.9 Delivery Recovery Closure Audit Package Verification

The v16.9 layer verifies v16.8 delivery recovery closure audit packages.

- `POST /api/v1/case-delivery/<case_id>/recovery-closure-audit-package/verify`

The verifier recomputes the package hash and audit package id, checks manifest order and per-row manifest ids, validates artifact hashes, and confirms linkage back to the verified v16.7 closure record.

## Verification checks

- `package_sha256` must match the canonical audit package payload.
- `audit_package_id` must match the canonical package payload plus package hash.
- Manifest order must match recovery, receipt, closure, and closure verification.
- Each manifest row must match its artifact and recomputed manifest id.
- Queue, case, receipt, and closure linkage must remain consistent.
- Failed closure verification or tampered package content blocks verification.

## Validation

- Focused regression coverage in `tests/test_v16_9_case_delivery_recovery_closure_audit_package_verification.py`.
- No database schema mutation or migration is introduced.

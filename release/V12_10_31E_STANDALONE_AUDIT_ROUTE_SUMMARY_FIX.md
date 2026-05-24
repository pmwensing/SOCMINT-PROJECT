# v12.10.31E — Standalone Audit Route Summary Hard Fix

Problem:
- v12.10.31D route-lock unit tests pass.
- Standalone drift audit still reports `missing_v12_routes: 8`.
- That means the audit summary/report path is not trusting or preserving the same runtime route result that tests validate.

Fix:
- Add a direct route-lock smoke function used by both tests and main audit.
- Force `main()` to use the normalized direct smoke output for `missing_v12_routes`.
- Emit route-lock diagnostics into the summary when routes are missing.
- Keep model/migration drift as WARN until schema reconciliation.

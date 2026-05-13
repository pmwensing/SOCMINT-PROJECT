# v10.1.1 Action Route Safety Contract + CSRF Enforcement Matrix

Generated: 2026-05-13T08:33:33.627388+00:00
Status: **pass**
Action readiness status: pass
Contracts: 49/49
Mutating routes: 40
CSRF missing: 0
Safe to migrate: 0

## Safety Matrix

- **PASS** `/api/v1/product/build-status` `['GET']` type=sensitive-read csrf=False session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final-gate/signoff-audit` `['GET']` type=sensitive-read csrf=False session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final-release/archive/<release_name>` `['GET']` type=file-or-archive-read csrf=False session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final-release/archives` `['GET']` type=file-or-archive-read csrf=False session=True auth=True write_safety=True blocked=True
- **PASS** `/product/artifacts/download/<path:relpath>` `['GET']` type=file-or-archive-read csrf=False session=True auth=True write_safety=True blocked=True
- **PASS** `/product/build-control` `['GET']` type=sensitive-read csrf=False session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final-release/archive` `['GET']` type=file-or-archive-read csrf=False session=True auth=True write_safety=True blocked=True
- **PASS** `/product/release-package/download/<package_name>` `['GET']` type=file-or-archive-read csrf=False session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/actions/export-control-snapshot` `['POST']` type=mutating csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/artifacts/review` `['POST']` type=mutating csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final/self-test/maintenance` `['POST']` type=mutating csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/release-package/<package_name>/zip` `['POST']` type=mutating csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/actions/export-control-snapshot` `['POST']` type=mutating csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/actions/refresh-readiness` `['POST']` type=mutating csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/artifacts/review` `['POST']` type=mutating csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final-release/archive/download/<path:filename>` `['GET']` type=file-or-archive-read csrf=False session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final/self-test/maintenance` `['POST']` type=mutating csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/release-package/zip/<package_name>` `['POST']` type=mutating csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/actions/write-reports` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/artifact-export-manifest/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final-gate/signoff` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final-gate/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final-release/archive/<release_name>/create` `['POST']` type=mutating csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final-release/distribution/decision` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final-release/distribution/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final-release/publish` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final/handoff/build` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final/self-test/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final/v10-bootstrap/decision` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final/v10-bootstrap/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/final/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/release-candidate/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/release-package/build` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/api/v1/product/write-reports` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/actions/write-reports` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/artifacts/export-manifest/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final-gate/signoff` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final-gate/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final-release/archive/<release_name>/create` `['POST']` type=mutating csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final-release/distribution/decision` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final-release/distribution/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final-release/publish` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final/handoff/build` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final/self-test/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final/v10-bootstrap/decision` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final/v10-bootstrap/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/final/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/release-candidate/write` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True
- **PASS** `/product/release-package/build` `['POST']` type=state-changing-action csrf=True session=True auth=True write_safety=True blocked=True

## Failed / Incomplete Contracts

- None

## Recommended Next Action

Safety contract is complete. Keep action routes dashboard-owned until CSRF/session/write-safety enforcement is independently tested.

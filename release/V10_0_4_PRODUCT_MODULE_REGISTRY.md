# v10.0.4 Product Module Registry + Route Ownership Map

Generated: 2026-05-13T05:11:02.850557+00:00
Status: **ok**
Product: SOCMINT Workbench
Release line: v10.x

## Module Summary

- **Dashboard core and compatibility route owner** — `socmint.dashboard` — 2/2 routes present — dashboard-owned
- **v9.9.x public compatibility URLs still served by dashboard during safe extraction** — `socmint.dashboard` — 9/9 routes present — dashboard-owned
- **Release Flow Extraction Phase 1** — `socmint.product_release_flow` — 15/15 routes present — extracted-module-reexport
- **Post-Release Extraction Phase 2** — `socmint.product_post_release` — 21/21 routes present — extracted-module-reexport
- **Artifact Pipeline Extraction Phase 3** — `socmint.product_artifacts` — 14/14 routes present — extracted-module-reexport

## Missing Routes

- None

## Ownership Map

- PRESENT `/` → `socmint.dashboard` / `dashboard-owned`
- PRESENT `/product/build-control` → `socmint.dashboard` / `dashboard-owned`
- PRESENT `/product/release-candidate` → `socmint.dashboard` / `dashboard-owned`
- PRESENT `/product/final-gate` → `socmint.dashboard` / `dashboard-owned`
- PRESENT `/product/final-release` → `socmint.dashboard` / `dashboard-owned`
- PRESENT `/product/artifacts` → `socmint.dashboard` / `dashboard-owned`
- PRESENT `/product/release-package` → `socmint.dashboard` / `dashboard-owned`
- PRESENT `/product/final` → `socmint.dashboard` / `dashboard-owned`
- PRESENT `/product/final/handoff` → `socmint.dashboard` / `dashboard-owned`
- PRESENT `/product/final/self-test` → `socmint.dashboard` / `dashboard-owned`
- PRESENT `/product/final/v10-bootstrap` → `socmint.dashboard` / `dashboard-owned`
- PRESENT `/product/release-candidate` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/api/v1/product/release-candidate` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/api/v1/product/release-candidate/write` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/product/final-gate` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final-gate` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final-gate/write` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final-gate/signoff` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final-gate/signoff-audit` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/product/final-release` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final-release` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final-release/publish` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/product/final-release/archive` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final-release/archives` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/product/final-release/verify` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final-release/verify` → `socmint.product_release_flow` / `extracted-module-reexport`
- PRESENT `/product/final-release/distribution` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final-release/distribution` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final-release/distribution/write` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final-release/distribution/decision` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final-release/distribution/audit` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/product/final` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final/write` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/product/final/handoff` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final/handoff` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final/handoff/build` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/product/final/self-test` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final/self-test` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final/self-test/write` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final/self-test/maintenance` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final/self-test/maintenance-audit` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/product/final/v10-bootstrap` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final/v10-bootstrap` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final/v10-bootstrap/write` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final/v10-bootstrap/decision` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/api/v1/product/final/v10-bootstrap/audit` → `socmint.product_post_release` / `extracted-module-reexport`
- PRESENT `/product/artifacts` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/api/v1/product/artifacts` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/product/artifacts/review` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/api/v1/product/artifacts/review` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/api/v1/product/artifact-review-state` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/product/artifacts/audit/<path:relpath>` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/api/v1/product/artifact-review-audit` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/product/artifacts/export-manifest` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/api/v1/product/artifact-export-manifest` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/product/release-package` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/api/v1/product/release-package` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/api/v1/product/release-package/build` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/api/v1/product/release-packages` → `socmint.product_artifacts` / `extracted-module-reexport`
- PRESENT `/product/release-package/download/{package_name}` → `socmint.product_artifacts` / `extracted-module-reexport`

# v10.0.6 Blueprint Ownership Migration Plan

Generated: 2026-05-13T05:49:55.376601+00:00
Status: **ready**
Module health: **healthy**
Overall module health score: 100
Safe candidates: 50/50
First wave routes: 10

## First Wave Routes

- `/product/artifacts` → `socmint.product_artifacts` / `product_artifacts_bp` (risk 5, low)
- `/product/artifacts/export-manifest` → `socmint.product_artifacts` / `product_artifacts_bp` (risk 5, low)
- `/product/final` → `socmint.product_post_release` / `product_post_release_bp` (risk 5, low)
- `/product/final-gate` → `socmint.product_release_flow` / `product_release_flow_bp` (risk 5, low)
- `/product/final-release` → `socmint.product_release_flow` / `product_release_flow_bp` (risk 5, low)
- `/product/final-release/distribution` → `socmint.product_post_release` / `product_post_release_bp` (risk 5, low)
- `/product/final-release/verify` → `socmint.product_release_flow` / `product_release_flow_bp` (risk 5, low)
- `/product/final/handoff` → `socmint.product_post_release` / `product_post_release_bp` (risk 5, low)
- `/product/final/self-test` → `socmint.product_post_release` / `product_post_release_bp` (risk 5, low)
- `/product/final/v10-bootstrap` → `socmint.product_post_release` / `product_post_release_bp` (risk 5, low)

## Blocked Routes

- None

## Recommended Next Action

Move first-wave low-risk GET/view routes to extracted blueprints one route family at a time.

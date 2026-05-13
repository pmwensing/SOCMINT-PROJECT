# v10.0.6 - Product Blueprint Ownership Migration Plan

## Purpose

v10.0.6 generates a route-by-route migration plan for moving dashboard-owned compatibility routes into extracted product blueprints.

## Adds

- Migration Plan UI:
  - `/product/v10/migration-plan`

- Migration Plan APIs:
  - `GET /api/v1/product/v10/migration-plan`
  - `POST /api/v1/product/v10/migration-plan/write`

- Migration plan artifacts:
  - `release/V10_0_6_BLUEPRINT_MIGRATION_PLAN.json`
  - `release/V10_0_6_BLUEPRINT_MIGRATION_PLAN.md`

- Hardening report:
  - `release/V10_0_6_BLUEPRINT_MIGRATION_PLAN_HARDENING_REPORT.json`
  - `release/V10_0_6_BLUEPRINT_MIGRATION_PLAN_HARDENING_REPORT.md`

- Smoke targets:
  - `make product-migration-plan-smoke`
  - `make test1006`
  - `make migration-plan-hardening-smoke`

## Risk Scoring

The plan scores each route using:

- HTTP method risk
- semantic route risk
- file/download/archive/package risk
- module health gate
- route presence gate

## Safety Gate

A route cannot be marked safe unless:

- module health is healthy
- the target module is healthy
- the target module is ready for deeper extraction
- the route is present
- the risk score is below the first-wave threshold

## Goal

Identify the safest first routes for actual blueprint ownership migration without breaking v9 compatibility.

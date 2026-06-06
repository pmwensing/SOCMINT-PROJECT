# Updated Ultimate SOCMINT Product Build Spec

This updated build specification is based on a current audit of the repository and implements a higher-value product plan that matches the existing SOCMINT architecture while correcting local build environment issues and strengthening production readiness.

## 1. Build Environment

- Default developer Python virtual environment: `.venv`
- Fallback: `venv` when `.venv` is not present
- Local dependency installation:
  - `make install` now detects and uses `.venv` by default
  - `make install-prod` and `make install-scanners` now use the active virtualenv
- CI and local commands should use `$(VENV)/bin/*` for all toolkit invocations to avoid hardcoded `./venv` paths
- `README.md` now documents the chosen virtualenv behavior explicitly

### Acceptance criteria

- `make install` creates and uses `.venv` by default
- `make ci` runs without requiring a hardcoded `./venv` path
- `README.md` and developer docs reflect `.venv` usage

## 2. Product Goal Validation

The repository implements a subject-centric SOCMINT platform with these core capabilities:

- ingest initial targets/seeds
- create subject records
- run connector discovery/enrichment
- build dossier assertions and evidence traces
- persist observation/assertion provenance

This matches the key product goal of back-linking enriched data to the originating input.

### Current strengths

- subject/seed models are isolated by `subject_id`
- connector runs store seed and provenance metadata
- dossier assertions are derived from subject-specific observations
- the spine pipeline is built to keep one subject context separate from another

### Remaining gaps

- stronger case scope and case-level authorization are not yet explicit
- audit logging and export blockers are not fully realized in existing models
- per-case separation of PII and retention policy enforcement needs formalization

## 3. Recommended High-Value Enhancements

### 3.1 Case and scope controls

- add explicit `Case` / `Scope` concepts
- bind subjects, seeds, dossiers, and exports to a case scope
- enforce target allowlists/deny-lists at the case level
- require authorization metadata for all connector runs and exports

### 3.2 Provenance and evidence traceability

- ensure every discovery record includes:
  - initial input seed ID
  - connector run ID
  - source reference
  - capture artifact hash
  - evidence chain to dossier claim
- record `actor`, `timestamp`, and `confidence` for all assertion actions

### 3.3 Dossier export and compliance

- extend dossier export support to:
  - JSON, HTML, Markdown, CSV
  - ZIP bundle with manifest
  - signed/hashed export metadata
- implement export blocker rules for:
  - single-source claims
  - unreviewed assertions
  - contradictory identity claims

### 3.4 Responsible use and data protection

- require policy gating for:
  - target captures
  - connector executions
  - dossier exports
- apply sensitive-data redaction defaults
- support audit records for all allow/warn/block decisions
- build role-based access controls for analyst actions

### 3.5 Graph and analyst experience

- represent subject intelligence as nodes and edges with evidence refs
- expose a review-first analyst workbench with:
  - active case dashboard
  - scan/review queues
  - high-risk claim alerts
  - contradiction visibility
- preserve user input isolation in graph discovery and export views

## 4. Security and operational requirements

- validate secrets and environment variables securely
- enforce CSRF, secure cookies, CSP/security headers
- limit access to administrative destructive operations
- ensure no secrets appear in logs
- enable encrypted backups and restore verification
- document Tor hidden-service deployment and smoke tests

### Deployment profiles

- `dev-local`: local app, SQLite, no Tor required
- `prod-tor-only`: app exposed only through Tor hidden service
- `prod-clearnet-admin-disabled`: optional future hardened profile

## 5. Immediate Build Plan

1. patch local developer tooling to use `.venv` by default and avoid hardcoded `./venv` commands
2. validate `make install`, `make ci`, and `make production-smoke` on a clean checkout
3. extend data models for explicit `Case` and `Scope` association
4. add audit/event logging around connector runs and export actions
5. improve dossier exports with manifest hash verification and evidence references
6. add acceptance tests for export blockers, case scope enforcement, and policy gate behavior

## 6. Recommended Implementation priorities

### Priority 1: Environment and reproducibility

- make `.venv` the standard local development environment
- ensure all automated targets resolve virtualenv paths dynamically
- document the local startup path clearly in `README.md`

### Priority 2: Core subject traceability

- preserve subject isolation across seeds and connector runs
- keep the initial input separate from other search inputs
- attach all enrichment and assertion data to the originating subject

### Priority 3: Responsible and compliant output

- add dossier export integrity checks
- enforce policy-based blocking for risky assertions
- create explicit reviewer workflows for claims and contradictions

## 7. Deliverable artifacts

- new build-spec document: `docs/UPDATED_ULTIMATE_SOCMINT_PRODUCT_BUILD_SPEC.md`
- updated `Makefile` to detect `.venv` and use the active virtualenv for CI commands
- updated `README.md` to document the chosen virtualenv directory
- future implementation work: case/scope enforcement, evidence provenance, dossier export blockers

---

This document is intended as the updated product build spec for the current repository state. It combines the audited architecture, the local development fix, and the next-highest-value product enhancements.

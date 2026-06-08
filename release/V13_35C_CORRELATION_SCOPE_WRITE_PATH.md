# v13.35C — Correlation Scope Backfill + Write-Path Propagation

## Purpose

v13.35B added the persistent scope-column migration and policy helper. v13.35C propagates scope IDs through write paths and adds an idempotent legacy backfill foundation.

## Scope

- New seed/root records receive `correlation_scope_id`.
- Connector-run style child records can inherit parent/root scope.
- Observations/assertions/finding-like records can carry scope forward.
- Legacy backfill is deterministic and idempotent.
- Separate initial searches remain isolated by default.
- Cross-scope ambiguous profile matches remain quarantine-first.

## Non-goals

- No new connectors.
- No new enrichment sources.
- No broad UI redesign.
- No final v13.35 tag.

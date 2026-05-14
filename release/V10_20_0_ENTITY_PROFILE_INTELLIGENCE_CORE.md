# SOCMINT v10.20.0 — Entity Profile Dossier Intelligence Core

## Summary

Refocuses the dossier builder on full entity profile intelligence. Adds a new intelligence core that expands the compact v10.3 dossier payload into identity, account, attribute, timeline, relationship, contradiction, risk, citation, and analyst-note sections.

## Focus

The intelligence core answers:

- Who is the entity?
- Which aliases and handles are known?
- Which accounts and platforms are associated?
- Which attributes are evidence-backed?
- What timeline events are known?
- Which relationships are known?
- Which claims conflict?
- What is the confidence and risk posture?
- Which evidence supports each section?

## Changes

- Adds `src/socmint/entity_profile_intelligence.py`.
- Adds `src/socmint/entity_profile_intelligence_routes.py`.
- Registers intelligence routes in `src/socmint/wsgi.py`.
- Adds `tests/test_entity_profile_intelligence_v10_20.py`.
- Adds `scripts/test_v10_20.sh`.

## Routes

- `POST /api/v1/dossier-builder/v3/intelligence/build`
- `POST /api/v1/dossier-builder/v3/intelligence/summary`
- `POST /api/v1/dossier-builder/v3/intelligence/markdown`

## Sections

- identity summary
- aliases / handles
- accounts / platforms
- evidence-backed attributes
- timeline
- relationships
- contradictions
- risk scoring
- confidence scoring
- source citations
- analyst notes

## Merge gate

Run:

```bash
bash scripts/test_v10_20.sh
```

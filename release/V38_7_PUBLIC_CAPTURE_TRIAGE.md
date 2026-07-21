# v38.7 — Public Capture Duplicate, Change, Relevance and Handoff Triage

## Objective

Add deterministic triage over accepted v29 artifacts that have already been registered as v36 source records. v38.7 identifies exact duplicates, canonical-URL recaptures, content-hash changes, analyst relevance classifications, and eligible v37 handoffs without storing raw content, assigning factual significance, or creating observations.

## Authoritative inputs

v38.7 accepts only registered v36.1 source records with:

- exact case binding;
- canonical and retrieved URLs;
- valid capture time;
- content SHA-256;
- accepted v29 artifact binding and artifact-event SHA-256;
- adapter identity.

Raw crawler responses, unaccepted artifacts, unregistered captures, and incomplete source bindings are blocked.

## Deterministic duplicate triage

Sources with the same content SHA-256 are grouped as exact duplicates. The earliest capture, with source ID as a deterministic tie-breaker, is suggested as the primary source for triage presentation. Later exact copies are marked support-suppressed.

The primary selection is a deterministic suggestion only. It does not mutate a source, delete an artifact, or declare publication origin.

Each exact-hash group creates a mirror proposal containing an `exact_content_hash` signal. The proposal does not become a v36.4 independence assessment until an analyst separately confirms it.

## Recapture and change summaries

Sources sharing a canonical URL are grouped as recaptures and ordered by capture time. Consecutive captures receive a hash-level summary:

- `unchanged` when content SHA-256 is equal;
- `content_hash_changed` when content SHA-256 differs.

A changed hash does not identify what changed, why it changed, whether the change matters, or whether any actor caused it. Factual significance and causation remain explicitly unassigned.

## Relevance classifications

Every source requires one explicit analyst classification:

- `direct_case`;
- `relocation_mitigation`;
- `candidate_review`;
- `out_of_scope`.

`direct_case` requires at least one matched term or matched entity plus a rationale. Candidate-review and out-of-scope sources are not eligible for support or v37 handoff. Exact-duplicate secondary sources are support-suppressed even when directly relevant.

This classification does not create an observation, approve a claim, or assign truth.

## Explicit v36.4 mirror confirmation

`confirm_mirror_proposal` requires:

- an existing v38.7 triage record;
- an exact proposal ID;
- explicit analyst confirmation and reason.

It then calls the existing v36.4 `assess_source_independence` authority. v38.7 does not create a second independence graph or silently count copies as corroboration.

## Explicit v37 handoff

`handoff_capture_to_v37` requires:

- an existing triage record;
- a source marked v37-handoff-eligible;
- a non-suppressed primary capture;
- exact accepted-artifact and content-hash binding;
- explicit analyst selection, confirmation, import time, filename, media type, format, and reason.

The function calls the existing v37.1 import-envelope authority. It registers or reuses an import envelope only. It does not stage records, promote observations, assign truth, merge entities, approve claims, mutate dossiers, export, or publish.

## Persistence and idempotency

Triage records are append-only AuditLog events. The record ID and SHA-256 are deterministic over source bindings, relevance assessments, duplicate groups, mirror proposals, recapture groups, change summaries, existing independence-group references, and reason. Exact replay reuses the existing triage record.

## Safety boundary

v38.7 does not:

- fetch a URL or run a crawler;
- read or retain raw capture content;
- mutate source or artifact records;
- automatically declare mirrors, syndication, derivation, common origin, or independence;
- count duplicate or mirror copies as independent support;
- infer textual changes from hash differences;
- assign factual significance, causation, intent, or misconduct;
- automatically register imports or stage records;
- create or promote observations;
- assign truth, merge entities, approve claims, mutate dossiers, export, or publish.

## Acceptance criteria

- incomplete, cross-case, or unregistered source bindings are blocked;
- every source has exactly one complete relevance assessment;
- direct-case classification requires matched evidence;
- exact hashes create deterministic duplicate groups and mirror proposals;
- duplicate secondary sources are support-suppressed;
- canonical recaptures create ordered hash-change summaries;
- hash changes assign no factual significance or causation;
- candidate-review and out-of-scope captures are not handoff-eligible;
- v36.4 mirror assessment requires a separate explicit confirmation;
- v37.1 handoff requires a separate explicit primary-source selection;
- import handoff does not stage records or create observations.

## Validation

```bash
pytest -q tests/test_v38_7_public_capture_triage.py
```

## Next authority

After v38.7 is merged and green, v38.8 may add the integrated Public Discovery and Capture Workspace with read-only execution, recovery, capture, provenance, duplicate/change, triage, and v37-handoff visibility plus browser E2E safety proof.

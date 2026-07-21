# v38.4 — Synthetic Capture Provenance Gate

## Objective

Prove the complete capture-governance path with fictional, offline content before any live-network adapter becomes eligible.

v38.4 turns one explicitly reviewed v38.3 candidate into a synthetic capture manifest, registers four hash-bound artifacts through the existing v29.4 evidence authority, requires separate human acceptance of those artifacts, registers provenance through the existing v36.1 source authority, and creates an explicit v37.1 import handoff. It does not contact the candidate URL or any archive service.

## Two-phase workflow

### Phase 1 — Prepare synthetic capture artifacts

`prepare_synthetic_capture` requires:

- an accepted v38.3 archive candidate;
- an explicit `approved_for_synthetic_capture` review decision and reason;
- an allowing v38.2 gate whose live-network eligibility remains false;
- the originating v38.1 request, collection job, case, purpose, and attempt bindings;
- normalized requested and final URLs;
- a validated redirect chain, response status, non-sensitive response headers, capture time, and adapter identity;
- exactly four fictional capture roles:
  - primary HTML;
  - public-document PDF;
  - WARC, WACZ, or equivalent archive capture;
  - screenshot.

The service calculates the byte size and SHA-256 of every fictional file, creates a deterministic capture manifest, and submits each file to the existing v29.4 `register_artifact` authority. The service does not retain the supplied content bytes.

Artifacts remain in the authoritative v29 state returned by registration. v38.4 does not automatically accept a registered or quarantined artifact.

### Phase 2 — Finalize provenance

`finalize_synthetic_capture_provenance` requires all four artifacts to have been explicitly accepted through v29.4 and to match the hashes in the synthetic manifest.

It then:

- registers the primary HTML capture through v36.1 with canonical and retrieved URLs, capture time, adapter identity, access method, terms notes, and the accepted artifact binding;
- registers an explicit v37.1 import envelope for the accepted HTML artifact;
- records the complete artifact, source, and import bindings in an append-only finalization event;
- marks the pre-live-network gate satisfied only after every required proof is present.

The v37 handoff creates an import envelope only. It does not stage records or promote an observation.

## Required proofs

The final gate records all of the following as true:

- synthetic capture envelope completed;
- deterministic content SHA-256 calculated;
- provenance manifest completed;
- accepted v29 artifact bindings completed;
- registered v36 source binding completed;
- explicit v37 import handoff completed;
- duplicate and quarantine controls did not inflate support.

## Safety and privacy boundaries

- no DNS lookup, HTTP request, Common Crawl request, Internet Archive request, Scrapy execution, or Browsertrix execution;
- no credentials, cookies, authorization headers, or authenticated browser state;
- sensitive response headers are rejected;
- no raw capture content is written to AuditLog or retained by v38.4;
- no artifact acceptance is automated;
- no observation is derived or promoted;
- no truth assignment, entity merge, claim approval, relationship decision, dossier mutation, export, or publication;
- fictional domains and synthetic bytes only in public tests;
- all consequential manifests and bindings are deterministic, append-only, and hash-bound.

## Live-network decision

Successful v38.4 completion proves the governance path required by the v38.0 planning contract. It does not itself enable a network adapter. A later v38.5 implementation must still add its own explicit operator action, current policy checks, execution controls, and exact-head validation before any live public HTTP request is possible.

## Next action

`implement_v38_5_live_passive_archive_and_strict_public_http_adapters_after_separate_review`

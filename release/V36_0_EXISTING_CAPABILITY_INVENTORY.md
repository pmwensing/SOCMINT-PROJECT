# v36.0 Existing Capability Inventory

## Authoritative capabilities to reuse

- dossier spine separation of seeds, connector runs, raw artifacts, observations, correlations, assertions, analyst validation, and dossiers
- accepted evidence artifacts and normalized spine observations
- v30.1 append-only corroboration claims bound to case, entity, purpose, and source references
- v30.2 deterministic claim-to-evidence and claim-to-observation linkages
- v30.3 append-only contradiction and analyst-disagreement records with immutable resolution history
- v30.4 bounded explainable confidence assessments with visible components, limitations, and unresolved-conflict penalties
- v30.5 human analytic review decisions and reassessment history
- v30.6 separate dossier-contribution decisions and withdrawal history
- existing identity graph, identity nodes, identity edges, and reviewable merge candidates
- existing dossier builder, quality gate, traceability, readiness, supervisor approval, export store, export gate, export audit, manifest, and bundle services
- existing append-only AuditLog and deterministic content hashing helpers
- closed v35 durable confirmation, action-contract validation, execution state, authoritative result envelopes, reconciliation, and read-only recovery observability

## Proven remaining gaps

- source records do not yet distinguish the original information origin from a retrieved or mirrored URL
- current confidence logic can count multiple artifacts or observations without proving independent origin
- entity merge candidates are primarily based on duplicate normalized values rather than an explainable multi-signal resolution assessment
- identity confidence and factual claim support are not consistently represented as separate dimensions
- identifier ownership is not consistently time-bounded
- claim assessments do not yet rank mutually exclusive alternatives inside an explicit conflict set
- temporal relevance and current-versus-historical status are not first-class claim dimensions throughout the dossier pipeline
- relationship and timeline edges do not yet require a uniform source, time interval, and inference-warning contract
- approved v30 dossier contributions are eligibility records but do not yet synthesize a canonical versioned entity dossier projection
- existing traceability and quality helpers include file-name and keyword heuristics that are insufficient for statement-level evidentiary verification
- privacy purpose, scope, minimization, and sensitive-context controls are not yet bound to every v36 collection-to-dossier transition

## Required v36 composition layer

- claim-type-specific source reliability profiles with visible reasons
- source origin, derivation, mirror, syndication, and dependency grouping
- tool-neutral canonical observation adapters with deterministic hashes and quarantine
- explainable entity-candidate matching using positive, negative, strong, supporting, and weak signals
- explicit identifier claims and temporal ownership
- dimensional verification assessments separating identity, support, source, integrity, time, independence, conflict, and review status
- alternative ranking that identifies the most strongly supported claim without assigning truth
- time-bounded relationship and event claims with correlation-versus-causation warnings
- reproducible EntityAccuracySnapshot projections derived from exact append-only event hashes
- section-level dossier synthesis through the existing export and manifest systems
- one operator workspace showing why a claim is believed, disputed, limited, held, rejected, or eligible for dossier use

## Non-goals

- no replacement spine or evidence backend
- no autonomous investigation objective selection
- no automatic truth declaration
- no automatic entity merge
- no face-recognition identity decision
- no automatic claim approval
- no automatic dossier publication
- no suppression of contradictory or rejected hypotheses
- no source allowlist that assigns reliability without claim-specific reasons
- no case-access or privacy-policy weakening
- no hidden background collection or execution

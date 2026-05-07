# SOCMINT-PROJECT Dossier Spine

## Core rule

Connectors do not write truth.

Connectors write raw evidence and observations. The spine correlates
observations into dossier assertions with confidence scores, provenance,
evidence hashes, and validation state.

## Pipeline

Seed -> ConnectorRun -> RawArtifact -> Observation -> Correlation
-> DossierAssertion -> Analyst Validation -> Dossier

## High-value connector standard

A connector belongs in the production spine only if it improves at least one:

1. seed expansion
2. cross-source corroboration
3. evidence preservation
4. entity resolution
5. media/profile enrichment
6. contradiction detection
7. validated dossier quality

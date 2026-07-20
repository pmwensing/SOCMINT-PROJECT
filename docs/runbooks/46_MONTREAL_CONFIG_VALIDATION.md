# 46 Montreal Config Validation

This runbook validates the case configuration added for the 46 Montreal evidence workflow.

## Validate config pack

Run from the SOCMINT-PROJECT repository root:

```bash
python scripts/case_46_montreal/validate_case_configs.py
```

Expected result:

```json
{
  "schema": "socmint.case_46_montreal.config_validation.v1",
  "status": "pass"
}
```

## What it checks

The validator checks that the config pack contains:

- the 46 Montreal case ID
- 46 Montreal address aliases
- entity-scope language for directly involved people, businesses, authorities, contractors, inspectors, documents, orders, communications, and events
- 559 Macdonnel as relocation / mitigation context only
- Cowdy address exclusions
- private evidence repo binding
- local and cloud evidence storage references
- evidence register and chain-of-custody manifest references
- search-pack identifiers and negative filters
- public-discovery scope gates
- human review before dossier/export

## Config files covered

```text
config/cases/46_montreal.case.yaml
config/evidence_repos/46_montreal_evidence_repo.yaml
config/search_packs/46_montreal_keywords.yaml
config/crawlers/46_montreal_public_sources.yaml
```

## Failure handling

If the validator reports `fail`, review the missing marker and update the relevant config before using the operator run commands.

# v13.36 - Export Case Scope Blockers

## Scope

This build extends case/scope enforcement into dossier export persistence and verification.

## Included

- Optional expected subject/case scope checks when persisting export packs
- Manifest scope matching helper for export verification
- Artifact-hash verification blocks when manifest subject/case does not match the requested scope
- Manifest/index verification now includes explicit manifest and index scope checks
- Export gate decisions deny tampered or mismatched export scope
- Regression tests for persist-time mismatch rejection, manifest tampering, and matching-scope allow decisions

## Operator Result

Exports can be written and verified only when their manifest subject and case match the requested export scope. Tampered or mismatched manifests are denied by the export gate instead of being treated as ordinary hash/index drift.

# v21.1 Import Approved Findings Package

Adds an explicit operator-visible import step for the current v20 approved or promoted findings package.

The import surface shows:

- source package identity
- declared and computed manifest hashes
- manifest verification status
- package freshness
- latest import actor, timestamp, and audit record
- clear blocked states when no valid package exists

The service records a separate immutable `case_dossier_package_import` audit event. The event captures the package id, manifest hash, finding count, verified import snapshot hash, and importing operator.

duplicate-import protection prevents a second audit event for the same package identity and manifest. When the current package differs from the latest imported identity, the workspace marks the import as stale and offers import of the newer package.

Routes:

- `GET /api/v1/dossier-assembly/<case_id>/package-import`
- `POST /api/v1/dossier-assembly/<case_id>/package-import`

The operator UI requires a verified current import before enabling arrangement controls. Legacy direct arrangement API calls remain compatible and return an import warning when no current import exists.

The existing `audit_logs` table is reused. Source package and finding records remain unchanged, and no migration is introduced.

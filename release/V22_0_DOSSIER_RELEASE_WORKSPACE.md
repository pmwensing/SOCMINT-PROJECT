# v22.0 Dossier Release Workspace

Loads the latest approved v21.6 export package and presents its approval record, integrity state, package identity, and export metadata in a release-preparation workspace.

The workspace provides authorized recipient and delivery-channel selection, release-readiness preview, explicit blockers, and a direct handoff link to the existing Case Delivery Workspace.

The release preview checks:

- generated v21.6 package availability
- approval-record presence
- required integrity hashes
- export package identity
- authorized recipient selection
- recipient-specific channel authorization

Routes:

- `GET /dossier-release/<case_id>`
- `GET /api/v1/dossier-release/<case_id>`
- `POST /api/v1/dossier-release/<case_id>/preview`

Recipient configuration may be supplied through `SOCMINT_AUTHORIZED_RECIPIENTS` as JSON. Supported preview channels are secure portal, encrypted email, and managed download, subject to recipient authorization.

This slice only previews and prepares release readiness. It connects to `/case-delivery?case_id=<case_id>` without transmitting, dispatching, or mutating the v21.6 package. No migration is introduced.

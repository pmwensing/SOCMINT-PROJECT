# v22.1 Recipient and Delivery Authorization

Adds a separate immutable authorization decision for the recipient and delivery channel selected in the v22.0 Dossier Release Workspace.

Authorization requires explicit operator confirmation and revalidates the selected recipient and channel against the current authorized-recipient catalog before recording anything.

Each immutable authorization records:

- authorizer identity
- authorization note
- selected recipient identity, organization, and role
- authorized delivery channel
- v21.6 export package identity and hash
- deterministic authorization id and hash
- authorization timestamp
- case-delivery workspace handoff payload

Route:

- `POST /api/v1/dossier-release/<case_id>/authorize`

The resulting record is consumable by the existing case-delivery workspace. It authorizes the handoff context without transmitting, dispatching, uploading, or mutating the dossier export package.

The existing audit log is reused, and no migration is introduced.

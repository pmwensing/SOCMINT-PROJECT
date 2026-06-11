# v15.6 Delivery Execution Envelope

The v15.6 layer adds the final case-delivery execution boundary:

- `POST /api/v1/case-delivery/<case_id>/execution-envelope`

The endpoint emits a compact execution envelope only after the v15.5 Delivery
Authorization Record authorizes the package and receipt chain. Tampered or
missing authorization records return a blocked result and do not emit an
envelope.

The envelope carries the case id, delivery id, package id, receipt id,
authorization id, authorized delivery links, manifest file count, canonical
payload hash, and deterministic execution id.

## Validation

- Focused regression coverage in `tests/test_v15_case_delivery_workspace.py`.

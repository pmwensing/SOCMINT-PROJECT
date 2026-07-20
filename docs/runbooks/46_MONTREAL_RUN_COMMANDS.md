# 46 Montreal Evidence Vault Run Commands

This runbook initializes and operates the private evidence-vault workflow for the 46 Montreal Street matter.

## Scope lock

SOCMINT-PROJECT is scope-locked to 46 Montreal Street and all entities directly involved in the 46 Montreal matter.

Included:

- 46 Montreal Street, 46 Montreal St, 46 Montreal, 46 Montréal, 46MONST
- Apt. B / Apartment B / Room 3 when tied to 46 Montreal
- directly involved people, businesses, owners, managers, contractors, inspectors, authorities, agencies, documents, orders, communications, events, and evidence connected to 46 Montreal

Relocation context:

- 559 Macdonnel is included only as suitable relocation / accommodation / mitigation context.

Excluded:

- 71 Cowdy, 71 Cowdy Street, 81 Cowdy, Cowdy Street
- unrelated personal history, unrelated business activity, unrelated disputes, credential/leak hunting, or unauthorized access

## Storage model

Raw evidence may be stored locally, on encrypted external drives, or in approved private cloud storage such as TeraBox, OneDrive, and Google Drive.

The private GitHub evidence repo is **not** the default raw-evidence vault. It is the manifest, hash, index, review, crawler-finding, redaction, timeline, dossier, and export-preparation layer.

## 1. Create the private evidence repo

Run from your normal development shell:

```bash
gh repo create pmwensing/46-montreal-evidence-private \
  --private \
  --description "Private evidence vault for the 46 Montreal Street matter" \
  --clone
```

## 2. Initialize the private evidence repo structure

From beside both repos:

```bash
cd 46-montreal-evidence-private
bash ../SOCMINT-PROJECT/scripts/case_46_montreal/init_evidence_repo.sh
```

Commit the initialized evidence-vault structure:

```bash
git add .
git commit -m "Initialize 46 Montreal private evidence vault"
git push -u origin main
```

## 3. Generate a SHA256 hash manifest for a local raw evidence vault

Windows Git Bash example:

```bash
bash ../SOCMINT-PROJECT/scripts/case_46_montreal/generate_hash_manifest.sh \
  "E:/46_Montreal_Evidence" \
  "00_manifest/HASH_MANIFEST.sha256"
```

Linux/macOS example:

```bash
bash ../SOCMINT-PROJECT/scripts/case_46_montreal/generate_hash_manifest.sh \
  "/mnt/e/46_Montreal_Evidence" \
  "00_manifest/HASH_MANIFEST.sha256"
```

## 4. Verify a hash manifest

```bash
bash ../SOCMINT-PROJECT/scripts/case_46_montreal/verify_hash_manifest.sh \
  "00_manifest/HASH_MANIFEST.sha256"
```

## 5. Register cloud storage locations

Edit:

```text
00_manifest/CLOUD_STORAGE_REGISTER.csv
```

Example rows:

```csv
CLOUD-GDRIVE-001,Google Drive,Personal Google Drive,/46_Montreal_Evidence,private,provider_encryption_plus_local_hashes,active,2026-07-03,cloud backup and document storage
CLOUD-ONEDRIVE-001,OneDrive,Personal OneDrive,/46_Montreal_Evidence,private,provider_encryption_plus_local_hashes,active,2026-07-03,cloud backup and working copy
CLOUD-TERABOX-001,TeraBox,Personal TeraBox,/46_Montreal_Evidence,private,provider_encryption_plus_local_hashes,active,2026-07-03,large-file backup storage
```

Avoid storing public or tokenized cloud share URLs in manifests unless needed for service/disclosure. Prefer provider, account label, folder path/file ID, and hash.

## 6. Register raw evidence locations

Use:

```text
00_manifest/EVIDENCE_LOCATION_MAP.csv
00_manifest/LOCAL_RAW_FILE_INDEX.csv
```

Each evidence item should have:

- evidence ID
- primary raw location
- cloud backup locations, if any
- SHA256 hash
- verification status
- derivative GitHub path, if any

## 7. Raw evidence approval rule

Raw unredacted files are not written to GitHub by default.

Before intentionally committing raw evidence or Git LFS objects, create an approval row in:

```text
00_manifest/RAW_EVIDENCE_APPROVAL_LOG.csv
```

Required approval fields:

- evidence ID assigned
- SHA256 hash registered
- PII review complete
- secret scan complete
- chain-of-custody event recorded
- backup verified
- operator approval recorded

## 8. Generate a crawler/search pack later

Crawler/search-pack execution should remain blocked until these gates exist in SOCMINT-PROJECT:

- case scope lock
- entity scope gate
- source allowlist
- robots/terms/public-access check
- no login bypass
- no credential/leak hunting
- human review before dossier/export

## 9. Service-volume output folders

The private evidence repo initializes these output folders:

```text
12_exports_service_volumes/physical_condition_photo_book/
12_exports_service_volumes/t2_guest_interference_documentary_exhibits/
12_exports_service_volumes/alarm_disturbance_safety_documentary_audio_exhibits/
12_exports_service_volumes/witness_statements/
12_exports_service_volumes/messages_emails_call_records/
12_exports_service_volumes/authority_entity_dossiers/
12_exports_service_volumes/ltb_disclosure_packages/
```

## 10. Final control statement

Every evidence item must be traceable by evidence ID, storage location, SHA256 hash, chain-of-custody event, review status, and disclosure/export status.

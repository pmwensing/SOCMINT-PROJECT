# v9.9.4 Final Release Verification Report

Generated: 2026-05-13T03:35:45.955833+00:00
Status: **pass**
Release: v9_9_4_verify_smoke_release

16/16 checks passed.

## Failures

- None

## Checks

### Required file exists: RELEASE_NOTES.md

- Key: `release_notes`
- Status: PASS

### Required file exists: FINAL_RELEASE_CHECKLIST.json

- Key: `checklist`
- Status: PASS

### Required file exists: PUBLISH_MANIFEST.json

- Key: `publish_manifest`
- Status: PASS

### Required file exists: INTEGRITY_MANIFEST.json

- Key: `integrity_manifest`
- Status: PASS

### Publish manifest status is published

- Key: `publish_manifest_published`
- Status: PASS

### Final gate is approved

- Key: `final_gate_approved`
- Status: PASS

### Integrity manifest is present and valid JSON

- Key: `integrity_manifest_present`
- Status: PASS

### Integrity manifest confirms required evidence presence

- Key: `integrity_required_presence`
- Status: PASS

### All integrity-manifest file SHA256 checks match

- Key: `integrity_file_checksums`
- Status: PASS

### Archive ZIP exists

- Key: `archive_zip_exists`
- Status: PASS

### Archive TAR.GZ exists

- Key: `archive_tar_exists`
- Status: PASS

### Archive ZIP checksum matches integrity seal when seal is available

- Key: `archive_zip_checksum`
- Status: PASS

### Archive TAR.GZ checksum matches integrity seal when seal is available

- Key: `archive_tar_checksum`
- Status: PASS

### ZIP contains required final release files

- Key: `zip_required_files`
- Status: PASS

### TAR.GZ contains required final release files

- Key: `tar_required_files`
- Status: PASS

### Package ZIPs referenced by publish manifest are present

- Key: `package_zips_present`
- Status: PASS

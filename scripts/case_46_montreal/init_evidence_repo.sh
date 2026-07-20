#!/usr/bin/env bash
set -euo pipefail

# Initialize the private evidence repository structure for the
# 46 Montreal Street matter.
#
# This script creates manifests, indexes, storage policy files,
# and disclosure/export folders. It does not collect evidence and
# does not upload raw evidence to GitHub.

mkdir -p \
  00_manifest \
  01_raw_evidence/{emails,attachments,photos,audio,video,documents} \
  02_gmail_exports/{threads,attachments,parsed_text} \
  03_city_orders_inspections/{property_standards,fire_inspection,building_orders,engineering,parsed_text} \
  04_fire_esa_ofm/{esa,fire_department,fire_inspection,ofm,notes,parsed_text} \
  05_ltb_filings/{t2_reasonable_enjoyment,t2_lockout,t6_maintenance,acc_orders,hearing_materials,service_records} \
  06_photos_video_audio/{extracted_metadata,thumbnails} \
  07_witness_messages_calls/{witness_statements,messages,call_records} \
  08_entity_dossiers/{people,businesses,authorities,addresses,contractors,inspectors,documents,orders} \
  09_timelines \
  10_crawler_findings/{search_packs,crawl_runs,warc_wacz,public_records,media_mentions,official_sources,business_registry_hits,rejected_out_of_scope} \
  11_ai_review/{relevance_scores,relationship_suggestions,contradiction_reports,causal_hypotheses,intent_hypotheses,missing_evidence,analyst_decisions} \
  12_exports_service_volumes/{physical_condition_photo_book,t2_guest_interference_documentary_exhibits,alarm_disturbance_safety_documentary_audio_exhibits,witness_statements,messages_emails_call_records,authority_entity_dossiers,ltb_disclosure_packages} \
  99_redacted_public/{redacted_pdfs,redacted_images,redacted_audio_transcripts,public_summary_exports}

cat > README.md <<'EOF'
# 46 Montreal Evidence Vault

Private evidence repository for the 46 Montreal Street matter.

Scope:
- 46 Montreal Street and all entities directly involved in the 46 Montreal matter.
- Included entities may include people, businesses, owners, managers, contractors, authorities, inspectors, documents, orders, communications, and events directly connected to 46 Montreal.
- 559 Macdonnel is included only as suitable relocation / mitigation context.
- Cowdy addresses are excluded from issue analysis.

Storage model:
- Raw evidence may be stored locally, on encrypted external drives, or in approved private cloud storage such as TeraBox, OneDrive, and Google Drive.
- This private GitHub repo is the manifest/index/review/export layer, not the default raw-evidence vault.

Core rules:
- Preserve raw evidence.
- Hash every evidence file.
- Summaries must cite source files and evidence IDs.
- AI output is review assistance only.
- Do not store unrelated personal records or unrelated housing complaints.
EOF

cat > 00_manifest/STORAGE_POLICY.md <<'EOF'
# Raw Evidence Storage Policy

SOCMINT-PROJECT uses a multi-location raw evidence model.

Raw unredacted evidence is stored locally and/or in approved private cloud storage by default.

Approved raw evidence locations:
- local encrypted evidence vault
- encrypted external backup
- TeraBox
- OneDrive
- Google Drive

The private GitHub evidence repo stores:
- manifests
- hashes
- evidence IDs
- local/cloud storage references
- OCR/text extracts when safe
- metadata extracts
- redacted copies
- thumbnails when safe
- summaries
- AI review output
- crawler findings
- timelines
- entity dossiers
- disclosure/export packages

GitHub is not the default source of truth for raw unredacted originals.

Raw originals may be copied into GitHub or Git LFS only after:
1. evidence ID assignment,
2. SHA256 hash registration,
3. privacy review,
4. repository safety review,
5. chain-of-custody entry,
6. backup confirmation,
7. explicit operator approval.

Cloud share links must not be public.
Cloud share links must not be placed in public repos.
Where possible, store provider, folder path, file name, file ID, and hash instead of public share URLs.

The source of truth for each evidence item is determined by:
- evidence ID,
- SHA256 hash,
- original storage location,
- chain-of-custody log,
- backup verification status.
EOF

cat > 00_manifest/SCOPE_LOCK.md <<'EOF'
# Scope Lock

SOCMINT-PROJECT is scope-locked to 46 Montreal Street and all entities directly involved in the 46 Montreal matter.

Included:
- 46 Montreal Street
- 46 Montreal St
- 46 Montreal
- 46 Montréal
- 46MONST
- Apt B / Apartment B / Room 3 when tied to 46 Montreal
- directly involved people, businesses, authorities, contractors, inspectors, documents, orders, communications, and events

Relocation Context:
- 559 Macdonnel only as suitable relocation / mitigation context.

Excluded:
- 71 Cowdy
- 71 Cowdy Street
- 81 Cowdy
- Cowdy Street

Expansion Rule:
The system may map and analyze entities only to the extent their actions, roles, records, communications, ownership, inspection activity, repair activity, enforcement activity, or decision-making relate to 46 Montreal Street.
EOF

cat > 00_manifest/EVIDENCE_REGISTER.csv <<'EOF'
evidence_id,date_received,date_of_event,source,source_type,file_path,hash_sha256,case_issue,entities,summary,review_status,disclosure_status,notes
EOF

cat > 00_manifest/CHAIN_OF_CUSTODY.csv <<'EOF'
item_id,file_path,original_source,collected_by,date_collected,method,hash_sha256,stored_location,changes_made,notes
EOF

cat > 00_manifest/CHAIN_OF_CUSTODY_EVENTS.csv <<'EOF'
event_id,evidence_id,event_type,timestamp,operator,source_location_id,source_path,destination_location_id,destination_path,old_hash,new_hash,tool_used,notes
EOF

cat > 00_manifest/LOCAL_RAW_FILE_INDEX.csv <<'EOF'
raw_id,evidence_id,local_path,file_name,file_type,hash_sha256,date_collected,source,backup_location,github_derivative_path,notes
EOF

cat > 00_manifest/CLOUD_STORAGE_REGISTER.csv <<'EOF'
cloud_location_id,provider,account_label,folder_path,access_type,encryption_status,sync_status,last_verified,notes
EOF

cat > 00_manifest/EVIDENCE_LOCATION_MAP.csv <<'EOF'
evidence_id,primary_raw_location_type,primary_raw_location_id,primary_raw_path,cloud_location_ids,github_manifest_path,github_derivative_paths,hash_sha256,verified,verification_date,notes
EOF

cat > 00_manifest/BACKUP_VERIFICATION_LOG.csv <<'EOF'
verification_id,evidence_id,location_id,provider,path_checked,hash_expected,hash_found,match,checked_by,checked_at,notes
EOF

cat > 00_manifest/SYNC_CONFLICT_LOG.csv <<'EOF'
conflict_id,evidence_id,provider,path_a,path_b,hash_a,hash_b,detected_at,resolution,reviewed_by,notes
EOF

cat > 00_manifest/RAW_EVIDENCE_APPROVAL_LOG.csv <<'EOF'
approval_id,evidence_id,file_path,proposed_destination,reason,privacy_review_done,repo_safety_review_done,hash_registered,backup_verified,approved_by,approved_at,notes
EOF

cat > 00_manifest/ENTITY_REGISTER.csv <<'EOF'
entity_id,entity_type,name,aliases,role_in_46_montreal_matter,source_evidence_ids,confidence,review_status,allowed_scope,notes
EOF

cat > 00_manifest/SOURCE_REGISTER.csv <<'EOF'
source_id,source_name,source_type,access_method,allowed_scope,robots_checked,terms_risk,privacy_risk,last_checked,notes
EOF

cat > 00_manifest/DISCLOSURE_STATUS.csv <<'EOF'
evidence_id,file_path,disclosure_volume,redaction_required,served,served_date,method,notes
EOF

cat > 00_manifest/REVIEW_DECISIONS.csv <<'EOF'
review_id,item_id,item_type,decision,reviewer,date,reason,export_allowed,notes
EOF

cat > 00_manifest/ACCESS_REVIEW_LOG.csv <<'EOF'
access_event_id,item_id,location_or_link,access_type,shared_with,purpose,created_at,expires_at,revoked_at,reviewed_by,notes
EOF

cat > 00_manifest/REDACTION_REGISTER.csv <<'EOF'
redaction_id,evidence_id,source_path,redacted_path,redaction_reason,privacy_level,reviewed_by,created_at,notes
EOF

cat > 00_manifest/HASH_MANIFEST.sha256 <<'EOF'
# Generated by scripts/case_46_montreal/generate_hash_manifest.sh
EOF

cat > .gitignore <<'EOF'
.env
*.key
*.pem
*.p12
*.pfx
private_config/
private_material/
__pycache__/
.DS_Store
Thumbs.db
EOF

cat > .gitattributes <<'EOF'
*.pdf filter=lfs diff=lfs merge=lfs -text
*.mp3 filter=lfs diff=lfs merge=lfs -text
*.m4a filter=lfs diff=lfs merge=lfs -text
*.mp4 filter=lfs diff=lfs merge=lfs -text
*.mov filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text
*.jpeg filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
*.zip filter=lfs diff=lfs merge=lfs -text
EOF

printf 'Initialized 46 Montreal evidence vault structure.\n'
printf 'Next: git add . && git commit -m "Initialize 46 Montreal private evidence vault"\n'

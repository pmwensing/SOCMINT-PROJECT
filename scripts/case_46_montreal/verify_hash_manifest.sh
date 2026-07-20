#!/usr/bin/env bash
set -euo pipefail

MANIFEST="${1:-00_manifest/HASH_MANIFEST.sha256}"

if [[ ! -f "$MANIFEST" ]]; then
  echo "Hash manifest not found: $MANIFEST" >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum -c "$MANIFEST"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 -c "$MANIFEST"
else
  echo "No SHA256 verification tool found. Install sha256sum or shasum." >&2
  exit 2
fi

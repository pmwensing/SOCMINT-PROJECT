#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-}"
OUT="${2:-00_manifest/HASH_MANIFEST.sha256}"

if [[ -z "$ROOT" ]]; then
  echo "Usage: $0 <evidence-root> [output-file]" >&2
  exit 1
fi

if [[ ! -d "$ROOT" ]]; then
  echo "Evidence root not found: $ROOT" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUT")"

if command -v sha256sum >/dev/null 2>&1; then
  HASH_CMD=(sha256sum)
elif command -v shasum >/dev/null 2>&1; then
  HASH_CMD=(shasum -a 256)
else
  echo "No SHA256 tool found. Install sha256sum or shasum." >&2
  exit 3
fi

find "$ROOT" -type f \
  ! -path '*/.git/*' \
  ! -path '*/node_modules/*' \
  ! -path '*/__pycache__/*' \
  -print0 \
  | sort -z \
  | xargs -0 "${HASH_CMD[@]}" > "$OUT"

printf 'Wrote hash manifest: %s\n' "$OUT"

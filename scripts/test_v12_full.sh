#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12 full regression gate"
TARGETS=(
  test-v12-3-1
  test-v12-3-2
  test-v12-5
  test-v12-5-1
  test-v12-6
  test-v12-6-1
  test-v12-7
  test-v12-7-1
  test-v12-8
  test-v12-8-1
  test-v12-9
  test-v12-9-1
  test-v12-10
)

for target in "${TARGETS[@]}"; do
  echo "[+] Running ${target}"
  make -f GNUmakefile "${target}"
done

echo "PASS v12 full regression gate"

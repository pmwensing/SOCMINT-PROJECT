#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/pmwensing/SOCMINT-PROJECT.git}"
BRANCH="${BRANCH:-master}"
WORK_ROOT="${WORK_ROOT:-/tmp/socmint-v13-33-clean-install}"
PROJECT_DIR="$WORK_ROOT/SOCMINT-PROJECT"
ADMIN_PASSWORD="${SOCMINT_ADMIN_PASSWORD:-LocalTest-41b555e7b1793c6f3ade1e13!Aa1}"
SECRET_KEY="${SOCMINT_SECRET_KEY:-CleanInstall-v13-33-Secret-Key-Change-Me-1234567890}"

rm -rf "$WORK_ROOT"
mkdir -p "$WORK_ROOT"

echo "[+] Clean clone $REPO_URL#$BRANCH"
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo "[+] Write local acceptance env"
cat > .env <<EOF
SOCMINT_SECRET_KEY=$SECRET_KEY
SOCMINT_ADMIN_USER=admin
SOCMINT_ADMIN_PASSWORD=$ADMIN_PASSWORD
SOCMINT_ALLOW_SIGNUP=false
SOCMINT_DATA_DIR=/var/lib/socmint
SOCMINT_LOG_FILE=/var/lib/socmint/socmint.log
EOF

echo "[+] Build and run clean install"
docker compose build --no-cache app
docker compose up -d --force-recreate

echo "[+] Wait for healthy"
for i in {1..90}; do
  cid="$(docker compose ps -q app 2>/dev/null || true)"
  status="unknown"
  if [ -n "$cid" ]; then
    status="$(docker inspect -f '{{.State.Health.Status}}' "$cid" 2>/dev/null || true)"
  fi
  echo "app health: ${status:-unknown}"
  [ "$status" = "healthy" ] && break
  sleep 2
done

bash scripts/runtime_acceptance_v13_33.sh

echo "[+] Clean install acceptance complete: $PROJECT_DIR"

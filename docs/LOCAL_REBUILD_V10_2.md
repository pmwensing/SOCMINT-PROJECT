# SOCMINT v10.2 Local Rebuild Guide

## Clean rebuild

```bash
git clone https://github.com/pmwensing/SOCMINT-PROJECT.git SOCMINT-PROJECT-v10.2
cd SOCMINT-PROJECT-v10.2
git checkout master
cp .env.production.example .env.production
nano .env.production
bash scripts/install_production.sh
```

## Start locally

```bash
set -a
source .env.production
set +a
make serve
```

## Validate

```bash
make lint
make test
make backup-restore-smoke
make production-smoke
```

## Review admin readiness endpoints

- `/api/v1/admin/installer/readiness/summary`
- `/api/v1/admin/release-integrity/summary`
- `/api/v1/admin/certification/summary`

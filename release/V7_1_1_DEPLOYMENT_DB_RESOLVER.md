# SOCMINT v7.1.1 — Deployment DB URL Resolver + Migration Runner

Adds a safe deployment database resolver and migration runner.

Commands:
PYTHONPATH=$PWD/src python3 -m socmint.deployment_db resolve --json
PYTHONPATH=$PWD/src python3 -m socmint.deployment_db write-env --output .env.deployment.local
PYTHONPATH=$PWD/src python3 -m socmint.deployment_db dry-run
PYTHONPATH=$PWD/src python3 -m socmint.deployment_db migrate

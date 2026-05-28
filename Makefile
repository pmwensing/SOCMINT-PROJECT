PYTHON=./venv/bin/python
PIP=./venv/bin/pip

.PHONY: all venv install install-prod install-scanners test migrate serve serve-prod process-jobs clean lint format precommit-install secrets backup-restore-smoke production-smoke production-docker-smoke ci connectors-health connectors-health-json install-connectors

all: install

venv:
	python3 -m venv venv
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install -r requirements-dev.txt

install-prod: venv
	$(PIP) install -r requirements-prod.txt

install-scanners: venv
	$(PIP) install -r requirements-scanners.txt

test: install
	$(PYTHON) -m pytest tests/ -q

migrate: install
	$(PYTHON) -m alembic upgrade head

serve: install
	$(PYTHON) -m src.socmint.main --serve

serve-prod: install
	./venv/bin/gunicorn --bind 127.0.0.1:5000 src.socmint.wsgi:app

process-jobs: install
	$(PYTHON) -m src.socmint.main process-jobs --max-jobs=$${MAX_JOBS:-1}

connectors-health:
	@PYTHONPATH=$(PWD)/src python3 -m socmint.connector_runtime_health_cli

connectors-health-json:
	@PYTHONPATH=$(PWD)/src python3 -m socmint.connector_runtime_health_cli --json

install-connectors:
	bash ./scripts/install_connector_runtime_v7_6_0.sh

lint: install
	./venv/bin/ruff check src tests scripts

format: install
	./venv/bin/ruff check --fix src tests scripts

precommit-install: install
	@if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then \
		TOPLEVEL=$$(git rev-parse --show-toplevel); \
		if [ "$$TOPLEVEL" != "$$PWD" ]; then \
			echo "error: this directory is inside a parent Git repository ($$TOPLEVEL)."; \
			echo "Please use a standalone checkout before running make precommit-install."; \
			exit 1; \
		fi; \
		echo "Git repository already initialized."; \
	elif [ -d .git ]; then \
		echo "Git repository already initialized in this directory."; \
	else \
		echo "Git repository not found. Initializing Git repository..."; \
		git init; \
	fi
	./venv/bin/pre-commit install

secrets: install-prod
	$(PYTHON) -m src.socmint.main generate-secrets

backup-restore-smoke: install-prod
	$(PYTHON) scripts/backup_restore_smoke.py

production-smoke: install-prod
	$(PYTHON) scripts/production_boot_check.py

production-docker-smoke: install-prod
	$(PYTHON) scripts/production_docker_smoke.py

ci: install
	./venv/bin/ruff check src tests scripts
	./venv/bin/pre-commit run --all-files
	./venv/bin/pytest -q
	@if [ ! -f .env ]; then cp .env.example .env; rm_env=1; fi; \
	 docker compose --env-file .env.example config; \
	 docker compose --env-file .env.example --profile postgres config; \
	 docker compose --env-file .env.example --profile worker config; \
	 if [ "$$rm_env" = "1" ]; then rm -f .env; fi
	rm -rf /tmp/socmint-ci
	mkdir -p /tmp/socmint-ci
	DATABASE_URL=sqlite:////tmp/socmint-ci/socmint.db SOCMINT_DATA_DIR=/tmp/socmint-ci SOCMINT_AUTO_CREATE_DB=false ./venv/bin/alembic upgrade head
	./venv/bin/pip-audit -r requirements.lock

clean:
	rm -rf __pycache__ src/socmint/__pycache__ tests/__pycache__ .pytest_cache

include Makefile.releases

test-v12-10-22:
	PYTHONPATH=src python3 scripts/real_world_audit_smoke_v12_10_22.py
	PYTHONPATH=src pytest -q tests/test_real_world_audit_v12_10_22.py

zip-v12-10-22:
	cd .. && zip -r SOCMINT-PROJECT-v12.10.22-real-world-audit-plan.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/.env'

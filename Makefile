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

test71:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_1.sh

zip71:
	cd .. && zip -r SOCMINT-PROJECT-v7.1.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/.venv/*' -x 'SOCMINT-PROJECT/venv/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/var/*' -x 'SOCMINT-PROJECT/.env'


test711:
	PYTHONPATH=$(PWD)/src pytest -q tests/test_deployment_db_v7_1_1.py
	PYTHONPATH=$(PWD)/src ./scripts/v7_1_1_migration_runner.sh


migrate711:
	PYTHONPATH=$(PWD)/src python3 -m socmint.deployment_db migrate


test72:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_2.sh


test721:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_2_1.sh


migrate721:
	PYTHONPATH=$(PWD)/src python3 -m socmint.deployment_db migrate

test722:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_2_2.sh

migrate722:
	PYTHONPATH=$(PWD)/src python3 -m socmint.deployment_db migrate

test73:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_3.sh

test731:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_3_1.sh

test732:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_3_2.sh

test74:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_4.sh

test741:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_4_1.sh

test742:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_4_2.sh

test743:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_4_3.sh


test75:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_5.sh


test751:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_5_1.sh

zip751:
	cd .. && zip -r SOCMINT-PROJECT-v7.5.1.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/.venv/*' -x 'SOCMINT-PROJECT/venv/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/var/*' -x 'SOCMINT-PROJECT/.env'


test752:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_5_2.sh

zip752:
	cd .. && zip -r SOCMINT-PROJECT-v7.5.2.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/.venv/*' -x 'SOCMINT-PROJECT/venv/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/var/*' -x 'SOCMINT-PROJECT/.env'


test753:
	PYTHONPATH=$(PWD)/src ./scripts/test_v7_5_3.sh

zip753:
	cd .. && zip -r SOCMINT-PROJECT-v7.5.3.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/.venv/*' -x 'SOCMINT-PROJECT/venv/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/var/*' -x 'SOCMINT-PROJECT/.env'


test754:
	PYTHONPATH=$(PWD)/src bash ./scripts/test_v7_5_4.sh

zip754:
	cd .. && zip -r SOCMINT-PROJECT-v7.5.4.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/.venv/*' -x 'SOCMINT-PROJECT/venv/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/var/*' -x 'SOCMINT-PROJECT/.env'


test755:
	PYTHONPATH=$(PWD)/src bash ./scripts/test_v7_5_5.sh

zip755:
	cd .. && zip -r SOCMINT-PROJECT-v7.5.5.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/.venv/*' -x 'SOCMINT-PROJECT/venv/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/var/*' -x 'SOCMINT-PROJECT/.env'


test756:
	PYTHONPATH=$(PWD)/src bash ./scripts/test_v7_5_6.sh

zip756:
	cd .. && zip -r SOCMINT-PROJECT-v7.5.6.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/.venv/*' -x 'SOCMINT-PROJECT/venv/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/var/*' -x 'SOCMINT-PROJECT/.env'


test757:
	PYTHONPATH=$(PWD)/src bash ./scripts/test_v7_5_7.sh

zip757:
	cd .. && zip -r SOCMINT-PROJECT-v7.5.7.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/.venv/*' -x 'SOCMINT-PROJECT/venv/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/var/*' -x 'SOCMINT-PROJECT/.env'


test758:
	PYTHONPATH=$(PWD)/src bash ./scripts/test_v7_5_8.sh

zip758:
	cd .. && zip -r SOCMINT-PROJECT-v7.5.8.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/.venv/*' -x 'SOCMINT-PROJECT/venv/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/var/*' -x 'SOCMINT-PROJECT/.env'


test759:
	PYTHONPATH=$(PWD)/src bash ./scripts/test_v7_5_9.sh

zip759:
	cd .. && zip -r SOCMINT-PROJECT-v7.5.9.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/.venv/*' -x 'SOCMINT-PROJECT/venv/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/var/*' -x 'SOCMINT-PROJECT/.env'


test760:
	PYTHONPATH=$(PWD)/src bash ./scripts/test_v7_6_0.sh

zip760:
	cd .. && zip -r SOCMINT-PROJECT-v7.6.0.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/.venv/*' -x 'SOCMINT-PROJECT/venv/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/.env' -x 'SOCMINT-PROJECT/.connector-tools/*'


test761:
	PYTHONPATH=$(PWD)/src bash ./scripts/test_v7_6_1.sh

zip761:
	cd .. && zip -r SOCMINT-PROJECT-v7.6.1.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/.venv/*' -x 'SOCMINT-PROJECT/venv/*' -x 'SOCMINT-PROJECT/.pytest_cache/*' -x 'SOCMINT-PROJECT/.env' -x 'SOCMINT-PROJECT/.connector-tools/*'


product-smoke:
	python3 scripts/product_qa_v9_7_4.py

test971:
	python3 -c "from src.socmint.product_control_center import build_status; import json; print(json.dumps(build_status(), indent=2))"

test972:
	python3 -c "from src.socmint.dossier_quality_gate import dossier_quality_gate; import json; print(json.dumps(dossier_quality_gate('demo-subject'), indent=2))"

test973:
	python3 -c "from src.socmint.dossier_traceability import evidence_to_dossier_traceability; import json; print(json.dumps(evidence_to_dossier_traceability('demo-subject'), indent=2))"

prepare98:
	python3 scripts/prepare_v9_8_productized_release.py


product-route-smoke:
	PYTHONPATH=src python3 scripts/product_route_smoke_v9_8_1.py

test981:
	PYTHONPATH=src python3 scripts/product_route_smoke_v9_8_1.py

release-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_hardening_smoke_v9_8_1.py

zip981:
	cd .. && zip -r SOCMINT-PROJECT-v9.8.1-release-hardening.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-ux-smoke:
	PYTHONPATH=src python3 scripts/product_ux_smoke_v9_8_2.py

test982:
	PYTHONPATH=src python3 scripts/product_ux_smoke_v9_8_2.py

ux-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_ux_hardening_v9_8_2.py

zip982:
	cd .. && zip -r SOCMINT-PROJECT-v9.8.2-product-control-ux.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-runtime-actions-smoke:
	PYTHONPATH=src python3 scripts/product_runtime_actions_smoke_v9_8_3.py

test983:
	PYTHONPATH=src python3 scripts/product_runtime_actions_smoke_v9_8_3.py

runtime-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_runtime_hardening_v9_8_3.py

zip983:
	cd .. && zip -r SOCMINT-PROJECT-v9.8.3-product-runtime-actions.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-artifacts-smoke:
	PYTHONPATH=src python3 scripts/product_artifacts_smoke_v9_8_4.py

test984:
	PYTHONPATH=src python3 scripts/product_artifacts_smoke_v9_8_4.py

artifact-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_artifacts_hardening_v9_8_4.py

zip984:
	cd .. && zip -r SOCMINT-PROJECT-v9.8.4-product-artifact-browser.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-artifact-review-smoke:
	PYTHONPATH=src python3 scripts/product_artifact_review_smoke_v9_8_5.py

test985:
	PYTHONPATH=src python3 scripts/product_artifact_review_smoke_v9_8_5.py

artifact-review-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_artifact_review_hardening_v9_8_5.py

zip985:
	cd .. && zip -r SOCMINT-PROJECT-v9.8.5-product-artifact-review.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-artifact-review-audit-smoke:
	PYTHONPATH=src python3 scripts/product_artifact_review_audit_smoke_v9_8_6.py

test986:
	PYTHONPATH=src python3 scripts/product_artifact_review_audit_smoke_v9_8_6.py

artifact-review-audit-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_artifact_review_audit_hardening_v9_8_6.py

zip986:
	cd .. && zip -r SOCMINT-PROJECT-v9.8.6-product-artifact-review-audit.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-artifact-export-manifest-smoke:
	PYTHONPATH=src python3 scripts/product_artifact_export_manifest_smoke_v9_8_7.py

test987:
	PYTHONPATH=src python3 scripts/product_artifact_export_manifest_smoke_v9_8_7.py

export-manifest-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_artifact_export_manifest_hardening_v9_8_7.py

zip987:
	cd .. && zip -r SOCMINT-PROJECT-v9.8.7-product-artifact-evidence-chain.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-release-package-smoke:
	PYTHONPATH=src python3 scripts/product_release_package_smoke_v9_8_8.py

test988:
	PYTHONPATH=src python3 scripts/product_release_package_smoke_v9_8_8.py

release-package-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_release_package_hardening_v9_8_8.py

zip988:
	cd .. && zip -r SOCMINT-PROJECT-v9.8.8-product-release-package-builder.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-release-package-zip-smoke:
	PYTHONPATH=src python3 scripts/product_release_package_zip_smoke_v9_8_9.py

test989:
	PYTHONPATH=src python3 scripts/product_release_package_zip_smoke_v9_8_9.py

release-package-zip-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_release_package_zip_hardening_v9_8_9.py

zip989:
	cd .. && zip -r SOCMINT-PROJECT-v9.8.9-product-release-package-zip.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-release-candidate-smoke:
	PYTHONPATH=src python3 scripts/product_release_candidate_smoke_v9_9_0.py

test990:
	PYTHONPATH=src python3 scripts/product_release_candidate_smoke_v9_9_0.py

release-candidate-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_release_candidate_hardening_v9_9_0.py

zip990:
	cd .. && zip -r SOCMINT-PROJECT-v9.9.0-product-release-candidate-console.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-final-gate-smoke:
	PYTHONPATH=src python3 scripts/product_final_gate_smoke_v9_9_1.py

test991:
	PYTHONPATH=src python3 scripts/product_final_gate_smoke_v9_9_1.py

final-gate-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_final_gate_hardening_v9_9_1.py

zip991:
	cd .. && zip -r SOCMINT-PROJECT-v9.9.1-final-product-gate.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-final-release-smoke:
	PYTHONPATH=src python3 scripts/product_final_release_smoke_v9_9_2.py

test992:
	PYTHONPATH=src python3 scripts/product_final_release_smoke_v9_9_2.py

final-release-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_final_release_hardening_v9_9_2.py

zip992:
	cd .. && zip -r SOCMINT-PROJECT-v9.9.2-final-release-publisher.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-final-release-archive-smoke:
	PYTHONPATH=src python3 scripts/product_final_release_archive_smoke_v9_9_3.py

test993:
	PYTHONPATH=src python3 scripts/product_final_release_archive_smoke_v9_9_3.py

final-release-archive-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_final_release_archive_hardening_v9_9_3.py

zip993:
	cd .. && zip -r SOCMINT-PROJECT-v9.9.3-final-release-archive-integrity.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-final-release-verify-smoke:
	PYTHONPATH=src python3 scripts/product_final_release_verify_smoke_v9_9_4.py

test994:
	PYTHONPATH=src python3 scripts/product_final_release_verify_smoke_v9_9_4.py

final-release-verify-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_final_release_verify_hardening_v9_9_4.py

zip994:
	cd .. && zip -r SOCMINT-PROJECT-v9.9.4-final-release-verification-console.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-distribution-readiness-smoke:
	PYTHONPATH=src python3 scripts/product_distribution_readiness_smoke_v9_9_5.py

test995:
	PYTHONPATH=src python3 scripts/product_distribution_readiness_smoke_v9_9_5.py

distribution-readiness-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_distribution_readiness_hardening_v9_9_5.py

zip995:
	cd .. && zip -r SOCMINT-PROJECT-v9.9.5-distribution-readiness.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-final-dashboard-smoke:
	PYTHONPATH=src python3 scripts/product_final_dashboard_smoke_v9_9_6.py

test996:
	PYTHONPATH=src python3 scripts/product_final_dashboard_smoke_v9_9_6.py

final-product-dashboard-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_final_dashboard_hardening_v9_9_6.py

zip996:
	cd .. && zip -r SOCMINT-PROJECT-v9.9.6-final-product-dashboard.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'


product-operator-handoff-smoke:
	PYTHONPATH=src python3 scripts/product_operator_handoff_smoke_v9_9_7.py

test997:
	PYTHONPATH=src python3 scripts/product_operator_handoff_smoke_v9_9_7.py

operator-handoff-hardening-smoke:
	PYTHONPATH=src python3 scripts/product_operator_handoff_hardening_v9_9_7.py

zip997:
	cd .. && zip -r SOCMINT-PROJECT-v9.9.7-operator-handoff.zip SOCMINT-PROJECT -x 'SOCMINT-PROJECT/.git/*' -x 'SOCMINT-PROJECT/storage/*' -x 'SOCMINT-PROJECT/__pycache__/*'

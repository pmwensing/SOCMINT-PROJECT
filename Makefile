PYTHON=./venv/bin/python
PIP=./venv/bin/pip

.PHONY: all venv install test migrate serve serve-prod clean

all: install

venv:
	python3 -m venv venv
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install -r requirements.txt

test: install
	$(PYTHON) -m pytest tests/ -q

migrate: install
	$(PYTHON) -m alembic upgrade head

serve: install
	$(PYTHON) -m src.socmint.main --serve

serve-prod: install
	./venv/bin/gunicorn --bind 127.0.0.1:5000 src.socmint.wsgi:app

lint: install
	./venv/bin/ruff check src tests

format: install
	./venv/bin/ruff check --fix src tests

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

clean:
	rm -rf __pycache__ src/socmint/__pycache__ tests/__pycache__ .pytest_cache

# Makefile — dev convenience for python-clean-hex-bff-api.
# Run `make help` to list targets.
#
# Override interpreter / environment without editing this file:
#   make install PYTHON=python3.12   -> build the venv with a specific interpreter
#   make test    VENV=/path/to/env   -> use an existing environment
#   make test    PY=python3          -> bypass the venv (system python)
#   make run     PORT=9000           -> override the port
#
# NOTE: keep variable assignments free of trailing inline comments — Make keeps
# the spaces before a '#' as part of the value, which corrupts the paths.

PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin
PY ?= $(BIN)/python
PORT ?= 8080

.DEFAULT_GOAL := help
.PHONY: help venv install run test check lint format openapi clean

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

$(PY): ## Create the venv if its interpreter is missing
	$(PYTHON) -m venv $(VENV)

venv: $(PY) ## Create the virtualenv (alias)

install: $(PY) ## Install runtime + dev dependencies
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

run: ## Run the API with autoreload (PORT=8080 by default)
	$(PY) -m uvicorn app.main:app --reload --port $(PORT)

test: ## Run unit tests
	$(PY) -m pytest -q

check: lint test ## Lint + run tests (CI gate)

lint: ## Lint with ruff
	$(PY) -m ruff check .

format: ## Auto-format with ruff
	$(PY) -m ruff format .

openapi: ## Export the OpenAPI schema to openapi.json
	$(PY) -c "import json, app.main; open('openapi.json','w').write(json.dumps(app.main.app.openapi(), indent=2))"

clean: ## Remove caches and the exported schema
	rm -rf .pytest_cache openapi.json
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .ruff_cache -prune -exec rm -rf {} +

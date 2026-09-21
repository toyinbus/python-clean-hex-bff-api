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
# Defaults come from .env via pydantic-settings (REST_API_HOST / REST_API_PORT).
# One-off override: make run PORT=9000
_REST_PORT := $(shell $(PY) -c "from app.pkg.config.config import Config; print(Config().REST_API_PORT)" 2>/dev/null)
_REST_HOST := $(shell $(PY) -c "from app.pkg.config.config import Config; print(Config().REST_API_HOST)" 2>/dev/null)
PORT ?= $(if $(_REST_PORT),$(_REST_PORT),8080)
HOST ?= $(if $(_REST_HOST),$(_REST_HOST),0.0.0.0)

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

run: ## Run the API with autoreload (reads REST_API_* from .env; override with PORT=)
	$(PY) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

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

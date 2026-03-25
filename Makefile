.PHONY: up down remove local-up local-down stack-up stack-down test lint typecheck policy-test helm-validate release-bundle bootstrap health ps logs smoke install-opa

# Canonical public install path: install/bootstrap.sh (or install/bootstrap.ps1 on Windows).
# This Makefile is kept as a source-checkout convenience wrapper for contributors.

ifeq ($(OS),Windows_NT)
VENV_PYTHON := .venv/Scripts/python.exe
DEFAULT_PYTHON := py -3
DEV_NULL := NUL
else
VENV_PYTHON := .venv/bin/python
DEFAULT_PYTHON := python3
DEV_NULL := /dev/null
endif

PYTHON ?= $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),$(DEFAULT_PYTHON))
CLI_RUNNER ?= $(PYTHON) -m frontier_tooling.cli
OPA_RUNNER ?= $(PYTHON) scripts/run_opa.py
SECURE_ENV_FILE := $(strip $(shell "$(PYTHON)" -c "from frontier_tooling.common import ensure_compose_env_file; print(ensure_compose_env_file(local_profile=False))"))
LIGHTWEIGHT_ENV_FILE := $(strip $(shell "$(PYTHON)" -c "from frontier_tooling.common import ensure_compose_env_file; print(ensure_compose_env_file(local_profile=True))"))
LOCAL_COMPOSE ?= docker compose --env-file $(LIGHTWEIGHT_ENV_FILE) -f docker-compose.local.yml
FULL_COMPOSE ?= docker compose --env-file $(SECURE_ENV_FILE)

up:             ## Start all services
	$(CLI_RUNNER) up

down:           ## Stop all services
	$(CLI_RUNNER) down

remove:         ## Tear down local install and delete installer-managed env files
	$(CLI_RUNNER) remove

local-up:       ## Start the lightweight local-first stack
	$(CLI_RUNNER) local-up

local-down:     ## Stop the lightweight local-first stack
	$(CLI_RUNNER) local-down

stack-up:       ## Start the full platform stack (gateway, sandbox, policy infra)
	$(CLI_RUNNER) stack-up

stack-down:     ## Stop the full platform stack
	$(CLI_RUNNER) stack-down

test:           ## Run all tests
	pytest apps/backend/tests tests -v --cov=app --cov=frontier_runtime --cov-report=term-missing

lint:           ## Lint and format
	ruff check . --fix
	ruff format .

typecheck:      ## Type check
	mypy frontier_tooling/ frontier_runtime/

policy-test:    ## Test OPA policies
	$(OPA_RUNNER) test policies/ -v

helm-validate:  ## Validate Helm chart manifests (requires helm)
	helm lint ./helm/lattix-frontier
	helm template lattix ./helm/lattix-frontier -f helm/lattix-frontier/values-prod.yaml > $(DEV_NULL)

release-bundle: ## Build a local release bundle (requires VERSION and helm)
	@test -n "$(VERSION)" || (echo "VERSION is required, e.g. make release-bundle VERSION=v0.1.0" && exit 1)
	mkdir -p dist/chart dist/installer
	helm package helm/lattix-frontier --destination dist/chart
	cp install/bootstrap.sh dist/installer/
	cp install/bootstrap.ps1 dist/installer/
	cp install/frontier-installer.py dist/installer/
	cp install/manifest.json dist/installer/
	$(PYTHON) scripts/build_release_bundle.py --version "$(VERSION)" --repo "local-worktree" --chart-dist dist/chart --installer-dist dist/installer --output-root dist/release

install-opa:    ## Install repo-local OPA binary (Windows helper remains available too)
	@echo "Install OPA with .\\scripts\\frontier.ps1 install-opa on Windows, or place the binary at .tools/opa/opa(.exe)."

bootstrap:      ## First-time setup
	$(CLI_RUNNER) bootstrap

health:         ## Check API health endpoint
	$(CLI_RUNNER) health

ps:
	$(CLI_RUNNER) ps

logs:
	$(CLI_RUNNER) logs

smoke:
	$(CLI_RUNNER) smoke


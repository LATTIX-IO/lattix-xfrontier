.PHONY: up down local-up local-down stack-up stack-down test lint typecheck policy-test helm-validate release-bundle bootstrap health ps logs smoke install-opa

PYTHON ?= python
OPA_RUNNER ?= $(PYTHON) scripts/run_opa.py
SECURE_ENV_FILE := $(shell $(PYTHON) -c "from frontier_tooling.common import ensure_compose_env_file; print(ensure_compose_env_file(local_profile=False))")
LIGHTWEIGHT_ENV_FILE := $(shell $(PYTHON) -c "from frontier_tooling.common import ensure_compose_env_file; print(ensure_compose_env_file(local_profile=True))")
LOCAL_COMPOSE ?= docker compose --env-file $(LIGHTWEIGHT_ENV_FILE) -f docker-compose.local.yml
FULL_COMPOSE ?= docker compose --env-file $(SECURE_ENV_FILE)

up:             ## Start all services
	$(FULL_COMPOSE) up -d

down:           ## Stop all services
	$(FULL_COMPOSE) down -v

local-up:       ## Start the lightweight local-first stack
	$(LOCAL_COMPOSE) up -d
	@echo "Lightweight local stack running. Frontend: http://localhost:3000  Backend health: http://localhost:8000/healthz"

local-down:     ## Stop the lightweight local-first stack
	$(LOCAL_COMPOSE) down -v

stack-up:       ## Start the full platform stack (gateway, sandbox, policy infra)
	$(FULL_COMPOSE) up -d

stack-down:     ## Stop the full platform stack
	$(FULL_COMPOSE) down -v

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
	helm template lattix ./helm/lattix-frontier -f helm/lattix-frontier/values-prod.yaml > /dev/null

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
	$(PYTHON) -m pip install -e ".[dev]" --break-system-packages
	$(FULL_COMPOSE) pull
	@echo "Run 'make up' to start the secure platform stack"

health:         ## Check API health endpoint
	$(PYTHON) -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/healthz', timeout=5).read().decode())"

ps:
	$(FULL_COMPOSE) ps

logs:
	$(FULL_COMPOSE) logs --tail=200

smoke:
	$(PYTHON) -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/healthz', timeout=5).read().decode())"


.PHONY: dev up down local-up local-down test lint typecheck policy-test bootstrap health ps logs smoke install-opa

PYTHON ?= python
OPA_RUNNER ?= $(PYTHON) scripts/run_opa.py
LOCAL_COMPOSE ?= docker compose -f docker-compose.local.yml
FULL_COMPOSE ?= docker compose

dev:            ## Start local stack (Docker Compose)
	$(FULL_COMPOSE) up -d
	@echo "Secure platform stack running. Gateway: http://frontier.localhost  Backend health: http://localhost:8000/healthz"

up:             ## Start all services
	$(FULL_COMPOSE) up -d

down:           ## Stop all services
	$(FULL_COMPOSE) down -v

local-up:       ## Start the lightweight local-first stack
	$(LOCAL_COMPOSE) up -d
	@echo "Lightweight local stack running. Frontend: http://localhost:3000  Backend health: http://localhost:8000/healthz"

stack-up:       ## Start the full platform stack (gateway, sandbox, policy infra)
	$(FULL_COMPOSE) up -d

stack-down:     ## Stop the full platform stack
	$(FULL_COMPOSE) down -v

local-down:     ## Stop the lightweight local-first stack
	$(LOCAL_COMPOSE) down -v

test:           ## Run all tests
	pytest apps/backend/tests tests -v --cov=app --cov=frontier_runtime --cov-report=term-missing

lint:           ## Lint and format
	ruff check . --fix
	ruff format .

typecheck:      ## Type check
	mypy frontier_tooling/ frontier_runtime/

policy-test:    ## Test OPA policies
	$(OPA_RUNNER) test policies/ -v

install-opa:    ## Install repo-local OPA binary (Windows helper remains available too)
	@echo "Install OPA with .\\scripts\\frontier.ps1 install-opa on Windows, or place the binary at .tools/opa/opa(.exe)."

bootstrap:      ## First-time setup
	$(PYTHON) -m pip install -e ".[dev]" --break-system-packages
	$(FULL_COMPOSE) pull
	@echo "Run 'make dev' to start the stack"

health:         ## Check API health endpoint
	$(PYTHON) -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/healthz', timeout=5).read().decode())"

ps:
	$(FULL_COMPOSE) ps

logs:
	$(FULL_COMPOSE) logs --tail=200

smoke:
	$(PYTHON) -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/healthz', timeout=5).read().decode())"


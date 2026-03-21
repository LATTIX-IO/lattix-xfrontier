.PHONY: dev up down test lint typecheck policy-test bootstrap health ps logs smoke install-opa

PYTHON ?= python
OPA_RUNNER ?= $(PYTHON) scripts/run_opa.py

dev:            ## Start local stack (Docker Compose)
	docker compose up -d
	@echo "Stack running. Admin UI: http://localhost:8000"

up:             ## Start all services
	docker compose up -d

down:           ## Stop all services
	docker compose down -v

test:           ## Run all tests
	pytest tests/ -v --cov=lattix_frontier --cov-report=term-missing

lint:           ## Lint and format
	ruff check . --fix
	ruff format .

typecheck:      ## Type check
	mypy lattix_frontier/

policy-test:    ## Test OPA policies
	$(OPA_RUNNER) test policies/ -v

install-opa:    ## Install repo-local OPA binary (Windows helper remains available too)
	@echo "Install OPA with .\\scripts\\frontier.ps1 install-opa on Windows, or place the binary at .tools/opa/opa(.exe)."

bootstrap:      ## First-time setup
	$(PYTHON) -m pip install -e ".[dev]" --break-system-packages
	docker compose pull
	@echo "Run 'make dev' to start the stack"

health:         ## Check API health endpoint
	$(PYTHON) -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/health', timeout=5).read().decode())"

ps:
	docker compose ps

logs:
	docker compose logs --tail=200

smoke:
	$(PYTHON) -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health', timeout=5).read().decode())"


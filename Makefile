.DEFAULT_GOAL := help
.PHONY: help up down restart logs ps migrate revision test psql shell verify fresh \
        sync dev local-migrate local-revision local-test local-psql local-verify local-fresh \
        features features-all features-local

# postgresql@16 is keg-only, so its binaries are not on PATH by default.
PGBIN  := /opt/homebrew/opt/postgresql@16/bin
PGUSER := postgres
PGDB   := planet_express
# Global `--directory` puts uv in api/, where pyproject.toml and app/ live.
UV := uv --directory api

# .env sits next to docker-compose.yml, so Compose auto-reads it — no --env-file
# needed, and a bare `docker compose` behaves identically to these targets.
COMPOSE := docker compose

# Read from the same file Compose reads, so the verify curls and `make dev`
# cannot drift from the port the container actually published. 8080 is the
# fallback if .env is missing (it is gitignored, so a fresh clone has none).
API_PORT := $(or $(shell sed -n 's/^API_PORT=//p' .env 2>/dev/null),8080)

help: ## Show available targets
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# --- Docker: the deliverable --------------------------------------------------

up: ## Build and start db + api (migrations run automatically)
	$(COMPOSE) up -d --build

down: ## Stop containers (data volume is preserved)
	$(COMPOSE) down

restart: ## Restart the api container
	$(COMPOSE) restart api

logs: ## Tail logs from both services
	$(COMPOSE) logs -f

ps: ## Show container status
	$(COMPOSE) ps

migrate: ## Apply migrations to the latest revision
	$(COMPOSE) exec api alembic upgrade head

revision: ## Autogenerate a migration: make revision m="add users table"
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(m)"

test: ## Run pytest inside the api container
	$(COMPOSE) exec api pytest -v

psql: ## Open a psql shell on the containerized database
	$(COMPOSE) exec db psql -U $(PGUSER) -d $(PGDB)

shell: ## Open a bash shell in the api container
	$(COMPOSE) exec api bash

verify: ## End-to-end proof that api -> postgres works
	@echo "--- GET /health ---"
	@curl -fsS localhost:$(API_PORT)/health && echo
	@echo "--- GET /health/db ---"
	@curl -fsS localhost:$(API_PORT)/health/db && echo
	@echo "--- straight from postgres: same database, migrations applied ---"
	@$(COMPOSE) exec -T db psql -U $(PGUSER) -d $(PGDB) \
		-c 'SELECT current_database(), version_num FROM alembic_version;'

fresh: ## Destroy the volume and rebuild from scratch
	$(COMPOSE) down -v
	$(COMPOSE) up -d --build

# --- Features: audit the claims in feature-list.json --------------------------

features: ## Verify every feature claimed "done" actually passes its checks
	@python3 scripts/verify-features.py

features-all: ## Same, but also run checks for todo/in_progress features
	@python3 scripts/verify-features.py --all

features-local: ## Same as `features`, but run pytest against host Postgres
	@python3 scripts/verify-features.py --local

# --- Local: faster inner loop, same code, host Postgres -----------------------

sync: ## Install/refresh the local virtualenv from uv.lock
	$(UV) sync

dev: sync ## Run the API on the host with reload, on API_PORT (see .env)
	$(UV) run uvicorn app.main:app --host 127.0.0.1 --port $(API_PORT) --reload

local-migrate: ## Apply migrations to the host database
	$(UV) run alembic upgrade head

local-revision: ## Autogenerate a migration on the host: make local-revision m="..."
	$(UV) run alembic revision --autogenerate -m "$(m)"

local-test: ## Run pytest on the host against the host database
	$(UV) run pytest -v

local-psql: ## Open a psql shell on the host database
	$(PGBIN)/psql -U $(PGUSER) -d $(PGDB)

local-verify: ## Same end-to-end proof, against the host database
	@echo "--- GET /health ---"
	@curl -fsS localhost:$(API_PORT)/health && echo
	@echo "--- GET /health/db ---"
	@curl -fsS localhost:$(API_PORT)/health/db && echo
	@echo "--- straight from postgres: same database, migrations applied ---"
	@$(PGBIN)/psql -U $(PGUSER) -d $(PGDB) \
		-c 'SELECT current_database(), version_num FROM alembic_version;'

local-fresh: ## Drop the host database and rebuild it from migrations
	# --force terminates the dev server's pooled connections, which would
	# otherwise make dropdb fail with "database is being accessed by other users".
	$(PGBIN)/dropdb --if-exists --force -U $(PGUSER) $(PGDB)
	$(PGBIN)/createdb -O $(PGUSER) -U $(PGUSER) $(PGDB)
	$(UV) run alembic upgrade head

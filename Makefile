ALEMBIC_INI=src/infrastructure/database/alembic.ini

# --- Deploy/compose defaults ---
# Which compose file to use for running on the server.
# Override like: make deploy COMPOSE_FILE=docker-compose.yml
COMPOSE_FILE ?= docker-compose.prod.internal.yml
COMPOSE ?= docker compose -f $(COMPOSE_FILE)

# Which git remote/branch to track
GIT_REMOTE ?= origin
GIT_BRANCH ?= main

.PHONY: setup-env
setup-env:
	@sed -i '' "s|^APP_CRYPT_KEY=.*|APP_CRYPT_KEY=$(shell openssl rand -base64 32 | tr -d '\n')|" .env
	@sed -i '' "s|^BOT_SECRET_TOKEN=.*|BOT_SECRET_TOKEN=$(shell openssl rand -hex 64 | tr -d '\n')|" .env
	@sed -i '' "s|^DATABASE_PASSWORD=.*|DATABASE_PASSWORD=$(shell openssl rand -hex 24 | tr -d '\n')|" .env
	@sed -i '' "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=$(shell openssl rand -hex 24 | tr -d '\n')|" .env
	@echo "Secrets updated. Check your .env file"

.PHONY: migration
migration:
	alembic -c $(ALEMBIC_INI) revision --autogenerate

.PHONY: migrate
migrate:
	alembic -c $(ALEMBIC_INI) upgrade head

.PHONY: downgrade
downgrade:
	@if [ -z "$(rev)" ]; then \
		echo "No revision specified. Downgrading by 1 step."; \
		alembic -c $(ALEMBIC_INI) downgrade -1; \
	else \
		alembic -c $(ALEMBIC_INI) downgrade $(rev); \
	fi


.PHONY: check-updates
check-updates:
	@set -e; \
	if [ ! -d .git ]; then echo "Not a git repo (no .git)."; exit 1; fi; \
	git remote get-url $(GIT_REMOTE) >/dev/null 2>&1 || { echo "Remote '$(GIT_REMOTE)' not found"; exit 1; }; \
	git fetch --prune $(GIT_REMOTE) >/dev/null; \
	LOCAL=$$(git rev-parse HEAD); \
	REMOTE=$$(git rev-parse $(GIT_REMOTE)/$(GIT_BRANCH)); \
	if [ "$$LOCAL" = "$$REMOTE" ]; then \
		echo "No updates: $$LOCAL"; \
	else \
		echo "Updates available:"; \
		echo "  local : $$LOCAL"; \
		echo "  remote: $$REMOTE"; \
	fi

.PHONY: git-update
git-update:
	@set -e; \
	if [ ! -d .git ]; then echo "Not a git repo (no .git)."; exit 1; fi; \
	git remote get-url $(GIT_REMOTE) >/dev/null 2>&1 || { echo "Remote '$(GIT_REMOTE)' not found"; exit 1; }; \
	git fetch --prune $(GIT_REMOTE) >/dev/null; \
	LOCAL=$$(git rev-parse HEAD); \
	REMOTE=$$(git rev-parse $(GIT_REMOTE)/$(GIT_BRANCH)); \
	if [ "$$LOCAL" = "$$REMOTE" ]; then \
		echo "Already up to date: $$LOCAL"; \
	else \
		echo "Pulling changes..."; \
		git pull --ff-only $(GIT_REMOTE) $(GIT_BRANCH); \
	fi

.PHONY: up
up:
	@$(COMPOSE) up -d --build

.PHONY: down
down:
	@$(COMPOSE) down

.PHONY: restart
restart:
	@$(COMPOSE) restart

.PHONY: logs
logs:
	@$(COMPOSE) logs -f --tail=200

.PHONY: ps
ps:
	@$(COMPOSE) ps

.PHONY: deploy
deploy:
	@$(MAKE) git-update
	@$(MAKE) up
	@docker restart remnawave-nginx || true
	@echo "Done: code checked/updated and containers are up"



.PHONY: run-local
run-local:
	@docker compose -f docker-compose.local.yml up --build
	@docker compose logs -f
	
.PHONY: run-prod
run-prod:
	@docker compose -f docker-compose.prod.external.yml up --build
	@docker compose logs -f

# .PHONY: run-dev
# run-dev:
# 	@docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
# 	@docker compose logs -f
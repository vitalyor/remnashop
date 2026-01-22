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
	if [ ! -d .git ]; then echo "Not a git repo (no .git). Skipping update check."; exit 0; fi; \
	git remote get-url $(GIT_REMOTE) >/dev/null 2>&1 || { echo "Remote '$(GIT_REMOTE)' not found"; exit 1; }; \
	git fetch --prune $(GIT_REMOTE) >/dev/null; \
	REMOTE=$$(git rev-parse $(GIT_REMOTE)/$(GIT_BRANCH)); \
	if git rev-parse --verify HEAD >/dev/null 2>&1; then \
		LOCAL=$$(git rev-parse HEAD); \
		if [ "$$LOCAL" = "$$REMOTE" ]; then \
			echo "No updates: $$LOCAL"; \
		else \
			echo "Updates available:"; \
			echo "  local : $$LOCAL"; \
			echo "  remote: $$REMOTE"; \
		fi; \
	else \
		echo "Repo has no checked-out commit yet (HEAD missing). Remote tip: $$REMOTE"; \
		echo "Run: make git-repair (or: git checkout -B $(GIT_BRANCH) $(GIT_REMOTE)/$(GIT_BRANCH))"; \
	fi

.PHONY: git-update
git-update:
	@set -e; \
	if [ ! -d .git ]; then echo "Not a git repo (no .git). Skipping git-update."; exit 0; fi; \
	git remote get-url $(GIT_REMOTE) >/dev/null 2>&1 || { echo "Remote '$(GIT_REMOTE)' not found"; exit 1; }; \
	git fetch --prune $(GIT_REMOTE) >/dev/null; \
	REMOTE=$$(git rev-parse $(GIT_REMOTE)/$(GIT_BRANCH)); \
	if ! git rev-parse --verify HEAD >/dev/null 2>&1; then \
		echo "HEAD is missing (repo not checked out yet). Checking out $(GIT_REMOTE)/$(GIT_BRANCH)..."; \
		git checkout -B $(GIT_BRANCH) $(GIT_REMOTE)/$(GIT_BRANCH); \
		LOCAL=$$(git rev-parse HEAD); \
		echo "Checked out: $$LOCAL"; \
	else \
		LOCAL=$$(git rev-parse HEAD); \
		if [ "$$LOCAL" = "$$REMOTE" ]; then \
			echo "Already up to date: $$LOCAL"; \
		else \
			echo "Pulling changes..."; \
			git pull --ff-only $(GIT_REMOTE) $(GIT_BRANCH); \
		fi; \
	fi

# Optional: initialize git repo in the current directory (in-place)
# Usage:
#   make git-init GIT_URL=https://github.com/snoups/remnashop.git
.PHONY: git-init
GIT_URL ?=

git-init:
	@set -e; \
	if [ -d .git ]; then \
		# If .git exists but nothing is checked out yet, try to repair in-place. \
		if git rev-parse --verify HEAD >/dev/null 2>&1; then \
			echo "Already a git repo."; exit 0; \
		else \
			echo "Repo exists but HEAD is missing. Attempting in-place checkout..."; \
			git remote get-url $(GIT_REMOTE) >/dev/null 2>&1 || { \
				if [ -z "$(GIT_URL)" ]; then echo "GIT_URL is empty. Example: make git-init GIT_URL=https://github.com/snoups/remnashop.git"; exit 1; fi; \
				git remote add $(GIT_REMOTE) "$(GIT_URL)"; \
			}; \
			git fetch --prune $(GIT_REMOTE); \
			git checkout -B $(GIT_BRANCH) $(GIT_REMOTE)/$(GIT_BRANCH); \
			echo "Git repaired. Remote=$(GIT_REMOTE) Branch=$(GIT_BRANCH)"; \
			exit 0; \
		fi; \
	fi; \
	if [ -z "$(GIT_URL)" ]; then echo "GIT_URL is empty. Example: make git-init GIT_URL=https://github.com/snoups/remnashop.git"; exit 1; fi; \
	git init; \
	git remote add $(GIT_REMOTE) "$(GIT_URL)"; \
	git fetch --prune $(GIT_REMOTE); \
	git checkout -B $(GIT_BRANCH) $(GIT_REMOTE)/$(GIT_BRANCH); \
	echo "Git initialized. Remote=$(GIT_REMOTE) Branch=$(GIT_BRANCH)"

# Repair an existing .git that has no checked-out commit yet
.PHONY: git-repair

git-repair:
	@set -e; \
	if [ ! -d .git ]; then echo "Not a git repo (no .git). Run: make git-init GIT_URL=..."; exit 1; fi; \
	git remote get-url $(GIT_REMOTE) >/dev/null 2>&1 || { echo "Remote '$(GIT_REMOTE)' not found. Run: make git-init GIT_URL=..."; exit 1; }; \
	git fetch --prune $(GIT_REMOTE); \
	git checkout -B $(GIT_BRANCH) $(GIT_REMOTE)/$(GIT_BRANCH); \
	echo "Git repaired. Now at $$(git rev-parse HEAD)"

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
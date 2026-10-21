COMPOSE = docker compose -f compose.yaml -f compose.local.yaml
.PHONY: install dev down logs check format build api-types dev-api dev-web infra-up docker-dev
install:
	uv sync --project apps/api
	pnpm --dir apps/web install --frozen-lockfile
dev: infra-up
	uv run --project apps/api python scripts/dev.py
infra-up:
	$(COMPOSE) up -d --wait postgres
docker-dev:
	$(COMPOSE) up --build -d --wait
down:
	$(COMPOSE) down
logs:
	$(COMPOSE) logs -f --tail=100
api-types:
	mkdir -p .generated
	uv run --project apps/api python -m kimmy.cli > .generated/openapi.json
	pnpm --dir apps/web generate:api
check:
	uv run --project apps/api ruff check apps/api/src scripts
	uv run --project apps/api ruff format --check apps/api/src scripts
	uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src scripts
	pnpm --dir apps/web lint
	pnpm --dir apps/web typecheck
	pnpm --dir apps/web format:check
format:
	uv run --project apps/api ruff check --fix apps/api/src scripts
	uv run --project apps/api ruff format apps/api/src scripts
	pnpm --dir apps/web format
build:
	pnpm --dir apps/web build
	$(COMPOSE) build
dev-api:
	uv run --project apps/api python scripts/dev.py api
dev-web:
	pnpm --dir apps/web dev --port 5173 --strictPort

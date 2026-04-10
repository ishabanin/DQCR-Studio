.PHONY: dev build lint test deploy down prod-build prod-up prod-down prod-logs prod-health prod-bundle

dev:
	docker compose -f infra/docker/docker-compose.yml up --build

build:
	docker compose -f infra/docker/docker-compose.yml build

lint:
	uv run --directory backend --with ruff ruff check app tests
	pnpm --dir frontend lint
	pnpm --dir frontend format:check

test:
	python3 -m compileall backend/app
	uv run --directory backend pytest
	pnpm --dir frontend test

deploy:
	./scripts/prod-up.sh

down:
	docker compose -f infra/docker/docker-compose.yml down

prod-build:
	docker compose -f infra/docker/docker-compose.prod.yml build

prod-up:
	./scripts/prod-up.sh

prod-down:
	./scripts/prod-down.sh

prod-logs:
	./scripts/prod-logs.sh

prod-health:
	./scripts/prod-health.sh

prod-bundle:
	./scripts/prod-bundle.sh

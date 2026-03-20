.PHONY: dev build test deploy down

dev:
	docker compose -f infra/docker/docker-compose.yml up --build

build:
	docker compose -f infra/docker/docker-compose.yml build

test:
	python3 -m compileall backend/app
	uv run --directory backend pytest
	pnpm --dir frontend test

deploy:
	@echo "Deploy pipeline is not configured yet (placeholder target)."

down:
	docker compose -f infra/docker/docker-compose.yml down

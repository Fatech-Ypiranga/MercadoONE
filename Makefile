.PHONY: help up up-app down test lint migrate migrate-down lock frontend-test frontend-lint

help:
	@echo "Targets:"
	@echo "  up             - Postgres + pgAdmin (docker compose)"
	@echo "  up-app         - API + Postgres (docker-compose.app.yml)"
	@echo "  down           - Para stacks compose"
	@echo "  test           - pytest com coverage"
	@echo "  lint           - ruff check + format --check"
	@echo "  migrate        - alembic upgrade head"
	@echo "  migrate-down   - alembic downgrade -1"
	@echo "  lock           - regenera requirements.lock (uv)"
	@echo "  frontend-test  - npm test (frontend/)"
	@echo "  frontend-lint  - npm run lint (frontend/)"

up:
	docker compose up -d

up-app:
	docker compose -f docker-compose.app.yml up --build

down:
	docker compose down
	docker compose -f docker-compose.app.yml down

test:
	pytest -q --cov=. --cov-fail-under=55

lint:
	ruff check .
	ruff format --check .

migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

lock:
	uv pip compile requirements.txt -o requirements.lock --python 3.11 --strip-extras

frontend-test:
	cd frontend && npm test

frontend-lint:
	cd frontend && npm run lint

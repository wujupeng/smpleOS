.PHONY: lint test migrate dev-up dev-down install clean format

PYTHON := poetry run python
RUFF := poetry run ruff
MYPY := poetry run mypy
PYTEST := poetry run pytest

lint:
	$(RUFF) check libs services
	$(RUFF) format --check libs services
	$(MYPY) libs services

format:
	$(RUFF) check --fix libs services
	$(RUFF) format libs services

test:
	$(PYTEST) --cov=aeroforge_common --cov=aeroforge_db -v

test-all:
	$(PYTEST) --cov --cov-report=html -v

migrate:
	cd libs/aeroforge-db && $(PYTHON) -m alembic upgrade head

migrate-down:
	cd libs/aeroforge-db && $(PYTHON) -m alembic downgrade -1

migrate-create:
	cd libs/aeroforge-db && $(PYTHON) -m alembic revision --autogenerate -m "$(msg)"

dev-up:
	docker compose -f deploy/docker-compose.yml up -d

dev-down:
	docker compose -f deploy/docker-compose.yml down

dev-logs:
	docker compose -f deploy/docker-compose.yml logs -f

install:
	poetry install

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	rm -rf htmlcov .coverage
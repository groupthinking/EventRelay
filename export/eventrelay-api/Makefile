.PHONY: install install-dev test run openapi lint fmt docker-build docker-run

PORT ?= 8080
IMAGE ?= eventrelay-api:local

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,youtube,gemini,postgres]"

# In-memory store + fake providers: no DB, keys, or network required.
test:
	pytest

# Local server (in-memory store unless EVENTRELAY_DATABASE_URL is set).
run:
	uvicorn service.app.main:app --reload --port $(PORT)

# Regenerate the contract of record from the live app.
openapi:
	python -c "import json; from service.app.main import app; print(json.dumps(app.openapi(), indent=2))" > service/openapi.json

lint:
	ruff check service
	black --check service
	isort --check-only service

fmt:
	ruff check service --fix
	black service
	isort service

docker-build:
	docker build -f service/Dockerfile -t $(IMAGE) .

docker-run:
	docker run --rm -p $(PORT):8080 \
		-e EVENTRELAY_GEMINI_API_KEY \
		-e EVENTRELAY_DATABASE_URL \
		$(IMAGE)

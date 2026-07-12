up:
	python scripts/start_stack.py

up-direct:
	docker compose up --build

up-ollama:
	docker compose --profile ollama up --build

down:
	docker compose --profile ollama down

logs:
	docker compose --profile ollama logs -f

logs-ollama:
	docker compose --profile ollama logs -f ollama

backend-shell:
	docker compose exec backend bash

frontend-shell:
	docker compose exec frontend sh

db-shell:
	docker compose exec postgres psql -U explainer -d programming_explainer

migrate:
	docker compose exec backend alembic upgrade head

test-backend:
	docker compose exec backend pytest

test-sandbox:
	docker compose exec sandbox-runner pytest
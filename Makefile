up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

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


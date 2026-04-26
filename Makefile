# Nadini — Developer Commands
# Usage: make <target>

.PHONY: up down build logs test lint clean keys demo

# ── Stack ──
up: keys ## Start full stack (Postgres + Redis + Auth + Meeting + Nginx)
	FRONTEND_PORT=$${FRONTEND_PORT:-3000} docker compose up -d
	@echo "\n  Nadini running:"
	@echo "  Frontend:  http://localhost:$${FRONTEND_PORT:-3000}"
	@echo "  Auth API:  http://localhost:8001/docs"
	@echo "  Meeting API: http://localhost:8002/docs"
	@echo ""

down: ## Stop all containers
	docker compose down

build: ## Rebuild all images
	docker compose build

restart: build up ## Rebuild + restart

logs: ## Tail all logs
	docker compose logs -f --tail=50

logs-auth: ## Tail auth-service logs
	docker compose logs -f auth-service

logs-meeting: ## Tail meeting-service logs
	docker compose logs -f meeting-service

ps: ## Show container status
	docker compose ps

# ── Development ──
keys: ## Generate JWT keys (if missing)
	@cd auth-service && bash scripts/generate_keys.sh

demo: ## Open demo in browser (no backend needed)
	open app/login.html?demo=1

lint: ## Run linters
	cd auth-service && python -m ruff check app/ tests/
	cd meeting-service && python -m ruff check app/

test-auth: ## Run auth-service tests (needs Docker)
	cd auth-service && pytest -v

test-e2e: ## Run E2E smoke test
	@echo "Testing Auth..."
	@curl -sf http://localhost:8001/health > /dev/null && echo "  Auth: OK" || echo "  Auth: FAILED"
	@echo "Testing Meeting..."
	@curl -sf http://localhost:8002/health > /dev/null && echo "  Meeting: OK" || echo "  Meeting: FAILED"
	@echo "Testing Frontend..."
	@curl -sf http://localhost:$${FRONTEND_PORT:-3000}/ > /dev/null && echo "  Frontend: OK" || echo "  Frontend: FAILED"

# ── Database ──
db-shell: ## Open psql shell
	docker compose exec postgres psql -U admin -d nadini

db-reset: ## Drop and recreate database (DESTRUCTIVE)
	docker compose down -v
	$(MAKE) up

migrate-auth: ## Run auth-service migrations
	docker compose exec auth-service alembic upgrade head

migrate-meeting: ## Run meeting-service migrations
	docker compose exec meeting-service alembic upgrade head

# ── Cleanup ──
clean: down ## Stop + remove volumes
	docker compose down -v --remove-orphans
	docker system prune -f

# ── Help ──
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

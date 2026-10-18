# Postulo dev tasks (macOS/Linux/Git Bash). On Windows without make, use the
# npm scripts in package.json (`npm run dev:backend`, ...) or scripts/dev.ps1.

.PHONY: help setup env dev dev-backend dev-frontend test lint format build docker-build docker-up docker-down

help:
	@echo "setup         install backend (uv) and frontend (npm) deps, create .env"
	@echo "dev           run backend :8000 and frontend :3000 together"
	@echo "test          backend pytest"
	@echo "lint          ruff + eslint"
	@echo "build         frontend production build"
	@echo "docker-up     docker compose up --build"

env:
	@test -f .env || cp .env.example .env

setup: env
	cd backend && uv sync
	cd frontend && npm install

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	$(MAKE) -j2 dev-backend dev-frontend

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run lint

format:
	cd backend && uv run ruff format . && uv run ruff check --fix .

build:
	cd frontend && npm run build

docker-build: env
	docker compose build

docker-up: env
	docker compose up --build

docker-down:
	docker compose down

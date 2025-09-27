SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help up down logs env deps api worker web-deps web web-build web-start db-migrate db-upgrade db-rev

help:
	@echo "make env      # copy .env.example -> .env"
	@echo "make up       # start Postgres/Rabbit/MinIO"
	@echo "make db-migrate   # run Alembic upgrade head (apps/api)"
	@echo "make db-upgrade   # alias to db-migrate"
	@echo "make db-rev       # create new Alembic revision with message MSG=..."
	@echo "make deps     # uv sync with api+worker groups"
	@echo "make api      # run FastAPI (uv script)"
	@echo "make worker   # run worker (uv script)"
	@echo "make web-deps # install Next.js deps (apps/web)"
	@echo "make web      # run Next.js dev server (apps/web)"
	@echo "make web-build# build Next.js (apps/web)"
	@echo "make web-start# start Next.js (apps/web)"

env:
	cp -n .env.example .env || true && echo ".env prepared"

up:
	docker compose up -d
	@echo "Postgres:  postgres://app:app@localhost:6432/mastering"
	@echo "MinIO:     http://localhost:9001"
	@echo "Rabbit: http://localhost:15678 (app/app)"
	docker compose ps

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

deps:
	uv sync --all-extras

api:
	cd apps/api && uv run -m uvicorn app.main:app --reload --port $${API_PORT:-4000}

worker:
	cd apps/worker && uv run -m worker.main

web-deps:
	cd apps/web && npm ci

web:
	cd apps/web && npm run dev

web-build:
	cd apps/web && npm run build

web-start:
	cd apps/web && npm run start

db-migrate:
	cd apps/api && uv run alembic -c alembic.ini upgrade head

db-upgrade: db-migrate

# db-rev:
# 	cd apps/api && uv run alembic -c alembic.ini revision -m "$${MSG:-change}"

db-rev:
	cd apps/api && \
	ID=$$(date +"%Y%m%d%H%M"); \
	AUTO=$${AUTO:-1}; \
	AUTOGEN=$${AUTO:+--autogenerate}; \
	uv run alembic -c alembic.ini revision $$AUTOGEN -m "$${MSG:-change}" --rev-id "$$ID"
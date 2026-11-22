# Easy Diligence: the everyday commands. `make` alone lists them.
#
# The recipes are plain commands that run the same under sh (Linux, macOS,
# Git Bash) and cmd (make on Windows without sh). On Windows, install make
# with: winget install ezwinports.make

.DEFAULT_GOAL := help

.PHONY: help up down ps logs build build-backend build-frontend admin demo \
	install dev-backend dev-frontend test lint format check migrate migration schema

# $(info) is printed by make itself: the same output under sh and cmd. It strips
# leading spaces, hence $(indent).
empty :=
indent := $(empty)  $(empty)

help:
	$(info Easy Diligence - make targets)
	$(info )
	$(info With Docker (the whole application, on http://localhost:8080):)
	$(info $(indent)make up              build the images if needed, then start everything)
	$(info $(indent)make down            stop everything (the data stays))
	$(info $(indent)make ps              the state of the services)
	$(info $(indent)make logs            follow the logs (one service: make logs s=backend))
	$(info $(indent)make build           build the images of the four services)
	$(info $(indent)make build-backend   rebuild the backend image and restart it)
	$(info $(indent)make build-frontend  rebuild the frontend image and restart it)
	$(info $(indent)make admin email=you@example.com name="Full Name")
	$(info $(indent)                     create an administrator (asks for the password))
	$(info $(indent)make demo            load a made-up due diligence to explore, without OpenAI)
	$(info $(indent)                     owner=you@example.com: its owner (default: the first admin))
	$(info $(indent)                     reset=1: delete the demo, then load it again)
	$(info )
	$(info By hand (development, see the README):)
	$(info $(indent)make install         install the backend and frontend dependencies)
	$(info $(indent)make dev-backend     the API on http://localhost:8000, reloaded on change)
	$(info $(indent)make dev-frontend    the interface on http://localhost:5173)
	$(info $(indent)make test            the backend tests)
	$(info $(indent)make lint            ruff, mypy, eslint and the formatting checks)
	$(info $(indent)make format          format the backend and the frontend)
	$(info $(indent)make check           lint, tests and the frontend build, as in CI)
	$(info $(indent)make migrate         apply the migrations to the database of backend/.env)
	$(info $(indent)make migration m="add column X")
	$(info $(indent)                     generate a migration from the models (review it))
	$(info $(indent)make schema          regenerate backend/db/schema.sql)
	@cd .

# --- Docker ---------------------------------------------------------------------

up:
	docker compose up -d --build

down:
	docker compose down

ps:
	docker compose ps

logs:
	docker compose logs -f $(s)

build:
	docker compose build

# --force-recreate: the container is replaced even when compose considers it up
# to date, so it always runs the image just built.
build-backend:
	docker compose up -d --build --force-recreate backend

build-frontend:
	docker compose up -d --build --force-recreate frontend

admin:
	$(if $(email),,$(error Usage: make admin email=you@example.com name="Full Name"))
	$(if $(name),,$(error Usage: make admin email=you@example.com name="Full Name"))
	docker compose exec backend python -m app.cli create-admin $(email) "$(name)"

# A made-up fund, questionnaire, answers and summaries (backend/app/demo/), to
# explore every screen without any call to OpenAI. Loaded once: run again, it
# says so and writes nothing.
demo:
	docker compose exec backend python -m app.cli seed-demo $(if $(owner),--owner $(owner)) $(if $(reset),--reset)

# --- By hand (development) --------------------------------------------------------

install:
	cd backend && uv sync
	cd frontend && npm ci

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .
	cd backend && uv run mypy app
	cd frontend && npm run lint
	cd frontend && npm run format:check

format:
	cd backend && uv run ruff format .
	cd frontend && npm run format

check: lint test
	cd frontend && npm run build

migrate:
	cd backend && uv run alembic upgrade head

migration:
	$(if $(m),,$(error Usage: make migration m="add column X"))
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

schema:
	cd backend && uv run alembic upgrade head --sql > db/schema.sql

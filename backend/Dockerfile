# Easy Diligence backend: the FastAPI application, run by uvicorn.
# Built by docker-compose.yml (service `backend`); the versions are in VERSION.md.

FROM python:3.12.16-slim-trixie

# uv, at the version the project asks for (pyproject.toml, [tool.uv]).
COPY --from=ghcr.io/astral-sh/uv:0.9.17 /uv /bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# The dependencies first, without the project: this layer is only rebuilt
# when uv.lock changes, not at every change of the code.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN uv sync --locked --no-dev

# Not root: the application needs no write access to its files.
RUN useradd --system --uid 10001 --no-create-home easy
USER easy

EXPOSE 8000

# The schema first (nothing to do when it is up to date), then the API.
# Behind the proxy, X-Forwarded-For carries the client's address, which the
# login limits count per IP: only the proxy can reach this port, so its
# headers are trusted.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'"]

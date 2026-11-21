# Easy Diligence

A web application that automates the due diligence of investment funds and of
their management company.

You describe a due diligence questionnaire (a **DD type**), then open a
**session** on a fund and attach its documents (prospectuses, presentations,
DDQs…). The answering engine then answers the questions one by one with the
OpenAI API: it searches the session's documents and the web, and cites its
sources. Analysts review, correct or regenerate the answers, have a synthesis
written for each DD type, then export a PDF report.

## Running the application

The application runs with Docker: there is no Python, Node or PostgreSQL to
install.

### What you need

- **Docker**, with Compose v2: Docker Desktop on Windows and macOS, Docker
  Engine on Linux. `docker compose version` must respond;
- **Git**, to get the code;
- **an OpenAI API key** (https://platform.openai.com/api-keys), on an account
  that has access to the chosen model (`OPENAI_MODEL`, see `.env.template`).

### 1. Get the code

```bash
git clone https://github.com/Plouplou37/Easy-Diligence.git
cd Easy-Diligence
```

### 2. Configure

Copy the configuration template to `.env`, at the root of the repository:

```bash
cp .env.template .env               # Linux, macOS, Git Bash
Copy-Item .env.template .env        # Windows PowerShell
```

Then open `.env` and fill in the three required values:

| Variable | Value |
| --- | --- |
| `POSTGRES_PASSWORD` | a password for the database, to generate (see below) |
| `OPENAI_API_KEY` | the OpenAI API key |
| `JWT_SECRET_KEY` | a key of at least 32 characters, to generate (see below) |

To generate a secret:

```bash
openssl rand -hex 32                # Linux, macOS, Git Bash
```

```powershell
# Windows PowerShell
$b = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); -join ($b | ForEach-Object { $_.ToString('x2') })
```

The rest of `.env` is optional, and each variable in it has a comment. Two
values are useful from the start:
- `FRONTEND_URL=http://localhost:8080`: the address used in password reset
  emails;
- `APP_PORT`: the application's port, if 8080 is already taken.

The `.env` file contains secrets: it is ignored by git, and must never be
committed.

### 3. Start

```bash
docker compose up -d --build
```

The first start builds the images and takes a few minutes. Later starts are
immediate. To check that everything is running:

```bash
docker compose ps
```

The four services (`proxy`, `frontend`, `backend`, `db`) must be `running` and
`healthy`.

### 4. Create the first administrator

There is no open sign-up: the first account is created from the command line.
The command asks for its password (at least 8 characters, with an uppercase
letter, a lowercase letter and a digit).

```bash
docker compose exec backend python -m app.cli create-admin <email address> "<Full Name>"
```

The application opens at **http://localhost:8080**, where you sign in with
this address and password. The administrator then creates the other accounts
from **User Management** ("Create user"), with a temporary password that each
user changes in their profile.

### 5. First due diligence

1. **DD Types** > **Add DD Type** > **Import from File**: import the example
   questionnaire, `examples/example_questionnaire.json` (18 example questions,
   in 6 sections).
2. **Vector Stores** > **Create Vector Store**, then upload the fund's
   documents to it (prospectus, presentation, DDQ…).
3. **New Session**: choose or create the fund, choose the questionnaire, then
   **Create Session**.
4. On the session page, attach the vector store (**Assign to all**), then
   **Start** on the questionnaire's card. Allow about 15 seconds per question.
   The card shows the progress, and the run can be paused and then resumed.
5. Review the answers (**Review Answers**), write the synthesis
   (**Synthesis**), then export the PDF report (**Export PDF**).

### Troubleshooting

- **A service is not `healthy`**: read its logs, for example
  `docker compose logs backend`. A missing required variable is named there,
  and `docker compose up` refuses to start without `POSTGRES_PASSWORD`.
- **Port 8080 is already taken**: set `APP_PORT=8090` (for example) in `.env`,
  then run `docker compose up -d` again.
- **Starting from scratch**: `docker compose down -v` also deletes the
  database, **and so all the data**.

### Day to day

```bash
docker compose ps                          # the state of the services
docker compose logs -f backend             # the logs of one service
docker compose down                        # stop everything (the data stays)
docker compose up -d                       # start again
git pull && docker compose up -d --build   # update, migrations included
```

The `Makefile` at the root gathers these commands and those of the
development sections below: `make` alone lists them (`make up`, `make logs`,
`make build-backend`, `make admin`, `make check`…). On Windows, install make
once with `winget install ezwinports.make`.

### Backup

```bash
# back up the database to a file
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > backup.sql
# restore it, into an empty database
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backup.sql
```

The data lives in the Docker volume `db-data`, which `docker compose down`
keeps.

### Accessing the database from your machine

Port 5432 is not published. To open it, on this machine only, create a
`docker-compose.override.yml` at the root (ignored by git):

```yaml
services:
  db:
    ports:
      - "127.0.0.1:5432:5432"
```

### PDF report banner

The repository's `branding/` folder (ignored by git) is mounted into the
backend, read-only, at `/app/branding`. For a banner at the top of the PDFs,
put the image there, then set in `.env`:
`BRAND_BANNER_PATH=/app/branding/<file>`. Without a `branding/` folder, Docker
creates an empty one, and the reports come out without a banner.

### Scripts and administration commands

They run in the backend container, for example:
`docker compose exec backend python scripts/audit_integrity.py`.

### How it is built

```
browser ──► proxy ──/api──► backend ──► db
              └──── / ────► frontend
```

Four services (`docker-compose.yml`):
- **`proxy`**: nginx, the only entry point, on port 8080. It forwards `/api` to
  the backend and the rest to the frontend, and enforces the limits (file
  size, timeouts) and the security headers;
- **`frontend`**: the built application, served as static files;
- **`backend`**: the API. It applies the migrations at every start;
- **`db`**: PostgreSQL 17, whose data lives in the `db-data` volume.

The database and the backend can only be reached from the other services, not
from your machine.

## Deploying to the cloud

The [`infra/`](infra/) folder contains the Terraform code to deploy the
application on managed services, on either cloud:
- **Azure** ([`infra/azure/`](infra/azure/README.md)): Container Apps,
  PostgreSQL Flexible Server, Key Vault. HTTPS is provided by Azure;
- **AWS** ([`infra/aws/`](infra/aws/README.md)): ECS Fargate, RDS PostgreSQL,
  Secrets Manager, behind a load balancer. HTTPS requires a domain name.

Each README gives the commands in order. Nothing is deployed without
`terraform apply`.

## Features

- **Questionnaires**: created and edited in the interface, or imported from a
  JSON file (see [`examples/`](examples/)). Each question can carry a "where
  to look" instruction that is passed to the model.
- **Answering engine**: one call per question with two tools, search in the
  documents (OpenAI vector stores) and web search. The run can be paused and
  resumed.
- **Review**: answers are versioned and editable, can be regenerated one by
  one, and have a review status.
- **Syntheses**: a summary for each section, then a synthesis for each DD
  type. They are written either live or later through OpenAI's Batch API,
  which costs half as much.
- **Export**: a two-level PDF report (the synthesis in the body, the detail of
  the questions and answers in an appendix).
- **Accounts and isolation**: `admin` and `analyst` roles. Each user sees only
  their own data, and the administrator sees everything.

## Running by hand (development)

### Prerequisites

- [uv](https://docs.astral.sh/uv/) 0.9.17 or newer. It installs Python 3.12
  itself if needed (`backend/.python-version`);
- Node.js 24, with npm (`frontend/.nvmrc`);
- a PostgreSQL 17 server;
- an OpenAI API key.

### 1. Configuration

```bash
cp .env.template backend/.env
```

In `backend/.env`, fill in at least `POSTGRES_PASSWORD` (with
`POSTGRES_HOST=localhost` locally), `OPENAI_API_KEY` and `JWT_SECRET_KEY`.
Each variable is described in the file.

The frontend does not need a `.env`: it calls the API on `/api`, and in
development the Vite server forwards these calls to the backend, at
`http://localhost:8000` (configurable with `VITE_API_PROXY` in
`frontend/.env`).

### 2. Database

Create the user and the database, with the values from `backend/.env`:

```sql
CREATE USER easy_diligence WITH PASSWORD '<password>';
CREATE DATABASE easy_diligence OWNER easy_diligence;
```

Then create the tables, from `backend/`:

```bash
uv run alembic upgrade head
```

Later, the same command applies the migrations added in new versions, and
keeps the data. For a database created before migration `0002`, first run
`uv run python scripts/audit_integrity.py` (read-only): it lists the rows that
`0002` will fix, and the rows that would stop it because they need a
decision.

### 3. Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

The API responds at `http://localhost:8000/api`. Its interactive
documentation, `http://localhost:8000/docs`, is closed by default: to open it
in development, set `DOCS_ENABLED=true` in `backend/.env`.

On Windows, if `uv sync` fails with "os error 1224", run the command again
with the variable `UV_LINK_MODE=copy`.

### 4. Frontend

```bash
cd frontend
npm ci
npm run dev
```

The application opens at `http://localhost:5173`.

### 5. First administrator

There is no open sign-up: an administrator creates the accounts. The first
one is created from the command line, from `backend/`:

```bash
uv run python -m app.cli create-admin <email address> "<Full Name>"
```

The command asks for the password. After that, an administrator creates the
other accounts from **User Management** ("Create user"), with their role and a
temporary password that the administrator passes on to them, and that each
user changes in their profile.

### 6. First questionnaire

An example questionnaire is provided: 18 questions about a fund, in 6
sections. To import it without going through the interface, run from
`backend/`:

```bash
uv run python scripts/import_questionnaire.py ../examples/example_questionnaire.json EXAMPLE "Example questionnaire"
```

You can also import it from the **DD Types** page.

### Production build

In production, the application runs with Docker (see
[Running the application](#running-the-application)). Without Docker:
`npm run build` in `frontend/` produces `frontend/dist/`, a static site to
serve as is, with every route sent to `index.html` (see `frontend/nginx.conf`)
and `/api` forwarded to the backend (see `proxy/default.conf.template`). The
backend then runs without `--reload`.

## Changing the database

The schema is described by the models (`backend/app/models/`, in SQLModel)
and versioned by Alembic (`backend/alembic/versions/`). For a change of
structure, from `backend/`:

```bash
# 1. change the model, then generate the migration
uv run alembic revision --autogenerate -m "add column X"
# 2. review the file created in alembic/versions/, then apply it
uv run alembic upgrade head
# 3. regenerate the full SQL script of the schema
uv run alembic upgrade head --sql > db/schema.sql
```

`db/schema.sql` creates the whole PostgreSQL database in one go, for anyone
who wants to do without Alembic. `uv run alembic check` checks that the
migrations match the models.

## Tests and quality

```bash
# Backend, from backend/ (uv sync also installs the development tools)
uv run pytest                    # the whole suite
uv run ruff check .              # lint
uv run ruff format .             # formatting
uv run mypy app                  # types
uv run pip-audit --skip-editable # known vulnerabilities in the dependencies

# Frontend, from frontend/
npm run lint
npm run format                   # formatting (Prettier); format:check checks it
npm run build
```

From the root, `make check` runs these checks (all but `pip-audit`), and
`make format` the formatting.

The tests need neither a database nor an OpenAI key. Their settings are fixed
in `pyproject.toml` (section `[tool.pytest.ini_options]`, through pytest-env)
and take precedence over `backend/.env`: a test cannot reach a real database.

There is one exception, reserved for the CI: with the variable
`TEST_POSTGRES_URL`, the tests run on the CI's disposable PostgreSQL. The
schema is created there by the migrations, and the tables are emptied before
each test. Only `tests/conftest.py` reads this variable, and it refuses any
host other than `localhost` or `127.0.0.1`. The tests marked `postgres`, which
check what only PostgreSQL knows (partial indexes, `CHECK` constraints, JSONB,
time zones), run only there.

Each test has its own in-memory SQLite database, created from the models.
`tests/conftest.py` provides this database, an API client, users and their
authentication headers, starting data (companies, DD types, sessions) and a
fake OpenAI client for the vector stores. The answering engine is also tested
with a fake client (`tests/test_processing.py`).

`npm run lint` accepts no warnings (`--max-warnings 0`) and also checks the
frontend's layers.

**Automatic checks**:
- **On every commit**, pre-commit hooks run ruff and look for files that are
  too large, private keys and OpenAI keys. To install them once, from the root
  of the repository: `uv run --project backend pre-commit install`.
- **On GitHub**, the CI (`.github/workflows/ci.yml`) runs the backend's lint,
  formatting, types, tests and audit, then the frontend's lint, formatting and
  build. It also runs the migrations on a disposable PostgreSQL 17: upgrade,
  `alembic check`, full downgrade then upgrade again, and an up-to-date
  `db/schema.sql`. It then runs the tests again on this PostgreSQL. A failing
  test shows up as an annotation on the pull request. Finally, it builds and
  starts the whole application with docker compose, then uses it through the
  proxy: the application and one of its routes, the security headers, the
  API, the creation of the first administrator and their sign-in. The
  Terraform code (`infra/azure`, `infra/aws`) is checked (`terraform fmt`,
  `terraform validate`), without deploying anything.

## Repository structure

```
backend/              FastAPI API
  app/
    api/              router.py, routes/ (one router per resource), deps.py
    core/             cross-cutting: config, database, security, cache, email
    engine/           answering engine: OpenAI client, runs, syntheses
    services/         business logic and database access
    exports/          PDF report
    models/           SQLModel tables, and what the API reads and returns
  alembic/            database migrations (Alembic)
  db/schema.sql       full SQL script of the schema, generated
  scripts/            questionnaire import and update, database audit
  tests/
  Dockerfile          backend image
frontend/             React application (Vite, Tailwind)
  src/                Feature-Sliced Design, from top to bottom:
    app/              router, providers (theme, sign-in), global styles
    pages/            one page per route
    widgets/          page blocks: layout, dashboard, DD type card,
                      answers, vector stores
    features/         user actions: sign-in, session creation,
                      answer review, administration
    entities/         business objects: API calls, model, small components
    shared/           HTTP client, interface components, utilities
  Dockerfile          frontend image (built by Node, served by nginx)
  nginx.conf          serves the application's files
proxy/                the entry point: nginx in front of the frontend and backend
docker-compose.yml    the four services (proxy, frontend, backend, db)
Makefile              the everyday commands (make alone lists them)
infra/                the Terraform deployment: azure/ and aws/
examples/             example questionnaire in the import format
docs/ARCHITECTURE.md  detailed design
.github/workflows/    continuous integration
.env.template         all the configuration variables
VERSION.md            version of the application and of the tools
CHANGELOG.md          changelog
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): the data model, the
  answering engine, per-user isolation, the syntheses, the PDF export and the
  frontend's design system.
- [`VERSION.md`](VERSION.md): the version of the application and the versions
  of the tools (Python, uv, Node, Docker images, Terraform). The dependency
  versions are pinned in `backend/uv.lock` and `frontend/package-lock.json`.
- [`CHANGELOG.md`](CHANGELOG.md): the changelog.

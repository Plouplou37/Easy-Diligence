# CLAUDE.md

A short guide for an agent working on Easy Diligence. The rest is in:
- [`README.md`](README.md): install, run, test;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): the design (engine, access
  isolation, syntheses, export, design system);
- [`VERSION.md`](VERSION.md): the version of the application and of its tools;
- [`CHANGELOG.md`](CHANGELOG.md): the change log, to be updated with every
  visible change.

## Landmarks

- FastAPI backend in `backend/app/`:
  - `api/`: `router.py` (assembly), `routes/` (one router per resource),
    `deps.py` (shared dependencies);
  - `core/`: cross-cutting concerns (config, database, security, cache,
    e-mail);
  - `engine/`: the answering engine (`openai_client.py`, `processor.py`,
    `summarizer.py`, `errors.py` to classify errors, `answers.py` to create an
    answer). The prompts and parameters sent to OpenAI are pinned by
    `tests/test_question_request.py`: an intended change rewrites
    `tests/data/question_request.json`;
  - `services/`: business logic and database access (sessions, answers, runs,
    vector stores, permissions, authentication, import). A route reads the
    request, calls a service and answers;
  - `exports/`: the PDF report (`pdf.py`), its markdown rendering and its
    sources;
  - `models/`: one file per table (SQLModel), with what the API reads and
    returns for it (create, update, response). Shared fields live in a base
    class;
  - `alembic/`: the database migrations.
- React frontend in `frontend/src/`, in Feature-Sliced Design: `app` > `pages` >
  `widgets` > `features` > `entities` > `shared`. A layer imports only the
  layers below it, and a slice does not import another slice of its own layer:
  `npm run lint` checks it (`eslint-plugin-boundaries`). From one slice to
  another, go through its `index.js` and the `@/` alias.
- The configuration is read by `backend/app/core/config.py`. Every variable is
  described in `.env.template`: a variable added to the code must be added to
  that file too.

## Rules

- **Python with uv only**: `uv sync`, `uv run …`, never pip.
- **No personal or client data in the repository**: no IP address, network
  path, name of a person, client or fund, no secret. Examples and tests use
  made-up names ("Example Asia Fund"). Branding files go in `branding/` and
  questionnaire files in `questionnaires/`: git ignores both folders.
- **Never run a test against a real database.** The test settings in
  `pyproject.toml` (pytest-env) force an in-memory SQLite database and a fake
  OpenAI key: do not remove them. The one exception: CI runs the tests again on
  its throwaway PostgreSQL, through `TEST_POSTGRES_URL`. Only
  `tests/conftest.py` reads that variable, and it refuses any host other than
  the machine itself. Never set it anywhere but in CI.
- **Database schema**: every change goes through the model (`app/models/`),
  then an Alembic migration generated with
  `uv run alembic revision --autogenerate` and **reviewed**, then the
  regeneration of `db/schema.sql`. Never edit a published migration: add a new
  one. Never bring `create_all` back into the application.
- **Errors**: never send `str(e)` to the client. For an expected error, raise an
  exception from `core/exceptions.py`, whose message is written for the user.
  For anything else, `logger.exception(...)` and then a generic message.
- **Routes as plain `def`**: FastAPI runs them in a thread pool. An `async def`
  that calls the database or OpenAI, two synchronous libraries, blocks the
  whole server. `async def` is kept for routes that read an uploaded file
  (`read_upload`); they hand the rest to the pool with `run_in_threadpool`.
- **A session or a DD type read from the URL** goes through the
  `get_accessible_session` and `get_visible_dd_type` dependencies of
  `api/deps.py`, which check permissions.
- **In a model, `Field` is SQLModel's, which silently ignores `pattern` (and
  `regex`).** For a pattern, use `pydantic.Field` (see `models/user.py`).
  `max_length`, `ge` and `le` are applied.
- **Authentication**: every endpoint that needs a user goes through
  `api/deps.py` (`get_current_active_user`, `get_current_admin_user`). Do not
  decode a token anywhere else.
- **Uploaded files**: read them with `api/uploads.read_upload`, which enforces
  the size and the allowed extensions.
- **Frontend**: only the theme's color tokens, no Tailwind palette, no `dark:`
  variant. Adding a color class to `Button` is forbidden.
- **A field sent to the model must be visible in the interface.**
- Do not validate a DD type for convenience: validation cannot be undone.
- Everything in English: documentation, comments, commit messages. A commit
  message or a changelog entry says what the change does, nothing else.

## Checking a change

```bash
# backend/
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy app
# frontend/
npm run build
npm run lint
npm run format:check   # npm run format to fix
```

From the root, `make check` runs all of the above.

- CI also runs `pytest` a second time, on PostgreSQL, with the tests marked
  `postgres` (skipped locally). A failure there shows up as an annotation on
  the pull request.
- Ruff and mypy pass on the whole backend, engine included. **Do not add
  `# noqa`**, nor `# type: ignore`, nor an `ignore_errors` section for mypy
  (`pyproject.toml`). Logging calls pass their values as arguments
  (`logger.info("… %s", x)`), never as an f-string: ruff checks it (`G004`).
- `npm run lint` passes without a single warning (`--max-warnings 0`), and CI
  checks it. No `eslint-disable`: fix the code.
- **Frontend**: a confirmation goes through `useConfirm()`, a dialog through
  `Modal` (never `window.confirm` nor a hand-made dialog), a field through
  `Input` or `PasswordInput` (`shared/ui`).

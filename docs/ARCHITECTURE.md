# Architecture

This document describes the design of Easy Diligence: the choices behind the
answering engine, the access isolation rules, the features and the frontend
design system. To install and run the application, see the
[README](../README.md).

## Stack

- **Backend**: FastAPI (Python 3.12), SQLModel models (SQLAlchemy 2 and
  Pydantic), PostgreSQL 17 via psycopg 3, Alembic migrations.
  Code in `backend/app/`, routes under the `/api` prefix:
  - `api/`: the router assembly (`router.py`), one router per resource
    (`routes/`) and the shared dependencies (`deps.py`: the user, and the
    session and DD type read from the URL, with access rights checked);
  - `core/`: cross-cutting concerns (configuration, database, security, cache,
    e-mail);
  - `engine/`: the answering engine;
  - `services/`: business logic and database access (`sessions`,
    `answers`, `processing`, `vector_stores`, `dd_types`, `authz`, `auth`,
    `file_parser`). Services raise the errors of `core/exceptions.py` and know
    nothing of FastAPI;
  - `exports/`: the PDF report;
  - `models/`: one table per file, with its API shapes: a base class carries
    the fields and their limits, and the table, the creation form and the
    response inherit from it.
- **Frontend**: React 18, Vite 8, Tailwind 4, axios and react-router 7. Code in
  `frontend/src/`.
- **LLM**: OpenAI's **Responses** API (`client.responses.create`). The model
  is chosen by `OPENAI_MODEL`. `openai_client.is_reasoning_model()` adapts the
  parameters to the model: no `temperature` on reasoning models (GPT-5.x), the
  name of the web tool (`web_search` or `web_search_preview`), the output
  budget and `reasoning.effort`. Switching from `gpt-5.6-luna` to `gpt-4o`
  therefore only takes a change to this variable.
- **Authentication**: JWT access and refresh tokens (PyJWT), passwords hashed
  with bcrypt, `admin` and `analyst` roles. See
  "Authentication and security".
- **Long-running tasks**: FastAPI's `BackgroundTasks`, in the web process.

## Deployment

The application runs with docker compose (`docker-compose.yml`, README
"Running the application"), as four services:

```
browser ──► proxy ──/api──► backend ──► db
              └──── / ────► frontend
```

- **`proxy`** (`proxy/default.conf.template`): the only entry point, and the
  only published port. All traffic rules live there:
  - the upload size (110 MB, for the 100 MB of `MAX_UPLOAD_SIZE`);
  - 10-minute timeouts on `/api`, for regenerations and syntheses that wait
    on OpenAI;
  - the security headers, and a `/healthz` of its own;
  - `X-Forwarded-For`, **set** rather than appended to: a header sent by the
    client cannot choose the address that the login limits count. Behind a
    trusted proxy (`TRUSTED_PROXIES`: Azure's ingress, AWS's load balancer),
    the client address is read from that proxy's `X-Forwarded-For`, starting
    from the right;
  - the upstream services (`BACKEND_UPSTREAM`, `FRONTEND_UPSTREAM`),
    **resolved on every request**: a backend recreated by an update is
    reached at its new address without restarting the proxy;
  - `Host` carries the upstream service's name: Azure's internal ingress
    routes on it.

  It is a template, rendered from these variables when the container starts.
  `proxy/Dockerfile` gives the docker compose values, `infra/` the cloud
  ones.
- **`frontend`**: the application built by Node, served as static files by
  nginx (`frontend/nginx.conf`). Files under `assets/` carry a fingerprint and
  are cached for good; every other route gets `index.html`, which is never
  cached.
- **`backend`**: the Python image with uv (`backend/Dockerfile`), running as
  an unprivileged user. On startup, `alembic upgrade head`, then uvicorn.
  uvicorn trusts the proxy's headers (`--forwarded-allow-ips '*'`): only the
  proxy can reach the backend.
- **`db`**: PostgreSQL 17, data in the `db-data` volume. No published port.
- Services reach each other by name, with no hard-coded address. They start
  in the order of their health checks: `db`, then `backend` and `frontend`,
  then `proxy`.
- Settings come from a single `.env` at the root. `docker-compose.yml` forces
  the `db` database on the backend, whatever the file says for a manual
  launch.
- No Redis: the cache falls back to memory.
- Image versions are pinned (`VERSION.md`). CI builds and starts the whole
  stack on every pull request, then uses it through the proxy.

### In the cloud (`infra/`)

The same images, on managed services, described in Terraform, with a choice
of two clouds:

| | Azure (`infra/azure/`) | AWS (`infra/aws/`) |
| --- | --- | --- |
| Containers | Container Apps | ECS on Fargate |
| Public entry, HTTPS | the proxy, HTTPS provided on `*.azurecontainerapps.io` | a load balancer in front of the proxy, HTTPS with a domain and its ACM certificate |
| Database | PostgreSQL Flexible Server 17, private | RDS PostgreSQL 17, private |
| Secrets | Key Vault, read by a managed identity | Secrets Manager, read by the execution role |
| Images | Container Registry, built by `az acr build` | ECR, pushed by `docker push` |
| Internal names | the Container Apps' names | Cloud Map (`backend.<…>.internal`) |

- **The backend stays at a single instance, always on**: a run lives in its
  process. On AWS, the old task stops before the new one starts, so there are
  never two engines, or two migrations, at once.
- **Secrets**: the database URL and the JWT key are generated by Terraform.
  They are also in its state, kept in a storage reserved for those who
  deploy. The OpenAI key is set by hand: Terraform never sees it.
- CI checks this code (`terraform fmt`, `terraform validate`) without
  deploying anything. Deployment is started by hand, following each folder's
  README.

## Database

- **PostgreSQL**, configured by `POSTGRES_*` or `DATABASE_URL`
  (`core/database_settings.py`). Tests run on in-memory SQLite.
- **Alembic owns the schema**: `alembic upgrade head` creates the database,
  then applies each change, without touching the data. The application
  creates no table at startup.
  - Migration `0001_initial_schema` creates the whole database. It was
    generated from the models, then reviewed. It carries the final state of
    the old SQL fixes applied by hand to the MySQL database: the indexes, the
    cascades and the `CHECK` constraints.
  - Migration `0002_integrity` sets the integrity rules (below). It first
    fixes the data that violates them, and stops without changing anything
    when it meets data that needs a decision.
    `scripts/audit_integrity.py` lists that data before migrating.
  - Migration `0003_dead_columns` removes the dead columns
    (`dd_sessions.status`, `dd_answers.confidence_score`,
    `dd_executions.validator_id`, `users.is_verified`). It also replaces the
    JSON copy `dd_sessions.dd_types_json` with the `session_dd_types` table:
    a code that matches no DD type is left out, and counted in the log.
  - `db/schema.sql` is the same schema as a single SQL script, regenerated
    with `alembic upgrade head --sql`.
  - `alembic check` verifies that the migrations match the models.
  - Alembic reads only the database settings (`DatabaseSettings`): a
    migration needs neither the OpenAI key nor the JWT key.
  - **CI checks the migrations on a real PostgreSQL 17** (a disposable
    service of the `backend` job, with credentials specific to CI):
    `upgrade head`, `check`, `downgrade base`, then `upgrade head` again
    (every downgrade is run), and `db/schema.sql` compared with a regenerated
    script. `DATABASE_URL` is set only for these steps.
  - **Tests run twice in CI**: on SQLite, as locally, then on this
    PostgreSQL, with `TEST_POSTGRES_URL`. This variable is read only by
    `tests/conftest.py`, which requires a local host. The schema is then
    created by `alembic upgrade head`, as in production, not by
    `create_all`. Tables are emptied (`TRUNCATE … RESTART IDENTITY`) before
    each test, and a lock wait of more than 10 s fails the test instead of
    blocking CI. Tests marked `postgres` (`test_postgres.py`) run only there.
  - **Lists have a stable order** (`ORDER BY` down to the id). SQLite
    returns rows in insertion order, PostgreSQL does not, and `now()` gives
    every row of a transaction the same time.
- **Models** (`models/`) are in SQLModel: each table is both a SQLAlchemy
  model and a Pydantic model. `models/base.py` sets:
  - a **naming convention** for constraints, so that migrations can find
    them by name;
  - the JSON type (JSONB under PostgreSQL);
  - dates as `TIMESTAMP WITH TIME ZONE`, filled in by the database;
  - enumerations, stored as text with a `CHECK` constraint rather than as a
    native `ENUM` type: adding a member needs no `ALTER TYPE`. The **value**
    is stored, in lower case (`needs_review`):
    `enum_type(…, store_values=True)`;
  - required columns with a default (`defaulted_field`): NOT NULL, and the
    default is set **by the database** too, so that an insert in plain SQL
    gets it.
- **The database enforces its own rules**: the code assumes nothing the
  database does not guarantee.
  - One run per session and DD type; at most one current answer per run and
    question (partial unique index `WHERE is_current`); one synthesis per
    session, DD type and section; one vector store assignment per session,
    DD type (or the whole session) and vector store, pointing to a DD type
    that exists; section codes unique within a DD type, and question codes
    unique within a section.
  - For SQL, two NULLs are different. The global synthesis (`section_id`
    NULL) and the assignment to the whole session (`dd_type_id` NULL)
    therefore each have a partial unique index (`… WHERE section_id IS
    NULL`), rather than a PostgreSQL-specific `NULLS NOT DISTINCT`: SQLite
    supports partial indexes too, so the tests see the rule.
  - No boolean, status, counter or creation date is NULL; each status has
    its `CHECK` constraint, and so does `users.role`. Only
    `dd_summary_batches.status` stays free: it carries OpenAI's statuses,
    which may change.
  - A violation is never a 500 error. The code catches the `IntegrityError`
    and responds as if its own check had seen the conflict: a code already
    taken gives a 409, an assignment or a synthesis already there is reused.
    A synthesis is inserted inside a savepoint, so that its failure leaves
    the rest of the transaction in place.
- **Indexes**: PostgreSQL does not index foreign keys automatically, unlike
  MySQL. Join columns are therefore indexed explicitly in the models.
- **Typed queries**: SQLModel types columns as Python values. For mypy to
  accept a filter, wrap the column in `col()`:
  `.filter(col(User.id) == user_id)`.
- **Real transactions**: nothing is written before `commit()`, and
  `rollback()` undoes everything since the last commit. The original MySQL
  database forced autocommit at the driver level, so rollbacks had no
  effect.
- **E-mail addresses**: stored and compared in lower case
  (`models/user.py`, `Email` type). PostgreSQL compares text
  case-sensitively.

## Data model

- `DDType` (`models/dd_types.py`) → `DDSection` → `DDQuestion`
  (`models/questions.py`). A DD type is a questionnaire.
- `Company` (`models/company.py`) holds two entities: the **fund** under
  review (`name`, `website_url`) and its **management company**
  (`management_company_name`, `management_company_website`, optional).
  Keeping them apart lets the engine know which one a question is about.
- `DDSession` (`models/session.py`): a DD on a fund (`company_id`,
  `created_by`, `assigned_to`). **A session has no status of its own**: its
  state is that of its runs. The frontend computes it (`getSessionStatus`),
  and the deletion guard reads it by the same rule.
- `SessionDDType` (`session_dd_types`): the DD types chosen when a session is
  created, in the chosen order (`position`). It is a link, not a copy: a
  renamed type appears under its new name, and a type that a session chose
  cannot be deleted (`RESTRICT`, then 409 in `delete_dd_type`). The API
  exposes it in `SessionResponse.dd_types` (`[{id, code, name}]`).
- `DDExecution` (`models/execution.py`): the run of **one** DD type in a
  session, only one per pair. Statuses (`ExecutionStatus`): `not_started`,
  `in_progress`, `generated`, `failed`, `paused`, etc. It carries the
  `conversation_id`.
- `DDAnswer` (`models/answer.py`): a run's (`execution_id`) answer to a
  question (`question_id`), versioned by `version` and `is_current`, with
  `status`, `response_id` and `sources` (JSON). History goes into
  `DDAnswerHistory`.
  - **Copies**: `session_id`, `dd_type_id` and `section_id` follow from the
    run and the question. They are kept for the dashboard indexes and the
    review page filters. `section_code` and `question_code` are a **copy
    taken at answer time**: a code changed later does not reach older
    answers. A single function fills them: `engine/answers.new_answer`.
  - A question or section that has answers cannot be deleted (409).
- `DDResponse` and `DDMessage`: OpenAI's raw responses and messages, chained
  by `previous_response_id`.
- `VectorStore` and `SessionVectorStore` (`models/vector_store.py`): the
  OpenAI vector stores and their assignment to sessions and DD types.
- `DDSummary` (`models/summary.py`): the generated summaries, per section or
  for a whole DD type.
- `DDSummaryBatch`: tracking of the syntheses sent to the Batch API.

### Deleting a session

- Only its creator can delete it, and deletion takes everything with it: the
  runs, the answers and their history, the links to its DD types and its
  vector store assignments.
- **Not during a run**: the background task would keep writing to deleted
  rows.
- **Not once finished**: when every chosen DD type (or, with no choice,
  every type that was started) has finished (`generated`, `under_review`,
  `validated`, `finalized`), the DD is kept.
- `services/sessions._deletion_refusal` checks this from the runs, and the
  frontend button locks on the status computed by the same rule. If the
  server refuses, its message is shown.

### Lifecycle rules

- **Inactive means "not offered", not "invisible".** Only the session
  creation screen (`SessionCreate.jsx`) filters on `is_active`. Screens that
  show existing data also load inactive types; otherwise, deactivating a type
  would silently hide the answers produced under it. Starting is blocked by
  `canStartDD` (`SessionDetail.jsx`), and `DDCard` shows an "Inactive"
  badge.
- **Validating a DD type is one-way.** A draft type is fully usable:
  `is_validated` plays no part in the engine or in `/processing`. Validation
  only freezes the **structure** (`check_*_immutability`,
  `api/routes/questions.py`), and no endpoint can un-validate.
- `PUT /company/{id}` expects a **complete** `CompanyCreate`, not a patch: a
  partial body erases the other fields.

## The answering engine

`engine/processor.py` (`DDProcessor`) orchestrates a run: `start_processing`
and `resume_processing` go through the same loop (`_run`); resuming only
chooses the questions. `engine/openai_client.py`
(`OpenAIProcessor.process_question`) makes the call to OpenAI.
`engine/errors.py` classifies errors, and `engine/answers.new_answer` creates
an answer row. The service creates the run and sets it to `in_progress`
(`services/processing.py`); the engine receives its id, the DD type's id and
its code.

### One transaction per question

- The OpenAI call happens **outside any transaction**. The engine finishes
  reading before the call, and no transaction stays open during the
  15 seconds it lasts.
- Then **a single transaction** writes everything the question produced: the
  raw response (`DDResponse`) and its messages, the old answer set aside
  (`is_current = false`), the new answer and the first version of its
  history. One commit, and a rollback on error: a failure between the call
  and the write leaves the question as it was.
- Same rule for a failure (the failed answer replaces the current one) and
  for a regeneration (the new version, its history row, the raw response).

### Errors and retries

- **Classification follows the class of the exception** raised by the
  `openai` SDK, never its text (`errors.classify`):

  | Exception | Type | Retried |
  | --- | --- | --- |
  | `RateLimitError` | `rate_limit` | yes |
  | `APITimeoutError` | `timeout` | yes |
  | `APIConnectionError` | `network_error` | yes |
  | `BadRequestError` (`context_length_exceeded`) | `context_overflow` | no |
  | other `BadRequestError`, `UnprocessableEntityError` | `validation_error` | no |
  | `AuthenticationError`, `PermissionDeniedError` | `api_error` | no |
  | `InternalServerError`, other 5xx error | `api_error` | yes |
  | `ResponseError` (empty or incomplete response) | `api_error` | yes |
  | everything else | `unknown` | yes |

- **One retry policy, the engine's**: the SDK is created with
  `max_retries=0`. The engine makes at most 3 calls per question
  (`MAX_ATTEMPTS`). It waits for the delay OpenAI asks for (`Retry-After`),
  otherwise for an exponential backoff by type, capped at 60 s.
  `retry_count` counts the actual retries. Previously, the SDK also retried
  twice under each attempt, up to nine calls for one question.
- **Circuit breaker**: a global error (`rate_limit`, `network_error`,
  `api_error`), which every question would hit, stops the run at the first
  occurrence (`CIRCUIT_BREAKER_THRESHOLD = 1`). The run ends `failed`, and
  "Resume" picks up from there.
- **The user never reads OpenAI's text**: `error_message` receives a message
  written for the user, derived from the type (`errors.MESSAGES`), and
  `/session/{id}/status` returns it in `last_error`. Technical detail goes
  only to the logs (`logger.exception`).
- **Final status**, decided in one place (`_final_status`): interrupted by a
  pause, the run stays `paused`; with at least one failed question, it ends
  `failed`; otherwise `generated`. An error in the run itself (rather than in
  a question) ends it `failed`.

### One call, two tools

Each question gives rise to **a single call**, with two tools: `file_search`
on the attached vector stores, and `web_search`.

- **`tool_choice`** (`TOOL_CHOICE`, `web_search` by default) forces the tool
  of the first call:
  - `web_search` forces a web search on every question;
  - `auto` lets the model choose;
  - `none` sends no `tool_choice`.

  An unknown value falls back to `web_search`, with a warning. A caller that
  passes an explicit value keeps control.
- **Why `web_search` by default.** A comparison on the same questionnaire
  and the same documents showed that `auto` saves almost nothing in input
  tokens, since the chained conversation dominates. On the other hand, the
  model then skips the web on most questions: web citations collapse, more
  answers come back without a source, and the questions about the management
  company suffer most. The documents describe the fund, whereas the
  manager's public footprint exists only on the web. Forcing the web does not
  stop the model from consulting the documents afterwards.
- **The search rule in the system prompt.** Forcing a tool decides only the
  **first** call: the model remains free to skip the other one.
  `_build_system_prompt` therefore requires using **both** tools on every
  question, and says what each one is for. With no vector store attached
  (`has_documents=False`), the rule becomes: "web only, and say what could
  only come from the documents". The model must never suggest that it has
  read documents. This rule costs about 30% more time, for answers that are
  clearly better sourced.
- `regenerate_single_answer` sends `"auto"` when the regeneration is guided
  by an instruction from the analyst.
- The API sometimes echoes back `tool_choice: {"type": "web_search_preview"}`
  even though `web_search` was sent. The response's `tools` list is
  authoritative: this is not a fallback to the old tool.
- Ruled out: two calls per question, one per tool. It is the only absolute
  guarantee that both tools are used, but it doubles the cost and the time,
  since each call sends the whole chained conversation again.

### Fund and management company

The system prompt (`_build_system_prompt`) names `FUND UNDER REVIEW` and
`MANAGEMENT COMPANY` separately. It then sets a **scope rule** based on the
`Level: Fund` or `Level: Management Company` marker that each question of
the reference questionnaires carries.

This context is built by `build_company_info()` in `core/utils.py`, the
single source for the three callers: start, resume and regenerate. When no
management company is filled in, the block is omitted. Behavior is then
degraded, but not broken.

### What the model receives

`DDProcessor.compose_question_text()` assembles:
1. the section title;
2. the section's `description`, if it is filled in;
3. the question text;
4. its `context_prompt`, under the label **`Where to look:`**.

- The **`context_prompt`** holds the sources to consult. It is editable in
  `QuestionEditor.jsx` ("Where to look") and reaches the model under the
  same label, whatever column it came from in the source workbook.
- The section **`description`** gives context for the theme. Like every
  field sent to the model, it is visible in the interface
  (`SectionCard.jsx`).
- The **reference** (`A.01`) is not in the text sent. It lives only in
  `question_code`, which is not sent.

### Citations and sources

- **No document citation markers in the text.** Under `gpt-5.6-luna`, OpenAI
  returns an `output_text` with holes in it: each hole falls on a
  `file_citation.index`, and the offset grows from one citation to the next.
  The `url_citation.start/end_index` values drift too. The defect is
  OpenAI's: their copy read back with `responses.retrieve` has the same
  holes, and streaming changes nothing. `gpt-4o` does not have the problem.
  - **The workaround**: when documents are attached, `_build_system_prompt`
    forbids these markers. The model then names the documents in plain text
    and ends its answer with a `Documents consulted:` line
    (`CONSULTED_LABEL`), visible in the interface and in the PDF.
  - **Document sources**: `documents_consulted()` rebuilds them from this
    line. It keeps only the files actually returned by
    `file_search_call.results`, and ignores case, the extension and a
    leading number ("1. PRIVATE…").
  - **The safety net**: if the model cites anyway, `process_question`
    retries **once**. The tokens of the discarded call are counted.
- **Orphan markers.** `strip_citation_markers` removes the markers that the
  model sometimes leaves without an annotation. It runs when the answer is
  finalized, before the empty-answer check. Three forms, all from OpenAI:
  - an empty `【】`;
  - `【4:0†source.pdf】`, recognizable by its `†`;
  - the `turn7file6` token. It is preceded either by `【`, or by the
    private-use character U+E200 followed by a label and U+E202. Several
    tokens can be chained by U+E202, and the whole is closed by U+E201.

  Any other text between `【】` is kept. ⚠️ The private-use characters are
  built with `chr(0xE200)` in the code: written as is, they would be
  invisible in an editor.
- Tests: `tests/test_citation_format.py`.

### Memory, compaction and limits

- **Memory.** The questions of a run form a conversation chained by
  `previous_response_id`, in `order_index` order. `truncation="auto"` is sent
  to OpenAI.
- **Compaction.** Chaining grows the input by about 4,000 tokens per
  question. A questionnaire of nearly 300 questions would thus exceed the
  model's context window. Beyond `COMPACT_THRESHOLD` (200,000 by default, see
  `openai_client._apply_compaction`), the history is compacted instead of
  being silently truncated. The `context_management` parameter goes through
  `extra_body`, because the SDK does not know it yet.
- **Reasoning model parameters** (`_apply_model_params`):
  - no `temperature`;
  - `max_output_tokens` of at least 25,000 (the
    `REASONING_MIN_OUTPUT_TOKENS` constant in `openai_client.py`), because
    reasoning tokens count against it;
  - `reasoning.effort` set by `REASONING_EFFORT` (`low`).
- **Rate limiting** (`engine/rate_limiter.py`): all pauses are disabled by
  default. A regular OpenAI account's quotas are far above what a run
  consumes, and 429 errors are covered by the engine's retries and circuit
  breaker ("Errors and retries"). The variables
  `INTER_QUESTION_DELAY_SECONDS`, `BATCH_SLEEP_MINUTES` and
  `HIGH_TOKEN_SLEEP_SECONDS` remain as a safety valve.
- **Duration.** Count about 15 seconds per question.

### Pause, resume and background tasks

- **Pause**: sets `execution.status` to `paused`. The loop checks it
  **between two questions**, so stopping is not instantaneous.
- **Resume**: keeps the `conversation_id`, skips the questions whose current
  answer is good and retries the others (no answer, or failed).
- The engine does not set the status back to `in_progress` itself: the
  service does. A pause clicked before the background task starts is
  therefore no longer overwritten. At the end of a run, the final status is
  written only if the run is still `in_progress`: a pause that arrived after
  the last question stays.
- **A status change is a single conditional `UPDATE`**
  (`services/processing._switch`): `… WHERE id = … AND status IN (…)`, and
  the number of rows touched says who won. Two clicks, or two tabs,
  therefore never start two runs. Two simultaneous first starts collide on
  the uniqueness of the run: the second one reads back the run of the first.
- Runs execute in `BackgroundTasks`, in the web process. A server restart in
  the middle of a run leaves the run `in_progress`: it must then be started
  again with "Resume".
- **A run is stuck** when it is `in_progress` but neither its execution nor
  its answers have changed for 10 minutes (`STUCK_AFTER`). "Resume" then
  takes it over, only once. The execution's timestamp alone is not enough:
  the engine touches it only at the start and at the end of a run, which can
  last more than an hour.

## Authentication and security

- **Required settings**:
  - `DATABASE_URL`, `OPENAI_API_KEY` and `JWT_SECRET_KEY` (at least
    32 characters) have no default value. They are `SecretStr` values, which
    show neither in logs nor in representations;
  - if one is missing, `core/config.py` stops startup with the list of the
    variables to set;
  - `backend/.env` is found whatever the launch folder, and environment
    variables take precedence over it.
- **Roles**: `Literal["admin", "analyst"]` (`models/user.py`).
  - **No open sign-up.** An administrator creates the accounts
    (`POST /admin/users`, `UserCreate`): a chosen role, and a temporary
    password that the user changes in their profile. `UserCreate` rejects any
    unknown field.
  - The first administrator is created with `python -m app.cli create-admin`
    (`app/cli.py`), which prompts for the password at the keyboard.
  - **Deleting an account** (`services/users.py`) is possible only if it
    owns nothing: no session (created or assigned), and no company, DD type,
    vector store, edited answer or synthesis. Otherwise, it is deactivated.
    Deletion used to clear these links, and a company with no creator is
    shared with everyone.
- **A single authentication dependency**: `api/deps.py`
  (`get_current_active_user`, alias `get_current_user`, and
  `get_current_admin_user`). It is the only place where a token is decoded,
  and where an inactive account is refused.
- **Tokens** (`core/security.py`):
  - each token carries a random `jti`. Without it, two tokens issued in the
    same second were identical;
  - `user_sessions` stores only their SHA-256;
  - the refresh token goes in the body of `POST /auth/refresh`, never in the
    URL, and it is replaced on every use;
  - the password reset token carries a fingerprint of the current password:
    it stops working as soon as the password changes. It therefore works
    only once, without being stored. The link in the e-mail leads to
    `/reset-password?token=…` (a public page), which sends it to
    `POST /auth/reset-password-confirm`;
  - the link request gets the same response, just as fast, whether or not
    the address exists: the e-mail goes out in a background task, after the
    response.
- **Login throttling** (`core/login_throttle.py`): after
  `LOGIN_MAX_ATTEMPTS` failures within `LOGIN_WINDOW_SECONDS`, the account
  gets a 429 with `Retry-After`. A single IP address is allowed four times as
  many failures. The counter lives in memory, which is enough for a single
  backend process.
- **Passwords**: at least 8 characters, with an upper-case letter, a
  lower-case letter and a digit, and at most 72 bytes, the limit that bcrypt
  reads.
- **Uploaded files**: `api/uploads.read_upload` enforces `MAX_UPLOAD_SIZE`
  (413) and `ALLOWED_EXTENSIONS` (400). Questionnaire import has its own list
  of extensions.
- **Errors**:
  - expected errors are exceptions from `core/exceptions.py`, free of
    FastAPI, which `main.py` translates into HTTP codes. Their message is
    written for the user;
  - any other exception is logged with its traceback and gets
    "Internal server error". Neither a driver's message nor an OpenAI
    response goes to the browser;
  - the last safety net (`UnhandledErrorMiddleware`) sits under the CORS
    middleware, so even a 500 carries the CORS headers.
- **API documentation**: `/docs`, `/redoc` and `/openapi.json` are served
  only if `DOCS_ENABLED=true`.
- **Logs** (`core/logging_setup.py`): the application logs from `LOG_LEVEL`
  up (INFO by default), third-party libraries from WARNING up. In the logs,
  a user is referred to by their id, never by their e-mail address or name.

## Per-user access isolation

Rule: **the administrator sees everything**, other users see only their own
data. The shared functions are in **`services/authz.py`**: `user_is_admin`,
`filter_*_for_user` and `assert_*_access/ownership`.

- **Sessions**: visible to their creator (`created_by`) or to the assignee
  (`assigned_to`).
- **Answers and runs**: isolated by the session that holds them.
- **DD types**: private (`created_by`). Those that are `is_system` or have no
  creator (`created_by IS NULL`) are **shared**. Any user can create one.
  Only the owner or an administrator can validate them.
- **Vector stores**: the list is filtered by `created_by`, and access to the
  files is reserved for the owner.
  - **Stores gone at OpenAI**: a read deletes nothing. An expired or missing
    store appears with the status `expired` or `missing`, and
    `POST /vector-stores/refresh` (the Refresh button) removes it from the
    database along with its assignments.
  - The frontend (`entities/vector-store/lib/storeState.js`) marks these
    stores ("Expired", "Gone") without figures, does not request their
    files, no longer offers them for assignment, and flags, on a DD type's
    card, an assigned store that has disappeared.
  - **Assignments**, on the other hand, are shared: a colleague's store can
    serve a session. The session's card therefore reads the store's name
    from the assignment (`vector_store_name`), not from the filtered list.
    Anyone who has access to the session manages its assignments.
  - **Scope of an assignment**: `session_vector_stores.dd_type_id` points to
    a specific DD type, `NULL` to the whole session.
    `processing.vector_store_ids_for` gives priority to the type's own
    assignment.
  - **Cache**: the list of stores and each store's files are kept for five
    minutes (they query OpenAI). Any change clears all of it.
- **Companies**: filtered by `created_by`. Those without a creator are
  shared.
- **`/processing`** (`start`, `pause`, `resume`, `progress`): the session and
  the DD type go through the shared dependencies. Another user's private DD
  type cannot be started (404).
- **Creating a session**: only the DD types that the user can see are kept.
- Frontend: the interceptor in `shared/api/client.js` handles 403 responses.
  The `/dd-types` and `/questions` pages are open to all roles.

## Features

### Regenerating an answer

`POST /answers/{id}/regenerate` (`api/routes/answers.py`,
`DDProcessor.regenerate_single_answer`) creates a new version with the status
`needs_review`. The context sent to the model includes the previous answers.
The button is on each answer (`AnswerCard`). If OpenAI fails despite the
retries, the request responds with the message written for the user
(`ExternalServiceError`), and the answer stays as it was.

### Syntheses

`engine/summarizer.py` first writes one summary per section, in parallel,
then one synthesis per DD type (3 to 4 pages) from those summaries. These
are pure writing calls, without tools. The module is synchronous: only the
OpenAI calls for the section summaries go out in parallel, in a
`ThreadPoolExecutor` (8 at most). Database writes stay in the request's
thread, and the routes stay `def`. Storage is in `dd_summaries` and the API
in `api/routes/summaries.py`:
- `POST /summaries/session/{id}/dd/{ddType}/generate`;
- `GET /summaries/session/{id}`;
- `PUT /summaries/{id}`.

A synthesis can be generated from partial answers. Running it again
overwrites the previous one.

**Through the Batch API.** `/v1/responses` is eligible for Batch, with a 50%
discount, but its only window is 24 hours. Syntheses, however, are made in
two stages: batching both would chain two windows. Only the section summary
stage therefore goes through Batch, and the final synthesis stays a
synchronous call, made at collection time.
- `openai_client`:
  - `build_summary_request_params` builds a request body shared by both
    paths, so that they do not diverge;
  - `submit_summary_batch`, `get_batch`, `fetch_batch_texts` and
    `extract_output_text` handle the batch.

  ⚠️ The order of the output lines does not follow the order of the input:
  matching goes through the `custom_id` (`section-{id}`).
- Endpoints:
  - `POST /summaries/.../generate/batch` starts the batch;
  - `GET /summaries/.../batch` tracks its state and does the collection;
  - `POST /summaries/.../batch/cancel` cancels it.
- **Collection happens in the GET**, which the frontend
  (`features/summaries/model/useSynthesis.js`) calls every 15 seconds. A
  background task would not survive a restart, whereas a batch can live for
  24 hours.
- The engine's synthesis functions are coroutines that also call the
  database and OpenAI synchronously. The routes are therefore `def`: each one
  runs its coroutine in its own event loop (`asyncio.run`), on its own pool
  thread. As `async def`, they blocked the whole server during the OpenAI
  call, on every poll.
- The state is tracked in `dd_summary_batches`, one row per session and DD
  type. Running again replaces the row.
- **Cancellation** first reads the state back from OpenAI. The stored status
  changes only when polled, and may still say `in_progress` for a batch that
  has finished in the meantime: cancelling it would throw away results
  already paid for. Only a batch that OpenAI reports as in progress is
  therefore cancelled, and the requests already completed remain billed.
- Batch has no guaranteed turnaround: a batch can sit in the queue for a
  long time. The synchronous path therefore remains the default button.
- The question engine, for its part, cannot move to Batch: `web_search` is
  refused there.

### Reasoning effort

`REASONING_EFFORT` (questions, `low`) and `SUMMARY_REASONING_EFFORT`
(syntheses, `medium`) are two separate settings:
- answering means extracting from documents already retrieved;
- summarizing is pure writing, where reasoning pays off.

The Batch discount roughly offsets the extra cost of `medium`. Reasoning
tokens are billed as output and count against the
`REASONING_MIN_OUTPUT_TOKENS` cap. If a synthesis comes back `incomplete`,
this cap is the one to raise.

### PDF export

`exports/pdf.py` produces a two-level report (markdown rendering is in
`exports/markdown.py`, reading of the sources in `exports/sources.py`):
- the body: the synthesis of each DD type;
- the appendices: for each section, its summary, then the questions, the
  answers and the sources.

Without a synthesis, the report contains only the detail.
- The question's reference (`A.01`) is put back in front of its text, from
  the `question_code`.
- **Branding**: the banner, which is optional, is read from
  `BRAND_BANNER_PATH`; if the file is missing, the report comes out without
  it and a warning is logged. The colors (`PDF_PRIMARY_COLOR`,
  `PDF_TEXT_COLOR`, `PDF_RULE_COLOR`) and the footer notice
  (`PDF_FOOTER_NOTICE`) also come from the configuration.
- The function returns bytes; the route builds the HTTP response.
- **Wide markdown tables**: each column first gets a minimum width
  (`_COL_MIN_POINTS`). If the table does not fit, the cell padding is
  reduced. Beyond about 40 columns, it is written as lines of text.
- The markdown horizontal rule (`---`) still comes out as plain text.

There is no Excel export. The review page's CSV export is built in the
browser.

### Dashboard

`GET /api/dashboard/sessions` (`api/routes/dashboard.py`) returns in one call
everything the dashboard shows, in about eight grouped queries whatever the
number of sessions.
- It is **read-only**: the state of the batches is read from
  `dd_summary_batches`, never through the batch GET, which calls OpenAI.
- Formatting is done by the pure function `build_dashboard_rows`, tested by
  `tests/test_dashboard.py`.
- The table refreshes every 15 seconds, **only** if a run or a batch is in
  progress.
- "Stuck?" signal: a run that is `in_progress` with no new answer for
  10 minutes.
- **"To review"** counts the current answers not yet approved, excluding
  failures (`completed`, `needs_review`, `draft`, `rejected`). A fresh answer
  from the model is `completed`, not `needs_review`.

## Questionnaire import format

The parser is `services/file_parser.py`; an example is in
[`examples/example_questionnaire.json`](../examples/example_questionnaire.json).
Questionnaire files kept locally go in `questionnaires/`, which git ignores.

```json
[
  {
    "section": "Section title",
    "description": "Optional: the theme, sent to the model with the title",
    "questions": [
      "A question as plain text",
      {"ref": "A.01", "text": "Question text", "context_prompt": "Where to look"}
    ]
  }
]
```

- A question is either a **string** or an **object**. The object form keeps
  the reference and the sources in their own fields.
- The Excel or CSV file has two columns, section then question, with a
  header row; the section is written only on its first row.
- `POST /dd-types/import` **always** creates a new DD type.

### Section and question codes

`services/question_codes.py`:
- a section takes the **letter of its position**: A, B… Z, then AA, AB…;
- a question takes **its section's letter and its rank**: `A.01`, `A.02`;
- if the JSON file gives a **reference** (`ref`, the numbering of the
  questionnaire's provider), it becomes the code. A reference that appears
  twice in the file is ignored: those questions take a rank code, and no
  code repeats within a questionnaire;
- a section or question created on screen takes the next letter or rank;
- codes are unique **only within a questionnaire**: each one has its own
  `A.01`. Nothing looks up a question by its code (everything goes through
  its id), but filtering answers by section also requires the DD type, and
  the export follows the order of the questionnaire, not the order of the
  codes;
- the database guarantees this uniqueness (one section per code in its DD
  type, one question per code in its section): a code already taken gives a
  409;
- the code is the reference displayed: by the on-screen badge
  (`entities/dd-type/lib/questionCode.js`), in front of the question in the
  PDF export, and by `scripts/update_questionnaire.py` for alignment. All
  three also read the old form, `A.01-_96323997` (reference, timestamp and
  random number).

### Scripts

The administration command runs from `backend/`:
`uv run python -m app.cli --help`. For now it has only `create-admin`.

Scripts also run from `backend/`: `uv run python scripts/<script>.py`.

- `xlsx_to_questionnaire.py`: converts a questionnaire workbook into import
  JSON.
  - Columns are read **by header name**, because two workbooks do not
    necessarily have the same ones. The reference goes into `ref`, and the
    documents to consult into `context_prompt`.
  - The script also adds a `Level:` line to each question, derived from the
    theme by the `MANAGEMENT_COMPANY_THEMES` table at the top of the file.
- `import_questionnaire.py <file.json> <CODE> <name> [owner_user_id]`:
  creates a DD type without going through HTTP. It uses the same parser as
  the API import. Without an owner, the type is shared.
- `update_questionnaire.py <file.json> <CODE> [--apply]`: this is the
  re-import path.
  - It rewrites the texts in place, keeping the ids and the codes. It is
    read-only without `--apply`.
  - It refuses to write if the structure diverges (sections, titles,
    counts, references), or if answers exist, unless `--answered` is given.
  - It fills `context_prompt` when it is empty, but never overwrites it: an
    analyst's input takes precedence over a file.
- `audit_integrity.py [--all]`: lists, read-only, the rows that violate the
  rules of migration `0002`, with their ids, and says what the migration
  does with them: it fixes some and stops at the others, which need a
  decision (exit code 1). Run it before migrating a database that holds
  data.

## Frontend

### Design system

- **Theme**: `data-theme="light|dark"` on `<html>`, set before the first
  paint by an inline script in `index.html`. The preference is stored in
  `DD_THEME` (`light`, `dark` or `system`).
  `shared/lib/theme/ThemeContext.jsx` exposes `mode`, `resolvedTheme`,
  `setMode`, `darkMode` and `toggleDarkMode`.
- **Colors are CSS variables**, declared in `src/app/styles/index.css` (one
  block per theme) and exposed as classes by the `@theme inline` block of
  the same file (Tailwind 4, with no JavaScript configuration file).
  `inline`: each class carries its value, so a class and a variable with the
  same name do not mask each other (`bg-bleu` is the brand's fixed blue,
  `var(--color-bleu)` follows the theme). Opacity works
  (`bg-accent-blue/10`). Custom classes are `@utility` rules.
  - The tokens: `bg-surface`, `bg-surface-bg`, `bg-surface-hover`,
    `text-content(-secondary|-muted|-inverse)`, `border-border`,
    `theme-success|warning|error` (with `-bg` and `-border`),
    `accent-blue|green|deep|gold`, `primary-dark` and `bleu-atlantis`.
  - **Rule: no color from the Tailwind palette (gray, blue…) and no `dark:`
    variant.** A token follows both themes on its own.
- **Custom classes** (`src/app/styles/index.css`, in `@layer components`, so
  utilities can override them): `eyebrow`, `form-input`, `form-surface`,
  `pill-action`, `alert-*`, `live-indicator`, `hairline-gradient`,
  `rail-accent`, `side-gradient(-2)`, `gradient-grey-border-hover`,
  `analysis-link`, `modal-backdrop`, `navbar-spacing` and `bg-auth`.
  - `input-gradient-border` is never combined with a `border-<color>` class,
    because it needs its transparent border.
- **Shared recipes**: `shared/ui/styles.js` (`pageHeader`,
  `sectionHeader`, `panel`, `tableStyles`, `modalStyles`, `field`, `tabs`,
  `menu`, `emptyState`). These are class strings, not components.
- **Statuses**:
  - `shared/lib/status/statusStyles.js` is the **only** mapping between a
    status and its tone (neutral, info, warning, success, error, brand).
    `Badge` plugs into it.
  - The labels are in `shared/lib/status/statusLabels.js`.
  - A session's status is computed in
    `entities/execution/lib/executionStatus.js` (`getSessionStatus`,
    `getSessionProgress`), shared by the dashboard and the session page.
  - `under_review`, `validated` and `finalized` are **terminal** states
    (`FINISHED_STATUSES`).
- **Components**:
  - `Button`: primary (solid midnight blue), secondary (outline), ghost,
    danger and success; with no children, it is an icon button. Do not add
    color classes to it: the order of the stylesheets would then decide which
    one wins. It responds to the press (pointer down, not released) with a
    slight shrink (`motion-safe:active:scale-[0.97]`); so do `pill-action`
    and the clickable tiles.
  - Menus: they grow out of the button that opens them (`origin-top-right
    animate-scale-in`).
  - `LoadingSpinner`: in sizes lg and xl, the logo with a sheen passing
    across it.
  - `Modal`: closes with Escape, the close button or a click outside. It is
    the application's only dialog: there are no hand-made dialogs any more.
  - Confirmations: `const confirm = useConfirm()` (`shared/lib/confirm`),
    then `await confirm({ title, message, confirmLabel, danger })`, which
    returns `true` or `false`. Never `window.confirm`.
  - `Input` (label, icon, help text and error, all linked to the field) and
    `PasswordInput` (the same, with a button to show the password).
  - In `shared/ui/`: `PageHeader`, `StatTile`, `EmptyState`,
    `SearchInput`, `StatusBadge` and `MiniProgressBar`.
- **Slices**: a page assembles widgets and features, and holds at most the
  page state (the tab, the open item). The features: `auth`,
  `session-create`, `session-actions`, `dd-run-control`, `answer-review`,
  `summaries`, `questionnaire-edit`, `dd-type-admin`, `vector-store-manage`,
  `vector-store-assign`, `user-admin` and `theme-toggle`. The widgets:
  `app-layout`, `sessions-overview` (dashboard), `dd-run-card`,
  `session-progress`, `answers-board`, `questionnaire-tree` and
  `vector-store-browser`.
- **Layout**: every page uses `pageLayout.container` (`max-w-7xl`) and the
  `PageHeader` header (breadcrumb, title, actions on the right). Technical
  details (codes, ids, tokens) appear only on hover (`title`).
- **Logo**: `public/logo-white.svg` and the icon `public/icon.svg`.
- **Branding** (`apple-design` skill, 4.4):
  - **system font** (`system-ui`: Segoe UI on Windows), nothing to
    download;
  - **letter-spacing by size**: negative on large text (headings, tile
    figures: `tracking-tight`), slight on small upper-case labels (0.06 to
    0.08 em, never more);
  - **navigation bar** in translucent material (`nav-bg`: surface at 72%,
    blur and saturation); the page scrolls beneath it;
  - **confirmation** only for what cannot be undone (deleting, validating a
    DD type): reverting to a version no longer asks for one, because the old
    version stays in the history.
- **Accessibility** (section 12 of `index.css`, outside the layers): the
  application follows the system settings.
  - **Reduce motion**: nothing moves (dialogs and menus fade, transitions
    are instant, no animated press, no sheen, no pulse).
  - **Reduce transparency**: solid surfaces, no blur.
  - **High contrast**: borders and secondary text are strengthened (tokens
    redefined per theme).
  - A **theme change** is smoothed over a quarter of a second
    (`.theme-changing`, set by `shared/lib/theme` for the duration of the
    change), except with reduced motion.
- ⚠️ Never put `filter`, `transform`, `backdrop-filter` or `isolation` on a
  page container. `Modal` (`fixed z-50`) would then end up under the
  navigation bar.

### Display

- **Never show a value whose source no longer exists, and never cut content
  silently.**
- `AnswerCard` animates `grid-rows-[0fr]→[1fr]` rather than a capped
  `max-h`, which cut long answers. Markdown tables are wrapped in an
  `overflow-x-auto` container (`MARKDOWN_COMPONENTS`).
- The answers page requests `limit=1000` (the server's cap): without it, the
  server returns only 100.
- The tiles of a DD card (`widgets/dd-run-card/ui/RunStatus.jsx`):
  - elapsed time is measured from the answers' timestamps;
  - tokens count only the `is_current` versions;
  - the third tile counts the answers backed by documents.

## Troubleshooting

- **"Internal server error"**: the message is deliberately generic. The full
  traceback is in the uvicorn console.
- **Startup fails with "Invalid configuration"**: the message lists the
  missing or invalid variables. See `.env.template`.
- **A run stays `in_progress` after a restart**: start it again with
  "Resume".
- **A synthesis comes back `incomplete`**: raise the
  `REASONING_MIN_OUTPUT_TOKENS` constant in `engine/openai_client.py`.

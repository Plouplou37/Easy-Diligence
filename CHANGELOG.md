# Changelog

## Unreleased

### New look, step 2: every page

- **Names that say what things are**: "Due diligences" (the dashboard),
  "New due diligence", "Documents" (the vector stores), "Questionnaires"
  (the DD types), "Users". The routes do not change.
- **The session page is a workspace in three columns**: on the left the
  fund (every field the model reads), the documents, the questionnaires
  and the sections; in the centre the questions, filtered by section,
  status or text (or the synthesis); on the right the selected answer, its
  sources and its actions. The answers page merges into it, and its old
  address redirects there.
- **Creating a due diligence is a guided flow in four steps**: fund and
  management company, documents (choose a collection, or create one and
  upload), questionnaires, review with an estimate of time and tokens. A
  panel shows what the AI will receive, as the backend writes it; a new
  fund is created only at the end.
- **Every field the AI reads carries a violet "Sent to the AI" badge**
  (`AiBadge`, shared): the fund's fields, a question's text, its section
  and its "where to look" hint, the questionnaire's name.
- **The dashboard**: figure tiles, one toolbar for search and filters, a
  clean table (cards on a phone), a stuck run said in words.
- **Documents**: two panes, collections on the left and the selected one
  on the right, with a state per file. **Questionnaires**: a table with the
  counts of sections and questions, an import in clear steps, read-only
  rows for questionnaires one cannot edit. **Users**, **Profile**, **Sign
  in**, **Reset password** and **Not found** restyled.

### New look, step 1: palette, typeface, shared components

- A new palette, in the dark and light themes: a neutral ground, one blue
  for the actions, violet kept for what concerns the AI (`theme-ai` tokens,
  for the screens to come). The blue-to-green gradients are gone.
- The Inter typeface, served by the application itself
  (`@fontsource-variable/inter`): no request to a font service.
- Shared components restyled, so every screen changes at once: buttons
  (taller, one blue primary), cards, fields, tables (tinted header, rules
  between rows), tabs, badges, figure tiles, menus, notifications.
- The bar at the top spans the width, solid, its links on pills; the
  account button shows the user's initials. The sign-in screens are one
  card on the plain background.

### Run card, error messages, PDF only

- **Run time without the pauses.** The card counted from the first answer,
  pauses included. A run now keeps the time it spends running
  (`dd_executions.run_seconds`, `running_since`, migration `0004`); the
  existing runs get an estimate from their answers, a gap of more than five
  minutes counting as a pause.
- **A paused or failed run** shows "Review Answers" and "Synthesis" next to
  "Resume": the answers already written can be read and summed up without
  resuming the rest.
- **Why a run stopped**: the card shows the message alone, without the
  internal error code in front ("api_error: …"), and the latest failure still
  current, not an older one since retried. A refused key is named as such.
- **A vector store OpenAI could not describe** says why ("OpenAI refused the
  server's API key…", "OpenAI could not be reached…"), instead of always
  "could not be reached". Its file list says it could not be listed, instead
  of "No files in this vector store", and the run card shows "files unknown"
  instead of "0 files".
- A regeneration that fails gives a message without "Use Resume", which only
  applies to a run.
- **Export**: the CSV export of the answers is removed; the PDF report is the
  only export.

### Answering engine: the earlier answers instead of a conversation chain

- The questions of a run are no longer chained into one OpenAI conversation
  (`previous_response_id`). Each question now carries the text of the answers
  already written for the earlier questions, in the questionnaire's order,
  within a budget of 30,000 characters (the closest questions first). A
  regenerated answer gets the same context.
- Why: measured on a run, a chained question cost 75,000 to 96,000 input
  tokens, against about 6,400 alone, because the chain sent every earlier
  search result again. The chain also followed the question number alone,
  which starts again in every section: from the second section on, each
  question continued the wrong one (B.02 continued A.01).
- The request sent to OpenAI changes on purpose:
  `tests/data/question_request.json` is rewritten.

### Vector store files

- When OpenAI lists a file but does not give its details, the row says so:
  the name is greyed out, with a tooltip, and the size and date show "—"
  instead of "NaN undefined" and "Invalid Date".
- An incomplete answer from OpenAI (a file without details, a store it could
  not describe) is no longer cached: the next display asks OpenAI again,
  instead of showing the same gap for five minutes.

### Makefile

- A `Makefile` at the root gathers the everyday commands; `make` alone lists
  them. With Docker: `up`, `down`, `ps`, `logs`, `build`, `build-backend` and
  `build-frontend` (rebuild one image and restart its container), `admin`. By
  hand: `install`, `dev-backend`, `dev-frontend`, `test`, `lint`, `format`,
  `check` (what CI checks, from lint to the frontend build), `migrate`,
  `migration`, `schema`.
- Its commands run the same under sh (Linux, macOS, Git Bash) and under cmd
  (make on Windows).

### Everything in English

- The documentation is in English: `README.md`, `docs/ARCHITECTURE.md`,
  `CLAUDE.md`, `VERSION.md`, the `infra/` READMEs and this changelog, as well
  as the comments of `.env.template` and the messages of the scripts in
  `backend/scripts/`.
- The syntheses are written in English. The instructions given to the model
  for the section summaries and the synthesis are in English, and so are the
  analyst's instruction and the web source added to a regenerated answer. In
  the PDF report, the synthesis heading reads "Synthesis".

### OpenAI errors explained to the user

- An OpenAI error outside a run (creating a vector store, uploading a
  document to it, listing its files…) showed "Internal server error". It now
  gives a message that says what happened and what to do: OpenAI
  unreachable, rate limit reached, key refused (to be checked by an
  administrator). OpenAI's text stays in the logs.

### Documentation fixes

- Two links still pointed to the old `proxy/nginx.conf` (README and
  `frontend/nginx.conf`): they now name its replacement,
  `proxy/default.conf.template`.

### Deployment on Azure or AWS (Terraform)

- **`infra/azure/`** deploys the application on Azure, as managed services:
  Container Apps for the three containers (only the proxy is public, over
  HTTPS), a private PostgreSQL Flexible Server, Key Vault, Container
  Registry, managed identity, virtual network, Log Analytics.
- **`infra/aws/`** does the same on AWS: ECS Fargate in private subnets, an
  HTTPS load balancer (with a domain and its certificate), RDS PostgreSQL,
  Secrets Manager, ECR, Cloud Map, CloudWatch.
- Each folder has its README: the commands in order, from creating the state
  storage to the first administrator, then updates. The OpenAI key is added
  by hand and never goes through Terraform. Nothing is deployed without
  `terraform apply`.
- CI checks the Terraform code of both folders on every pull request.
- **The proxy** becomes a template rendered at startup, so that it works in
  Docker as well as in both clouds:
  - **it resolves the services on every request.** Before, it kept their
    address from startup: after an update that recreated the backend, it
    answered with a 502 error until it was itself restarted;
  - **it reads the client's address behind a cloud's entry point**, without
    a client being able to choose it;
  - **it has its own health check** (`/healthz`).

### README and cleanup

- The README starts with a step-by-step getting-started guide: what you
  need, the configuration (with secret generation on Linux, macOS and
  Windows), startup, the first administrator, a first due diligence and
  common problems.
- The scripts no longer add `backend/` to Python's path before importing the
  application: uv installs it as a package. Their 9 `# noqa: E402` markers
  are gone, along with the matching ruff exception.
- `.git-blame-ignore-revs` points to the current formatting commits (backend
  and frontend). It named a commit that no longer exists.

### Docker Compose

- **The application runs with Docker**: `cp .env.template .env`, fill in
  three values, then `docker compose up -d --build`. Python, Node and
  PostgreSQL no longer need to be installed.
- Four services: an nginx **proxy**, the only entry point (port 8080), in
  front of the **frontend** (static files), the **backend** (which applies
  the migrations at every startup) and **PostgreSQL 17**. The database and
  the backend cannot be reached from the machine.
- The proxy holds the traffic rules: 110 MB per upload, 10 minutes for calls
  that wait for OpenAI, security headers. The client address it passes on
  cannot be chosen by the client: the per-IP-address login limits hold.
- The README describes the first startup, creating the first administrator,
  the logs, updating, backing up and restoring the database, accessing the
  database from the machine, and the PDF banner.
- Image versions are pinned (`VERSION.md`).
- CI starts the whole application on every pull request and uses it through
  the proxy, up to creating an administrator and logging in.

### Answering engine reworked

- **A failed question shows a message written for the user**, instead of
  OpenAI's raw text. For example: "OpenAI rate limit reached. Use Resume in
  a few minutes." The details stay in the server logs.
- **A question costs at most 3 calls to OpenAI**, against 9 before: the SDK
  no longer retries on its own, only the engine does. It waits for the delay
  OpenAI asks for when a rate limit is hit, and does not retry what a new
  attempt would not fix (request refused, key refused). `retry_count`
  counts the actual retries.
- **Errors are classified by their type**, no longer by looking for words in
  their text. A message containing "invalid" no longer stops the retries,
  and a context overflow is no longer retried for nothing.
- **A refused key or quota stops the run at the first question**, instead of
  failing on each one.
- **A question is written in a single transaction**: the raw response, its
  messages, the old answer set aside, the new one and its history. A failure
  halfway no longer leaves a question without a current answer.
- **Start and resume go through the same loop**, and the final status is
  decided in one place. A fatal error always ends the run as `failed` (a
  start set it back to `not_started`). A pause clicked right after "Start"
  is no longer overwritten when the run starts.
- **A regeneration that fails on OpenAI's side** answers with a readable
  message (502) instead of a 500 error.
- **Syntheses**: the module is synchronous (the routes launched coroutines
  that called the database synchronously). Only the section summary calls
  run in parallel, in threads, and the database stays in the request's
  thread.
- A vector store's expiry date carries its time zone (UTC).
- The engine is checked by mypy, and its logging calls pass their values as
  arguments. A test pins the parameters sent to OpenAI for a question.

### Dead columns and copies (migration 0003)

- **A session can no longer be deleted during a run**, nor once it is
  finished. The guard existed, but it read a session status that stayed at
  "created" forever: it never fired, and the background task kept writing to
  deleted rows. A session's status is now read from its runs, on the server
  as in the interface. If the server refuses, its message is shown.
- The `dd_sessions.status` column is gone, along with the `status` field of
  the `/session/…` responses and the `status` filter of the session list.
- A session's DD types move to a link table (`session_dd_types`). The API
  returns `dd_types: [{id, code, name}]`, in the order chosen at creation,
  instead of `dd_types_json`. A renamed type shows under its new name, and a
  type that a session chose can no longer be deleted (409).
- Deleting a question or a section that has answers returns a 409, instead
  of a 500 error on the foreign key.
- The confidence score is gone: the column, its field in the API and
  `average_confidence` in the review page statistics. It measured nothing (a
  fixed value of 0.8, then nothing at all) and always averaged 0.
- `is_verified` is gone from accounts and `validator_id` from runs: nothing
  filled them.

### CI: tests on PostgreSQL too

- CI runs the whole test suite again on its throwaway PostgreSQL, with a
  schema created by the migrations, as in production. Until now the tests
  stayed on SQLite, which checks neither partial indexes, nor time zones,
  nor JSONB. Nothing changes locally.
- PostgreSQL-specific tests check that the unique indexes are indeed
  partial, that the `CHECK` constraints refuse an unknown status and that
  dates carry their time zone.
- A failing test shows up as an annotation on the pull request.
- Companies, syntheses and vector store assignments are listed in a stable
  order, and so are answers created at the same instant: PostgreSQL
  guarantees no order without `ORDER BY`.

### Database integrity (migration 0002)

- **The database itself guarantees what the code assumed**: a single run per
  session and DD type, at most one current answer per question, one
  synthesis per section and a single global synthesis, one vector store
  assignment per scope (and the assigned DD type exists), unique section and
  question codes. Until now, two clicks or two simultaneous requests could
  create duplicates.
- **Two clicks no longer start two runs.** "Resume" on a run already in
  progress started it a second time in parallel; it is now refused
  ("already in progress"). Start, pause and resume change the status in a
  single conditional step.
- A long run that keeps answering is no longer taken for "stuck" after 10
  minutes: it is only stuck if no answer has been written for 10 minutes.
  "Resume" resumes a stuck run, only once.
- A section or question code already taken returns a **409** (instead of a
  400), even when another request took it at the same moment.
- No boolean, status, counter or creation date can be NULL any more, and the
  database sets the default values itself. Each status is checked by a
  `CHECK` constraint, and so is a user's role.
- Answer statuses are stored by their value, in lower case (`needs_review`),
  like the others. The API does not change: it already returned the values.
- Sending `null` for a DD type's `is_active` or `order_index` leaves the
  field as it is, instead of clearing it.
- **Before migrating a database that holds data**:
  `uv run python scripts/audit_integrity.py` (from `backend/`, read-only)
  lists the rows at fault. The migration fixes duplicates and NULLs. It
  stops, without changing anything, at what needs a decision: duplicate
  runs, answers without a run or without a question, duplicate codes,
  unknown status or role.

### CI: migrations checked on PostgreSQL

- CI runs the migrations on a throwaway PostgreSQL 17: `alembic upgrade
  head`, `alembic check` (the migrations match the models), a full downgrade
  then upgrade again, and a comparison of `db/schema.sql` with a regenerated
  script. Until now, nothing ran them: the tests create their tables on
  SQLite.

### Simplifications

- **No more open registration.** The `/register` page and the
  `POST /auth/register` route are gone: anyone could create an account on an
  internal tool. An administrator now creates accounts from User Management
  ("Create user"): name, username, e-mail, role, and a temporary password
  that they pass on and that the user changes in their profile
  (`POST /admin/users`).
- The "Questions" menu entry is gone: a questionnaire opens from its DD type
  ("Questions" button), and the "DD Types" entry stays highlighted on its
  page.
- The "User Analytics" table of the dashboard is gone.
- The old `/dashboard`, `/sessions` and `/answers` addresses no longer
  redirect: they lead to the "not found" page.

### Interface all in English

- What was still in French moves to English, like the rest of the
  interface: the synthesis tab and its messages, the answer regeneration
  dialog, the question and section editors, the "Answers" and "Synthesis"
  tabs.
- The reason recorded on a regenerated version is in English ("Regenerated
  by the AI…"); versions already recorded keep theirs.
- Kept in French, on purpose, because they are content and not interface:
  the instructions given to the model (and so the language of the
  syntheses) and the PDF report.
- The labels of the regeneration dialog are linked to their fields.

### Frontend: apple-design branding

- The font is the system's (Segoe UI on Windows): Roboto is no longer
  downloaded with the application.
- Letter spacing follows the size: headings and large figures tighter,
  upper-case labels much less spaced (0.06 to 0.08 em instead of 0.1 to
  0.22 em).
- Buttons, badges and clickable tiles respond as soon as they are pressed.
  Menus (account, export) grow out of the button that opens them.
- The navigation bar is a translucent, blurred material that the page
  scrolls under; it carries the name "Easy Diligence" (instead of
  "DD Automation").
- The application follows the system's accessibility settings: reduced
  motion (nothing moves any more), reduced transparency (solid surfaces),
  high contrast (stronger borders and secondary text). A theme change fades
  in instead of switching all at once.
- Going back to a version of an answer no longer asks for confirmation:
  nothing is lost, the old version stays in the history.
- The account menu shows the user's name: it read fields (`first_name`,
  `last_name`) that an account does not have, and stayed empty.
- The Tailwind configuration moves into the CSS (`@theme`):
  `tailwind.config.js` is gone. Checked: the 36 screenshots were identical
  before the branding changed anything.

### Frontend: Tailwind 4

- Tailwind 3 → 4, with the official migration tool. The pages stayed
  pixel-identical: 36 screenshots compared before and after, in light and
  dark themes.
- Only one visible difference, intended: the footer of the dialogs (creating
  a DD type, a question, a section, a vector store) finally touches the
  bottom of the dialog. Tailwind 3 canceled its margin and left a white band
  under the buttons.
- `npm audit`: 0 vulnerabilities, build tools included. The 2 alerts came
  from `@tailwindcss/typography`, which pins an old version of
  `postcss-selector-parser`; an `overrides` entry in `package.json`, limited
  to that package, replaces it with 6.1.6, which is fixed (same major
  version).
- `autoprefixer` is no longer needed and is gone.

### Forgotten password, vanished vector stores, server no longer blocked

- The link in the "forgot password" e-mail leads to a page that exists
  (`/reset-password`): you choose your new password there, then log in with
  it. An expired or already used link says so, and explains how to ask for a
  new one. The link used to lead to a 404 page.
- Asking for a link gets an answer just as fast whether the address exists
  or not: the e-mail goes out after the response, and the response time no
  longer gives accounts away.
- A vector store that expired or was deleted at OpenAI is marked "Expired"
  or "Gone", without the "0 files" that made it look like an empty store.
  Its page explains that its documents are lost and no longer tries to list
  its files (which ended in an error). It is no longer offered for
  assignment, and the card of a DD type that uses it flags it.
- The "Refresh" button of the vector stores says that it removes the stores
  that vanished at OpenAI, and how many it removed.
- The server no longer blocks while a synthesis batch is being tracked
  (called every 15 seconds) nor during a synthesis generation: these routes
  called OpenAI from the application's event loop, and every other request
  waited.

### Frontend: pages split up (2/2)

- User management paginates and searches on the server. It loaded the first
  100 accounts and searched among them: the 101st never showed up. The
  server search also covers the company.
- A single kind of dialog, `Modal`: the six hand-made dialogs (forgot
  password, password change, user details and user deletion, DD type,
  question) now all close with Esc. Deleting a user goes through the shared
  confirmation.
- The registration and password change forms state the password rule up
  front, and flag each faulty field next to it. The profile no longer sends
  the role (the server ignored it).
- Files can be dropped into the upload dialog of a vector store, as it
  announced. Failed files stay listed, and the dialog stays open to resend
  or remove them; it also announced a 10 MB limit that the server does not
  enforce (100 MB by default).
- Removed: the "Remember me" checkbox and the "Terms and Conditions"
  checkbox (empty link), which had no effect, and the "Edit user" button,
  which showed "coming soon".
- Choosing a DD type category no longer files "Credit" or "Equity" among the
  technical types (the word "it" was searched for in the whole name).
- Dashboard, session creation, DD types, users, profile, login, registration
  and vector stores are split into widgets and features; no frontend file
  exceeds 250 lines (nine exceeded 400 lines).
- `npm run lint` passes without a single warning, and CI runs it.

### Example questionnaire

- The example questionnaire is `examples/example_questionnaire.json` (code
  `EXAMPLE`): 18 questions about a fund, in 6 sections (fund identity, team,
  strategy, risks, operations, fees and sustainability). Each section has a
  description and each question a "where to look" hint. A test checks that
  it imports.
- A DD type whose name matches no icon keyword gets the default icon.

### Frontend: pages split up (1/2)

- Confirmations open in an application dialog, no longer in the browser's
  `confirm()`. The message names what is about to disappear; Esc, the close
  button or a click outside count as "Cancel".
- The answers page loads all the answers of a DD type. It only received 100
  of them (the server's default page size): beyond that, the rest were
  missing without any message.
- Choosing a section in the filters no longer reloads the page: the request
  sent a parameter that the server ignored. After a regeneration or a return
  to a version, the open sections and answers stay open.
- The CSV export keeps its accents in Excel (UTF-8 byte order mark at the
  start of the file).
- The "Sources" button of an answer no longer counts sources that have
  nothing to show (file search without a file name, web search without a
  link), and the editor no longer shows them as empty rows.
- The session page, the DD type card, the answers page and the synthesis are
  split into widgets (`dd-run-card`, `session-progress`, `answers-board`) and
  features (`dd-run-control`, `vector-store-assign`, `session-actions`,
  `answer-review`, `summaries`). The session page goes from 648 to 198
  lines.

### Frontend: layers

- The code is organized in Feature-Sliced Design (`app`, `pages`, `widgets`,
  `features`, `entities`, `shared`), and the lint refuses an import that
  goes up the layers or from one slice to its neighbor.
- A single layout for all pages, a 404 page, and `/login` sends you to the
  dashboard when you are already logged in.
- An expired login session sends you to the login page without reloading
  the application.
- DD types are loaded once and shared: the session page asked for their full
  structure once per card.

### Frontend: foundation

- The frontend calls the API with a relative path, `/api`, whatever the
  address it is served from. In development, the Vite server forwards
  these calls to the backend (`VITE_API_PROXY`, `http://localhost:8000` by
  default); `VITE_API_URL` is gone.
- Vite 8, react-router 7 and ESLint 9; no known vulnerability left in the
  code shipped to the browser (18 before, 14 of them "high").
- Authentication goes through the shared HTTP client. A wrong password shows
  the API's message instead of reloading the page.
- Removed: editing the "attributes" of a vector store file (the endpoint did
  not exist), dead files and API calls, and unused dependencies
  (`rehype-mermaid`, `react-dropzone`, `tailwind-scrollbar`).
- The `@/` alias points to `frontend/src`.

### Database

- PostgreSQL 17 replaces MySQL, through psycopg 3. The connection is set
  with `POSTGRES_*` or `DATABASE_URL`.
- The models move to SQLModel.
- Alembic manages the schema: the initial migration creates the whole
  database, and `db/schema.sql` gives its complete SQL script. The old SQL
  fixes applied by hand are removed, and the application no longer creates
  its tables at startup.
- Transactions are real: a `rollback()` now really cancels.
- Foreign keys are indexed, and statuses are stored as text with a check
  constraint.
- E-mail addresses are stored and compared in lower case.
- Data from the old MySQL database is not carried over.

### Tooling

- The frontend code is formatted by Prettier (`npm run format`), and CI
  checks it (`npm run format:check`). Formatting changed nothing in the code
  shipped to the browser: the build is identical, byte for byte.
- The backend project is called `easy-diligence`, at version 0.1.0, and
  moves to Python 3.12.
- The development tools are in the `dev` group of `pyproject.toml`:
  `uv sync` installs them, `uv sync --no-dev` leaves them out. The unused
  extras (monitoring, documentation) and the dependencies with no use
  (celery, aiofiles, python-dateutil…) are removed.
- Ruff checks and formats the code (black is removed); mypy checks the
  types, in lenient mode to begin with.
- pytest 9 and pytest-asyncio 1.x.
- `.pre-commit-config.yaml` and GitHub Actions continuous integration.
- `.gitattributes` sets the line endings (LF).
- `pip-audit` no longer finds any known vulnerability, development tools
  included.

### Tests

- The suite is rewritten: each test has its own in-memory SQLite database,
  and `conftest.py` provides the users, the seed data and fake OpenAI
  clients. Empty, duplicate or no longer useful tests are removed.
- New tests: access isolation between users, companies, vector stores,
  answering engine (start, pause, resume, failed question), models, token
  security, login.
- CI runs the whole suite.

### Fixes

- The Excel export crashed for any answer that had sources.
- Editing a vector store always failed.
- After a vector store was edited, the list showed the old version for five
  minutes (cache).
- The administration page could change neither the role nor the status of a
  user (wrong HTTP method).
- The export included every version of an answer: a regenerated question
  appeared twice in the report. It now keeps only the current version.
- An administrator or the person assigned to a session could not manage its
  vector stores.
- A new session could include another user's private DD types. Another
  user's private DD type can no longer be started.

- Deleting an account cleared the creator of its sessions and companies: its
  companies became visible to everyone. An account that owns data can no
  longer be deleted; it is deactivated instead.
- The search on the administration page only searched the page on display,
  with a wrong total.
- A section added after a first section took the same position as it.
- Sections and questions come in questionnaire order.

### Export

- A single server-side export: the PDF report. The Excel export is removed;
  the CSV export of the review page stays.
- The report's colors and its footer notice are set in the configuration
  (`PDF_PRIMARY_COLOR`, `PDF_TEXT_COLOR`, `PDF_RULE_COLOR`,
  `PDF_FOOTER_NOTICE`).
- The export code is split: `exports/pdf.py`, `markdown.py`, `sources.py`.

### Models

- `schemas/` is gone: each file in `models/` holds its table and what the
  API reads and returns for it. Fields and their limits are written only
  once, and the API now refuses what the database would refuse (length,
  negative position). The database schema does not change.
- The expiry duration chosen when a vector store is created is honored (it
  was always 30 days).

### Question codes

- Sections are lettered by their position (A, B…) and questions numbered
  within their section (A.01, A.02…), on import as on creation on screen.
  The file's reference, when it gives one, stays the code. Old codes
  (`A.01-_96323997`) are still read.
- Filtering answers by section also requires the DD type, and the export
  follows questionnaire order.

### Services

- Logic and database access move into `services/`, for every route. Routes
  now only read the request, call a service and answer.
- Routes are plain functions: an asynchronous route that called the
  database or OpenAI blocked the whole server during the call.
- The session and the DD type read from the URL go through two shared
  dependencies, which check permissions.
- Reading the list of vector stores no longer deletes anything: a store that
  vanished at OpenAI appears as `expired` or `missing`, and the Refresh
  button removes it.
- Removed, as duplicates: six variants of an answer's history
  (`with-history`, `versions/{v}`, `original`, `history/{v}/raw`,
  `by-execution`, `POST validate`) and `/dd-types/code/{code}`.

### Cleanup

- Removed, because no screen called them and several crashed: the
  `/executions` and `/documents` endpoints, search in a vector store and
  `/company/auth-test`, with their schemas.
- Also removed: the methods of the OpenAI client and of the utilities that
  had no caller, and cache invalidations that targeted no cached data.
- Pydantic v2 code everywhere (`ConfigDict`, `model_validate`,
  `model_dump`), and `datetime.utcnow()` replaced.
- The application's logging is configured (`LOG_LEVEL`): under uvicorn, its
  info messages were lost.

### Backend structure

Files are organized into `api/routes`, `core`, `engine`, `services` and
`exports`, with no change in logic.

### Security

- Registration can no longer choose its role: a new account is always an
  analyst. The first administrator is created with
  `python -m app.cli create-admin`.
- `DATABASE_URL`, `OPENAI_API_KEY` and `JWT_SECRET_KEY` are required, and
  the application refuses to start without them.
- Tokens are stored hashed and made unique, the refresh token moves into the
  request body, and the password reset token can only be used once.
- Login is limited after repeated failures.
- The size and type of uploaded files are checked.
- An unexpected error returns a generic message; its trace goes to the
  logs.
- `/docs` is closed by default (`DOCS_ENABLED`).
- The two unused WebSockets are removed.
- PyJWT and bcrypt replace python-jose and passlib; FastAPI, Starlette,
  python-multipart, jinja2, cryptography and the dependencies they pull in
  are upgraded.

## 0.1.0 — 18/11/2026

First version of Easy Diligence.

- The documentation is rewritten: `README.md`, `docs/ARCHITECTURE.md` and
  `VERSION.md`. Outdated reviews and analyses are removed, along with Docker
  leftovers and one-off measurement scripts.
- All the configuration is listed and commented in `.env.template`.
  `DATABASE_URL` becomes required, and an empty `JWT_SECRET_KEY` is refused.
- The application comes with a neutral logo, and the PDF report banner
  becomes optional (`BRAND_BANNER_PATH`).
- An example questionnaire is provided in `examples/`.

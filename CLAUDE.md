# CLAUDE.md

Guide court pour un agent qui travaille sur Easy Diligence. Le reste est dans :
- [`README.md`](README.md) : installer, lancer, tester ;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) : la conception (moteur,
  cloisonnement, synthèses, export, design system) ;
- [`VERSION.md`](VERSION.md) : la version de l'application et des outils ;
- [`CHANGELOG.md`](CHANGELOG.md) : le journal des changements, à compléter à
  chaque changement visible.

## Repères

- Backend FastAPI dans `backend/app/` :
  - `api/` : `router.py` (assemblage), `routes/` (un router par ressource),
    `deps.py` (dépendances communes) ;
  - `core/` : le transverse (config, database, sécurité, cache, e-mail) ;
  - `engine/` : le moteur de réponses (`openai_client.py`, `processor.py`,
    `summarizer.py`, `errors.py` pour le classement des erreurs, `answers.py`
    pour la création d'une réponse). Les prompts et les paramètres envoyés à
    OpenAI sont figés par `tests/test_question_request.py` : un changement
    voulu réécrit `tests/data/question_request.json` ;
  - `services/` : la logique métier et les accès à la base (sessions, réponses,
    traitement, vector stores, droits, authentification, import). Une route lit
    la requête, appelle un service et répond ;
  - `exports/` : le rapport PDF (`pdf.py`), son rendu markdown et ses sources ;
  - `models/` : un fichier par table (SQLModel), avec ce que l'API en lit et en
    renvoie (création, mise à jour, réponse). Les champs communs sont dans une
    classe de base ;
  - `alembic/` : les migrations de la base.
- Frontend React dans `frontend/src/`, en Feature-Sliced Design : `app` >
  `pages` > `widgets` > `features` > `entities` > `shared`. Une couche n'importe
  que les couches du dessous, et une tranche n'importe pas une autre tranche de
  sa couche : `npm run lint` le vérifie (`eslint-plugin-boundaries`). D'une
  tranche à l'autre, on passe par son `index.js` et par l'alias `@/`.
- La configuration est lue par `backend/app/core/config.py`. Chaque variable est
  décrite dans `.env.template` : une variable ajoutée au code doit l'être aussi
  dans ce fichier.

## Règles

- **Python avec uv uniquement** : `uv sync`, `uv run …`, jamais pip.
- **Aucune donnée réelle dans le dépôt** : pas d'IP, de chemin réseau, de nom de
  personne, de client ou de fonds réel, pas de secret. Les exemples et les tests
  utilisent des noms fictifs (« Example Asia Fund »). Les fichiers de charte
  restent dans `branding/`, et les vrais questionnaires dans `questionnaires/` :
  les deux dossiers sont ignorés par git.
- **Ne jamais lancer de test contre une vraie base.** Les réglages de test de
  `pyproject.toml` (pytest-env) imposent une base SQLite en mémoire et une
  fausse clé OpenAI : ne pas les retirer. Seule exception : la CI relance les
  tests sur son PostgreSQL jetable, via `TEST_POSTGRES_URL`. Cette variable
  n'est lue que par `tests/conftest.py`, qui refuse tout hôte autre que la
  machine elle-même. Ne jamais la définir ailleurs que dans la CI.
- **Schéma de la base** : toute modification passe par le modèle
  (`app/models/`), puis par une migration Alembic générée avec
  `uv run alembic revision --autogenerate`, **relue**, puis par la régénération
  de `db/schema.sql`. Ne jamais modifier une migration déjà publiée, en ajouter
  une nouvelle. Ne jamais remettre de `create_all` dans l'application.
- **Erreurs** : ne jamais renvoyer `str(e)` au client. Pour une erreur attendue,
  lever une exception de `core/exceptions.py`, dont le message est écrit pour
  l'utilisateur. Pour le reste, `logger.exception(...)` puis un message
  générique.
- **Routes en `def` simple** : FastAPI les exécute dans un pool de threads.
  Une `async def` qui appelle la base ou OpenAI, deux bibliothèques
  synchrones, bloque tout le serveur. `async def` est réservé aux routes qui
  lisent un fichier envoyé (`read_upload`) ; elles passent ensuite la suite au
  pool avec `run_in_threadpool`.
- **Une session ou un type de DD lus dans l'URL** passent par les dépendances
  `get_accessible_session` et `get_visible_dd_type` de `api/deps.py`, qui
  vérifient les droits.
- **Dans un modèle, `Field` est celui de SQLModel, qui ignore `pattern` (et
  `regex`)** sans erreur. Pour un motif, utiliser `pydantic.Field` (voir
  `models/user.py`). `max_length`, `ge` et `le` sont bien appliqués.
- **Authentification** : tout endpoint qui demande un utilisateur passe par
  `api/deps.py` (`get_current_active_user`, `get_current_admin_user`). Ne pas
  décoder un jeton ailleurs.
- **Fichiers envoyés** : les lire avec `api/uploads.read_upload`, qui applique
  la taille et les extensions autorisées.
- **Frontend** : uniquement des tokens de couleur du thème, ni palette Tailwind,
  ni variante `dark:`. Ajouter une classe de couleur à `Button` est interdit.
- **Un champ envoyé au modèle doit être visible dans l'interface.**
- Ne pas valider un type de DD par commodité : la validation est irréversible.
- Commits : messages en français.

## Vérifier un changement

```bash
# backend/
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy app
# frontend/
npm run build
npm run lint
npm run format:check   # npm run format pour corriger
```

- La CI lance aussi `pytest` une seconde fois, sur PostgreSQL, avec les tests
  marqués `postgres` (sautés en local). Un échec y apparaît en annotation de
  la pull request.
- Ruff et mypy passent sur tout le backend, moteur compris. **Ne pas ajouter de
  `# noqa`**, ni de `# type: ignore`, ni de section `ignore_errors` à mypy
  (`pyproject.toml`). Les journaux passent leurs valeurs en arguments
  (`logger.info("… %s", x)`), jamais en f-string : ruff le vérifie (`G004`).
- `npm run lint` passe sans aucun avertissement (`--max-warnings 0`), et la CI
  le vérifie. Pas de `eslint-disable` : corriger le code.
- **Frontend** : une confirmation passe par `useConfirm()`, une fenêtre par
  `Modal` (jamais `window.confirm` ni une fenêtre faite à la main), un champ par
  `Input` ou `PasswordInput` (`shared/ui`).

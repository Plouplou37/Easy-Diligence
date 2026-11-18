# Journal des changements

## Non publié

### Base de données

- PostgreSQL 17 remplace MySQL, via psycopg 3. La connexion se configure par
  `POSTGRES_*` ou `DATABASE_URL`.
- Les modèles passent en SQLModel.
- Alembic gère le schéma : la migration initiale crée toute la base, et
  `db/schema.sql` en donne le script SQL complet. Les anciens correctifs SQL
  appliqués à la main sont supprimés, et l'application ne crée plus ses tables
  au démarrage.
- Les transactions sont réelles : un `rollback()` annule désormais vraiment.
- Les clés étrangères sont indexées, et les statuts stockés en texte avec une
  contrainte de contrôle.
- Les adresses e-mail sont enregistrées et comparées en minuscules.
- Il n'y a pas de reprise des données de l'ancienne base MySQL.

### Outillage

- Le projet backend s'appelle `easy-diligence`, en version 0.1.0, et passe à
  Python 3.12.
- Les outils de développement sont dans le groupe `dev` de `pyproject.toml` :
  `uv sync` les installe, `uv sync --no-dev` les laisse de côté. Les extras
  inutilisés (monitoring, documentation) et les dépendances sans usage (celery,
  aiofiles, python-dateutil…) sont retirés.
- Ruff vérifie et formate le code (black est retiré) ; mypy vérifie les types,
  en mode permissif pour commencer.
- pytest 9 et pytest-asyncio 1.x.
- `.pre-commit-config.yaml` et une intégration continue GitHub Actions.
- `.gitattributes` fixe les fins de ligne (LF).
- `pip-audit` ne trouve plus aucune faille connue, outils de développement
  compris.

### Tests

- La suite est réécrite : chaque test a sa propre base SQLite en mémoire, et
  `conftest.py` fournit les utilisateurs, les données de départ et de faux
  clients OpenAI. Les tests vides, en double ou devenus inutiles sont supprimés.
- Nouveaux tests : cloisonnement entre utilisateurs, sociétés, vector stores,
  moteur de réponses (démarrage, pause, reprise, question en échec), modèles,
  sécurité des jetons, connexion.
- La CI lance toute la suite.

### Corrections

- L'export Excel plantait pour toute réponse qui avait des sources.
- La modification d'un vector store échouait toujours.

### Structure du backend

Les fichiers sont rangés en `api/routes`, `core`, `engine`, `services` et
`exports`, sans changement de logique.

### Sécurité

- L'inscription ne peut plus choisir son rôle : un nouveau compte est toujours
  analyste. Le premier administrateur se crée avec
  `python -m app.cli create-admin`.
- `DATABASE_URL`, `OPENAI_API_KEY` et `JWT_SECRET_KEY` sont obligatoires, et
  l'application refuse de démarrer sans eux.
- Les jetons sont stockés hachés et rendus uniques, le jeton de rafraîchissement
  passe dans le corps de la requête, et le jeton de réinitialisation du mot de
  passe ne sert qu'une fois.
- La connexion est limitée après des échecs répétés.
- La taille et le type des fichiers envoyés sont vérifiés.
- Une erreur imprévue renvoie un message générique ; sa trace part dans les
  journaux.
- `/docs` est fermé par défaut (`DOCS_ENABLED`).
- Les deux WebSockets inutilisés sont supprimés.
- PyJWT et bcrypt remplacent python-jose et passlib ; FastAPI, Starlette,
  python-multipart, jinja2, cryptography et les dépendances qu'elles entraînent
  sont montés.

## 0.1.0 — 18/11/2026

Premier commit d'Easy-Diligence, sur un historique neuf.

- La documentation est réécrite : `README.md`, `docs/ARCHITECTURE.md` et
  `VERSION.md`. Les revues et analyses périmées sont supprimées, ainsi que les
  restes Docker et les scripts de mesure ponctuels.
- Toute la configuration est listée et commentée dans `.env.template`.
  `DATABASE_URL` devient obligatoire, et une `JWT_SECRET_KEY` vide est refusée.
- Les éléments de charte sont retirés : un logo neutre les remplace, et la
  bannière du rapport PDF devient facultative (`BRAND_BANNER_PATH`).
- Un questionnaire d'exemple est fourni dans `examples/`.

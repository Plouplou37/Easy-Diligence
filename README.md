# Easy Diligence

Application web qui automatise la due diligence de fonds d'investissement et de
leur société de gestion.

On décrit un questionnaire de due diligence (un **type de DD**), puis on ouvre
une **session** sur un fonds et on y rattache ses documents (prospectus,
présentations, DDQ…). Le moteur répond alors aux questions une à une avec l'API
OpenAI : il cherche dans les documents de la session et sur le web, et cite ses
sources. Les analystes relisent, corrigent ou régénèrent les réponses, font
rédiger une synthèse par type de DD, puis exportent un rapport PDF.

## Fonctionnalités

- **Questionnaires** : création et édition dans l'interface, ou import d'un
  fichier JSON (voir [`examples/`](examples/)). Chaque question peut porter une
  consigne « où chercher » transmise au modèle.
- **Moteur de réponses** : un appel par question avec deux outils, la recherche
  dans les documents (vector stores OpenAI) et la recherche web. Le traitement
  peut être mis en pause et repris.
- **Revue** : réponses versionnées, éditables, régénérables une à une, avec un
  statut de relecture.
- **Synthèses** : un résumé par section, puis une synthèse par type de DD.
  Elles se rédigent en direct ou en différé via la Batch API d'OpenAI, deux fois
  moins chère.
- **Export** : un rapport PDF à deux niveaux (la synthèse en corps de texte, le
  détail des questions et réponses en annexe), et un export CSV des réponses
  depuis la page de revue.
- **Comptes et cloisonnement** : rôles `admin` et `analyst`. Chacun ne voit que
  ses propres données, et l'administrateur voit tout.

## Démarrage avec Docker

Il ne faut que Docker (avec Compose v2) et une clé d'API OpenAI.

```
navigateur ──► proxy ──/api──► backend ──► db
                 └──── / ────► frontend
```

Quatre services (`docker-compose.yml`) :
- **`proxy`** : nginx, le seul point d'entrée, sur le port 8080. Il transmet
  `/api` au backend et le reste au frontend, et porte les limites (taille des
  fichiers, délais) et les en-têtes de sécurité ;
- **`frontend`** : l'application construite, servie en fichiers statiques ;
- **`backend`** : l'API. Elle applique les migrations à chaque démarrage ;
- **`db`** : PostgreSQL 17, dont les données vivent dans le volume `db-data`.

La base et le backend ne sont joignables que depuis les autres services, pas
depuis la machine.

### Premier démarrage

Depuis la racine du dépôt :

```bash
cp .env.template .env
# remplir dans .env : POSTGRES_PASSWORD, OPENAI_API_KEY, JWT_SECRET_KEY
docker compose up -d --build
docker compose exec backend python -m app.cli create-admin <adresse e-mail> "<Prénom Nom>"
```

La dernière commande demande le mot de passe du premier administrateur.
L'application s'ouvre ensuite sur `http://localhost:8080`. Pour un autre
port, mettre `APP_PORT` dans `.env`. Un administrateur crée ensuite les autres
comptes depuis **User Management**.

Le questionnaire d'exemple (`examples/example_questionnaire.json`) s'importe
depuis la page **DD Types**.

### Au quotidien

```bash
docker compose ps                       # l'état des services
docker compose logs -f backend          # les journaux d'un service
docker compose down                     # tout arrêter (les données restent)
git pull && docker compose up -d --build   # mettre à jour : migrations comprises
```

`docker compose down -v` supprime aussi le volume `db-data`, **donc toutes les
données**.

### Sauvegarde

```bash
# sauvegarder la base dans un fichier
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > sauvegarde.sql
# la restaurer, dans une base vide
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sauvegarde.sql
```

### Accéder à la base depuis la machine

Le port 5432 n'est pas publié. Pour l'ouvrir, sur cette machine seulement,
créer un `docker-compose.override.yml` à la racine (ignoré par git) :

```yaml
services:
  db:
    ports:
      - "127.0.0.1:5432:5432"
```

### Bannière des rapports PDF

Le dossier `branding/` du dépôt (ignoré par git) est monté dans le backend, en
lecture seule, sur `/app/branding`. Pour une bannière en tête des PDF, y
déposer l'image, puis mettre dans `.env` :
`BRAND_BANNER_PATH=/app/branding/<fichier>`. Sans dossier `branding/`, Docker
en crée un vide, et les rapports sortent sans bannière.

### Scripts et commandes d'administration

Ils se lancent dans le conteneur du backend, par exemple :
`docker compose exec backend python scripts/audit_integrity.py`.

## Lancement à la main (développement)

### Prérequis

- [uv](https://docs.astral.sh/uv/) 0.9.17 ou plus récent. Il installe lui-même
  Python 3.12 au besoin (`backend/.python-version`) ;
- Node.js 24, avec npm (`frontend/.nvmrc`) ;
- un serveur PostgreSQL 17 ;
- une clé d'API OpenAI.

### 1. Configuration

```bash
cp .env.template backend/.env
```

Dans `backend/.env`, renseigner au minimum `POSTGRES_PASSWORD` (avec
`POSTGRES_HOST=localhost` en local), `OPENAI_API_KEY` et `JWT_SECRET_KEY`.
Chaque variable est décrite dans le fichier.

Le frontend n'a pas besoin de `.env` : il appelle l'API sur `/api`, et en
développement le serveur de Vite transmet ces appels au backend, sur
`http://localhost:8000` (réglable par `VITE_API_PROXY` dans `frontend/.env`).

### 2. Base de données

Créer l'utilisateur et la base, avec les valeurs de `backend/.env` :

```sql
CREATE USER easy_diligence WITH PASSWORD '<mot de passe>';
CREATE DATABASE easy_diligence OWNER easy_diligence;
```

Puis créer les tables, depuis `backend/` :

```bash
uv run alembic upgrade head
```

La même commande applique, plus tard, les migrations ajoutées au fil des
versions, en gardant les données. Pour une base créée avant la migration
`0002`, lancer d'abord `uv run python scripts/audit_integrity.py` (en lecture
seule) : il liste les lignes que `0002` corrigera, et celles qui l'arrêteraient
faute d'une décision.

### 3. Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

L'API répond sur `http://localhost:8000/api`. Sa documentation interactive,
`http://localhost:8000/docs`, est fermée par défaut : pour l'ouvrir en
développement, mettre `DOCS_ENABLED=true` dans `backend/.env`.

Sous Windows, si `uv sync` échoue avec « os error 1224 », relancer la commande
avec la variable `UV_LINK_MODE=copy`.

### 4. Frontend

```bash
cd frontend
npm ci
npm run dev
```

L'application s'ouvre sur `http://localhost:5173`.

### 5. Premier administrateur

Il n'y a pas d'inscription libre : un administrateur crée les comptes. Le
premier se crée en ligne de commande, depuis `backend/` :

```bash
uv run python -m app.cli create-admin <adresse e-mail> "<Prénom Nom>"
```

Le mot de passe est demandé au clavier. Ensuite, un administrateur crée les
autres comptes depuis **User Management** (« Create user »), avec leur rôle et
un mot de passe provisoire qu'il leur transmet, et que chacun change dans son
profil.

### 6. Premier questionnaire

Un questionnaire d'exemple, fictif, est fourni : 18 questions sur un fonds, en
6 sections. Pour l'importer sans passer par l'interface, lancer depuis
`backend/` :

```bash
uv run python scripts/import_questionnaire.py ../examples/example_questionnaire.json EXAMPLE "Example questionnaire"
```

On peut aussi l'importer depuis la page **DD Types**.

### Build de production

En production, l'application tourne avec Docker (« Démarrage avec Docker »).
Sans Docker : `npm run build` dans `frontend/` produit `frontend/dist/`, un site
statique à servir tel quel, avec un renvoi de toutes les routes vers
`index.html` (voir `frontend/nginx.conf`) et `/api` transmis au backend (voir
`proxy/nginx.conf`). Le backend se lance alors sans `--reload`.

## Faire évoluer la base

Le schéma est décrit par les modèles (`backend/app/models/`, en SQLModel) et
versionné par Alembic (`backend/alembic/versions/`). Pour un changement de
structure, depuis `backend/` :

```bash
# 1. modifier le modèle, puis générer la migration
uv run alembic revision --autogenerate -m "ajoute la colonne X"
# 2. relire le fichier produit dans alembic/versions/, puis l'appliquer
uv run alembic upgrade head
# 3. régénérer le script SQL complet du schéma
uv run alembic upgrade head --sql > db/schema.sql
```

`db/schema.sql` crée toute la base PostgreSQL d'un coup, pour qui veut s'en
passer d'Alembic. `uv run alembic check` vérifie que les migrations
correspondent aux modèles.

## Tests et qualité

```bash
# Backend, depuis backend/ (uv sync installe aussi les outils de développement)
uv run pytest                    # toute la suite
uv run ruff check .              # lint
uv run ruff format .             # formatage
uv run mypy app                  # types
uv run pip-audit --skip-editable # failles connues des dépendances

# Frontend, depuis frontend/
npm run lint
npm run format                   # formatage (Prettier) ; format:check le vérifie
npm run build
```

Les tests n'ont besoin ni de base ni de clé OpenAI. Leurs réglages sont fixés
dans `pyproject.toml` (section `[tool.pytest.ini_options]`, via pytest-env) et
priment sur `backend/.env` : un test ne peut pas atteindre une vraie base.

Une seule exception, réservée à la CI : avec la variable `TEST_POSTGRES_URL`,
les tests tournent sur le PostgreSQL jetable de la CI. Le schéma y est créé
par les migrations, et les tables sont vidées avant chaque test. Seul
`tests/conftest.py` lit cette variable, et il refuse tout hôte autre que
`localhost` ou `127.0.0.1`. Les tests marqués `postgres`, qui vérifient ce que
seul PostgreSQL connaît (index partiels, contraintes `CHECK`, JSONB, fuseaux
horaires), ne tournent que là.

Chaque test a sa propre base SQLite en mémoire, créée à partir des modèles.
`tests/conftest.py` fournit cette base, un client d'API, des utilisateurs et
leurs en-têtes d'authentification, des données de départ (sociétés, types de
DD, sessions) et un faux client OpenAI pour les vector stores. Le moteur de
réponses est testé avec un faux client lui aussi (`tests/test_processing.py`).

`npm run lint` n'accepte aucun avertissement (`--max-warnings 0`) et vérifie
aussi les couches du frontend.

**Contrôles automatiques** :
- **À chaque commit**, des hooks pre-commit lancent ruff et cherchent les
  fichiers trop gros, les clés privées et les clés OpenAI. Pour les installer
  une fois, depuis la racine du dépôt :
  `uv run --project backend pre-commit install`.
- **Sur GitHub**, la CI (`.github/workflows/ci.yml`) lance le lint, le
  formatage, les types, les tests et l'audit du backend, puis le lint, le
  formatage et le build du frontend. Elle joue aussi les migrations sur un
  PostgreSQL 17 jetable : montée, `alembic check`, descente complète puis
  remontée, et `db/schema.sql` à jour. Elle relance enfin les tests sur ce
  PostgreSQL. Un test en échec apparaît en annotation sur la pull request.
  Enfin, elle construit et démarre toute l'application avec docker compose,
  puis l'utilise à travers le proxy : l'application et l'une de ses routes,
  les en-têtes de sécurité, l'API, la création du premier administrateur et
  sa connexion.

## Structure du dépôt

```
backend/              API FastAPI
  app/
    api/              router.py, routes/ (un router par ressource), deps.py
    core/             transverse : config, base, sécurité, cache, e-mail
    engine/           moteur de réponses : client OpenAI, traitement, synthèses
    services/         logique métier et accès à la base
    exports/          rapport PDF
    models/           tables SQLModel et ce que l'API en lit et en renvoie
  alembic/            migrations de la base (Alembic)
  db/schema.sql       script SQL complet du schéma, généré
  scripts/            import et mise à jour de questionnaires, audit de la base
  tests/
  Dockerfile          image du backend
frontend/             application React (Vite, Tailwind)
  src/                Feature-Sliced Design, du haut vers le bas :
    app/              routeur, fournisseurs (thème, connexion), styles globaux
    pages/            une page par route
    widgets/          blocs de page : mise en page, tableau de bord, carte d'un
                      type de DD, réponses, vector stores
    features/         actions de l'utilisateur : connexion, création de
                      session, revue des réponses, administration
    entities/         objets métier : appels d'API, modèle, petits composants
    shared/           client HTTP, composants d'interface, utilitaires
  Dockerfile          image du frontend (construit par Node, servi par nginx)
  nginx.conf          le service des fichiers de l'application
proxy/                le point d'entrée : nginx devant le frontend et le backend
docker-compose.yml    les quatre services (proxy, frontend, backend, db)
examples/             questionnaire d'exemple au format d'import
docs/ARCHITECTURE.md  conception détaillée
.github/workflows/    intégration continue
.env.template         toutes les variables de configuration
VERSION.md            version de l'application et des outils
CHANGELOG.md          journal des changements
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) : le modèle de données, le
  moteur de réponses, le cloisonnement par utilisateur, les synthèses, l'export
  PDF et le design system du frontend.
- [`VERSION.md`](VERSION.md) : la version de l'application et celle des outils
  (Python, uv, Node). Les versions des dépendances sont figées dans
  `backend/uv.lock` et `frontend/package-lock.json`.
- [`CHANGELOG.md`](CHANGELOG.md) : le journal des changements.

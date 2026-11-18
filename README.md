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
  détail des questions et réponses en annexe) et un export Excel.
- **Comptes et cloisonnement** : rôles `admin` et `analyst`. Chacun ne voit que
  ses propres données, et l'administrateur voit tout.

## Démarrage en local

Le déploiement par Docker Compose arrive dans une prochaine version. En
attendant, l'application se lance à la main.

### Prérequis

- [uv](https://docs.astral.sh/uv/) 0.9.17 ou plus récent. Il installe lui-même
  Python 3.12 au besoin (`backend/.python-version`) ;
- Node.js 24, avec npm (`frontend/.nvmrc`) ;
- un serveur MySQL 8 ;
- une clé d'API OpenAI.

### 1. Configuration

```bash
cp .env.template backend/.env
```

Dans `backend/.env`, renseigner au minimum `DATABASE_URL`, `OPENAI_API_KEY` et
`JWT_SECRET_KEY`. Chaque variable est décrite dans le fichier.

Créer ensuite `frontend/.env`, avec une seule ligne :

```
VITE_API_URL=http://localhost:8000
```

### 2. Base de données

Créer une base vide et son utilisateur :

```sql
CREATE DATABASE easy_diligence CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'easy_diligence'@'localhost' IDENTIFIED BY '<mot de passe>';
GRANT ALL PRIVILEGES ON easy_diligence.* TO 'easy_diligence'@'localhost';
```

Les tables sont créées au premier démarrage du backend.

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

Un compte créé depuis la page d'inscription est toujours analyste. Le premier
administrateur se crée en ligne de commande, depuis `backend/` :

```bash
uv run python -m app.cli create-admin <adresse e-mail> "<Prénom Nom>"
```

Le mot de passe est demandé au clavier. Un administrateur peut ensuite changer
le rôle des autres comptes depuis l'interface.

### 6. Premier questionnaire

Un questionnaire d'exemple est fourni. Pour l'importer sans passer par
l'interface, lancer depuis `backend/` :

```bash
uv run python scripts/import_questionnaire.py ../examples/example_questionnaire.json EXAMPLE "Example"
```

On peut aussi l'importer depuis la page **DD Types**.

### Build de production

```bash
cd frontend
npm run build
```

Le dossier `frontend/dist/` est un site statique à servir tel quel, avec un
renvoi de toutes les routes vers `index.html`. Le backend se lance alors sans
`--reload`.

## Tests et qualité

```bash
# Backend, depuis backend/ (uv sync installe aussi les outils de développement)
uv run pytest tests/test_auth_security.py tests/test_citation_format.py tests/test_dashboard.py
uv run pytest                    # toute la suite
uv run ruff check .              # lint
uv run ruff format .             # formatage
uv run mypy app                  # types
uv run pip-audit --skip-editable # failles connues des dépendances

# Frontend, depuis frontend/
npm run lint
npm run build
```

Les tests n'ont besoin ni de base ni de clé OpenAI. Leurs réglages sont fixés
dans `pyproject.toml` (section `[tool.pytest.ini_options]`, via pytest-env) et
priment sur `backend/.env` : un test ne peut pas atteindre une vraie base.

La suite complète compte encore des tests anciens en échec, qui sont en cours
de reprise. ESLint signale aussi de nombreux problèmes dans le code existant du
frontend.

**Contrôles automatiques** :
- **À chaque commit**, des hooks pre-commit lancent ruff et cherchent les
  fichiers trop gros, les clés privées et les clés OpenAI. Pour les installer
  une fois, depuis la racine du dépôt :
  `uv run --project backend pre-commit install`.
- **Sur GitHub**, la CI (`.github/workflows/ci.yml`) lance le lint, le
  formatage, les types, les tests et l'audit du backend, puis le build du
  frontend.

## Structure du dépôt

```
backend/              API FastAPI
  app/
    api/              router.py, routes/ (un router par ressource), deps.py
    core/             transverse : config, base, sécurité, cache, e-mail
    engine/           moteur de réponses : client OpenAI, traitement, synthèses
    services/         logique métier : authentification, droits, import
    exports/          exports PDF et Excel
    models/           modèles SQLAlchemy
    schemas/          schémas Pydantic
  migrations/         anciens correctifs SQL appliqués à la main
  scripts/            import et mise à jour de questionnaires
  tests/
frontend/             application React (Vite, Tailwind)
  src/
    pages/            une page par route
    features/         revue des réponses, questionnaires, vector stores
    components/       composants partagés, dont components/ui
    contexts/         connexion, thème
    services/         client HTTP
    utils/            statuts, libellés, formats
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

# Version

**Easy Diligence 0.1.0**

Les versions des dépendances sont celles figées dans `backend/uv.lock` et
`frontend/package-lock.json`. Pour les mettre à jour, modifier ces fichiers (via
`uv lock` et `npm install`), puis ce tableau.

## Outils

| Outil | Version |
| --- | --- |
| Python | 3.11 minimum (`requires-python`), vérifié avec 3.12.0 |
| uv | 0.9.17 |
| Node.js | vérifié avec 24.10.0 |
| npm | 11.12.1 |
| MySQL | 8.0 |
| Modèle OpenAI | `gpt-5.6-luna` (valeur de `.env.template`) |

Il n'y a pas encore d'image Docker.

## Backend (`backend/uv.lock`)

| Paquet | Version |
| --- | --- |
| fastapi | 0.164.0 |
| starlette | 1.10.0 |
| uvicorn | 0.50.1 |
| sqlalchemy | 2.0.23 |
| pymysql | 1.2.4 |
| cryptography | 50.0.2 |
| pydantic | 2.14.3 |
| pydantic-settings | 2.16.3 |
| openai | 2.2.0 (figée : le moteur est réglé sur cette version) |
| httpx | 0.28.1 |
| redis | 5.0.1 |
| pyjwt | 2.15.1 |
| bcrypt | 5.0.0 |
| python-multipart | 0.0.34 |
| jinja2 | 3.1.6 |
| aiosmtplib | 5.1.3 |
| typer | 0.29.2 |
| reportlab | 4.4.4 |
| pandas | 2.3.2 |
| openpyxl | 3.1.5 |
| pytest (dev) | 7.4.3 |
| pytest-asyncio (dev) | 0.21.1 |
| pytest-env (dev) | 1.1.3 |
| ruff (dev) | 0.13.2 |

## Frontend (`frontend/package-lock.json`)

| Paquet | Version |
| --- | --- |
| react, react-dom | 18.3.1 |
| react-router-dom | 6.30.1 |
| axios | 1.11.0 |
| react-markdown | 10.1.0 |
| remark-gfm | 4.0.1 |
| @heroicons/react | 2.2.0 |
| react-hot-toast | 2.5.2 |
| @fontsource/roboto | 5.3.0 |
| vite | 4.5.14 |
| @vitejs/plugin-react | 3.1.0 |
| tailwindcss | 3.4.17 |
| @tailwindcss/typography | 0.5.19 |
| postcss | 8.5.6 |
| autoprefixer | 10.4.21 |
| eslint | 8.57.1 |
| prettier | 3.6.2 |

## Journal des changements

### Non publié

- **Structure du backend** : les fichiers sont rangés en `api/routes`, `core`,
  `engine`, `services` et `exports`, sans changement de logique.
- **Sécurité** :
  - l'inscription ne peut plus choisir son rôle : un nouveau compte est toujours
    analyste. Le premier administrateur se crée avec
    `python -m app.cli create-admin` ;
  - `DATABASE_URL`, `OPENAI_API_KEY` et `JWT_SECRET_KEY` sont obligatoires, et
    l'application refuse de démarrer sans eux ;
  - les jetons sont stockés hachés et rendus uniques, le jeton de
    rafraîchissement passe dans le corps de la requête, et le jeton de
    réinitialisation du mot de passe ne sert qu'une fois ;
  - la connexion est limitée après des échecs répétés ;
  - la taille et le type des fichiers envoyés sont vérifiés ;
  - une erreur imprévue renvoie un message générique, sa trace part dans les
    journaux ;
  - `/docs` est fermé par défaut (`DOCS_ENABLED`) ;
  - les deux WebSockets inutilisés sont supprimés.
- **Dépendances** : PyJWT et bcrypt remplacent python-jose et passlib ;
  FastAPI, Starlette, python-multipart, jinja2, cryptography et les dépendances
  qu'elles entraînent sont montés. Les dépendances d'exécution n'ont plus de
  faille connue d'après `pip-audit`.

### 0.1.0 — 18/11/2026

Premier commit d'Easy-Diligence, sur un historique neuf.

- La documentation est réécrite : `README.md`, `docs/ARCHITECTURE.md` et ce
  fichier. Les revues et analyses périmées sont supprimées, ainsi que les restes
  Docker et les scripts de mesure ponctuels.
- Toute la configuration est listée et commentée dans `.env.template`.
  `DATABASE_URL` devient obligatoire, et une `JWT_SECRET_KEY` vide est refusée.
- Les éléments de charte sont retirés : un logo neutre les remplace, et la
  bannière du rapport PDF devient facultative (`BRAND_BANNER_PATH`).
- Un questionnaire d'exemple est fourni dans `examples/`.

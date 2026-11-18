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
| fastapi | 0.104.1 |
| starlette | 0.27.0 |
| uvicorn | 0.24.0 |
| sqlalchemy | 2.0.23 |
| pymysql | 1.1.0 |
| pydantic | 2.5.0 |
| pydantic-settings | 2.1.0 |
| openai | 2.2.0 |
| httpx | 0.25.2 |
| redis | 5.0.1 |
| python-jose | 3.3.0 |
| passlib | 1.7.4 |
| bcrypt | 4.1.2 |
| reportlab | 4.4.4 |
| pandas | 2.3.2 |
| openpyxl | 3.1.5 |
| pytest (dev) | 7.4.3 |
| pytest-asyncio (dev) | 0.21.1 |
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

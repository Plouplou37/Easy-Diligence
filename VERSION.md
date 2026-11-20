# Version

**Easy Diligence 0.1.0**

## Outils

| Outil | Version | Figée dans |
| --- | --- | --- |
| Python | 3.12 | `backend/.python-version` |
| uv | 0.9.17 ou plus récent | `backend/pyproject.toml` (`[tool.uv] required-version`) |
| Node.js | 24 | `frontend/.nvmrc` |
| PostgreSQL | 17 | |
| Modèle OpenAI | `gpt-5.6-luna` | `.env.template` (`OPENAI_MODEL`) |

## Images Docker

Figées à la version exacte, jamais `latest` : une image ne change pas sans
qu'un commit le dise.

| Service | Image | Figée dans |
| --- | --- | --- |
| `backend` | `python:3.12.16-slim-trixie`, avec uv `0.9.17` (`ghcr.io/astral-sh/uv`) | `backend/Dockerfile` |
| `frontend` | `node:24.22.3-alpine` pour construire, `nginx:1.30.7-alpine` pour servir | `frontend/Dockerfile` |
| `proxy` | `nginx:1.30.7-alpine` | `proxy/Dockerfile` |
| `db` | `postgres:17.12-trixie` | `docker-compose.yml` |

Les dépendances sont déclarées dans `backend/pyproject.toml` et
`frontend/package.json`, et leurs versions exactes figées dans `backend/uv.lock`
et `frontend/package-lock.json`.

Les changements d'une version à l'autre sont dans [`CHANGELOG.md`](CHANGELOG.md).

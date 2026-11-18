# Version

**Easy Diligence 0.1.0**

## Outils

| Outil | Version | Figée dans |
| --- | --- | --- |
| Python | 3.12 | `backend/.python-version` |
| uv | 0.9.17 ou plus récent | `backend/pyproject.toml` (`[tool.uv] required-version`) |
| Node.js | 24 | `frontend/.nvmrc` |
| MySQL | 8.0 | |
| Modèle OpenAI | `gpt-5.6-luna` | `.env.template` (`OPENAI_MODEL`) |

Les dépendances sont déclarées dans `backend/pyproject.toml` et
`frontend/package.json`, et leurs versions exactes figées dans `backend/uv.lock`
et `frontend/package-lock.json`.

Les changements d'une version à l'autre sont dans [`CHANGELOG.md`](CHANGELOG.md).

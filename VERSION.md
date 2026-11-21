# Version

**Easy Diligence 0.1.0**

## Tools

| Tool | Version | Pinned in |
| --- | --- | --- |
| Python | 3.12 | `backend/.python-version` |
| uv | 0.9.17 or newer | `backend/pyproject.toml` (`[tool.uv] required-version`) |
| Node.js | 24 | `frontend/.nvmrc` |
| PostgreSQL | 17 | |
| OpenAI model | `gpt-5.6-luna` | `.env.template` (`OPENAI_MODEL`) |

## Docker images

Pinned to the exact version, never `latest`: an image does not change unless a
commit says so.

| Service | Image | Pinned in |
| --- | --- | --- |
| `backend` | `python:3.12.16-slim-trixie`, with uv `0.9.17` (`ghcr.io/astral-sh/uv`) | `backend/Dockerfile` |
| `frontend` | `node:24.22.3-alpine` to build, `nginx:1.30.7-alpine` to serve | `frontend/Dockerfile` |
| `proxy` | `nginx:1.30.7-alpine` | `proxy/Dockerfile` |
| `db` | `postgres:17.12-trixie` | `docker-compose.yml` |

## Deployment (Terraform)

| Tool | Version | Pinned in |
| --- | --- | --- |
| Terraform | 1.17.2 (1.11 at least) | `infra/*/versions.tf`, CI |
| Provider `azurerm` | 5.14 | `infra/azure/.terraform.lock.hcl` |
| Provider `aws` | 6.73 | `infra/aws/.terraform.lock.hcl` |
| Providers `random`, `time` | 3.9, 0.14 | the same files |

The dependencies are declared in `backend/pyproject.toml` and
`frontend/package.json`, and their exact versions pinned in `backend/uv.lock`
and `frontend/package-lock.json`.

The changes from one version to the next are in [`CHANGELOG.md`](CHANGELOG.md).

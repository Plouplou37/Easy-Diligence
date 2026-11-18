# CLAUDE.md

Guide court pour un agent qui travaille sur Easy Diligence. Le reste est dans :
- [`README.md`](README.md) : installer, lancer, tester ;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) : la conception (moteur,
  cloisonnement, synthèses, export, design system) ;
- [`VERSION.md`](VERSION.md) : les versions.

## Repères

- Backend FastAPI dans `backend/app/` :
  - `api/` : `router.py` (assemblage), `routes/` (un router par ressource),
    `deps.py` (dépendances communes) ;
  - `core/` : le transverse (config, database, sécurité, cache, e-mail) ;
  - `engine/` : le moteur de réponses (`openai_client.py`, `processor.py`,
    `summarizer.py`) ;
  - `services/` : la logique métier (authentification, droits, import de
    questionnaires) ;
  - `exports/` : les exports PDF et Excel ;
  - `models/` (SQLAlchemy) et `schemas/` (Pydantic).
- Frontend React dans `frontend/src/`.
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
- **Ne jamais lancer de test contre une vraie base.** `db.rollback()` n'annule
  rien, à cause de l'autocommit du pilote (voir `docs/ARCHITECTURE.md`). Les
  réglages de test de `pyproject.toml` (pytest-env) imposent une base SQLite
  en mémoire et une fausse clé OpenAI : ne pas les retirer.
- **Erreurs** : ne jamais renvoyer `str(e)` au client. Pour une erreur attendue,
  lever une exception de `core/exceptions.py`, dont le message est écrit pour
  l'utilisateur. Pour le reste, `logger.exception(...)` puis un message
  générique.
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
uv run pytest tests/test_auth_security.py tests/test_citation_format.py tests/test_dashboard.py
uv run ruff check .
# frontend/
npm run build
npm run lint
```

Ruff et ESLint signalent déjà de nombreux problèmes dans le code existant : le
critère est de n'en ajouter aucun.

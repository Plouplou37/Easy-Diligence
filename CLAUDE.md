# CLAUDE.md

Guide court pour un agent qui travaille sur Easy Diligence. Le reste est dans :
- [`README.md`](README.md) : installer, lancer, tester ;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) : la conception (moteur,
  cloisonnement, synthèses, export, design system) ;
- [`VERSION.md`](VERSION.md) : les versions.

## Repères

- Backend FastAPI dans `backend/app/` : routers dans `api/`, logique dans `core/`.
  Le moteur est dans `core/openai_client.py` et `core/processor.py`.
- Frontend React dans `frontend/src/`.
- La configuration est lue par `backend/app/config.py`. Chaque variable est
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
  rien, à cause de l'autocommit du pilote (voir `docs/ARCHITECTURE.md`). Utiliser
  un faux client OpenAI et une fausse session.
- **Frontend** : uniquement des tokens de couleur du thème, ni palette Tailwind,
  ni variante `dark:`. Ajouter une classe de couleur à `Button` est interdit.
- **Un champ envoyé au modèle doit être visible dans l'interface.**
- Ne pas valider un type de DD par commodité : la validation est irréversible.
- Commits : messages en français.

## Vérifier un changement

```bash
# backend/
DATABASE_URL=sqlite:// uv run pytest tests/test_citation_format.py tests/test_dashboard.py --noconftest
uv run ruff check .
# frontend/
npm run build
npm run lint
```

Ruff et ESLint signalent déjà de nombreux problèmes dans le code existant : le
critère est de n'en ajouter aucun.

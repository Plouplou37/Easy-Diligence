# Architecture

Ce document décrit la conception d'Easy Diligence : les choix du moteur de
réponses, les règles de cloisonnement, les fonctionnalités et le design system
du frontend. Pour installer et lancer l'application, voir le
[README](../README.md).

## Stack

- **Backend** : FastAPI (Python 3.12), modèles SQLModel (SQLAlchemy 2 et
  Pydantic), PostgreSQL 17 via psycopg 3, migrations Alembic.
  Code dans `backend/app/`, routes sous le préfixe `/api` :
  - `api/` : l'assemblage des routers (`router.py`), un router par ressource
    (`routes/`) et les dépendances communes (`deps.py` : l'utilisateur, la
    session et le type de DD lus dans l'URL, droits vérifiés) ;
  - `core/` : le transverse (configuration, base, sécurité, cache, e-mail) ;
  - `engine/` : le moteur de réponses ;
  - `services/` : la logique métier et les accès à la base (`sessions`,
    `answers`, `processing`, `vector_stores`, `dd_types`, `authz`, `auth`,
    `file_parser`). Les services lèvent les erreurs de `core/exceptions.py` et
    ne connaissent pas FastAPI ;
  - `exports/` : le rapport PDF ;
  - `models/` : une table par fichier, avec ses formes d'API : une classe de
    base porte les champs et leurs limites, la table, le formulaire de création
    et la réponse en héritent.
- **Frontend** : React 18, Vite 8, Tailwind 4, axios et react-router 7. Code dans
  `frontend/src/`.
- **LLM** : l'API **Responses** d'OpenAI (`client.responses.create`). Le modèle
  est choisi par `OPENAI_MODEL`. `openai_client.is_reasoning_model()` adapte les
  paramètres au modèle : pas de `temperature` sur les modèles à raisonnement
  (GPT-5.x), nom de l'outil web (`web_search` ou `web_search_preview`), budget de
  sortie et `reasoning.effort`. Passer de `gpt-5.6-luna` à `gpt-4o` ne demande donc
  que de changer cette variable.
- **Authentification** : jetons JWT (PyJWT) d'accès et de rafraîchissement,
  mots de passe hachés avec bcrypt, rôles `admin` et `analyst`. Voir
  « Authentification et sécurité ».
- **Tâches longues** : les `BackgroundTasks` de FastAPI, dans le processus web.

## Base de données

- **PostgreSQL**, configuré par `POSTGRES_*` ou `DATABASE_URL`
  (`core/database_settings.py`). Les tests tournent sur SQLite en mémoire.
- **Alembic possède le schéma** : `alembic upgrade head` crée la base puis
  applique chaque évolution, sans toucher aux données. L'application ne crée
  aucune table au démarrage.
  - La migration `0001_initial_schema` crée toute la base. Elle a été générée
    depuis les modèles puis relue. Elle reprend l'état final des anciens
    correctifs SQL appliqués à la main sur la base MySQL : les index, les
    cascades et les contraintes `CHECK`.
  - La migration `0002_integrity` pose les règles d'intégrité (ci-dessous).
    Elle corrige d'abord les données qui les violent, et s'arrête sans rien
    changer devant celles qui demandent une décision.
    `scripts/audit_integrity.py` les liste avant de migrer.
  - `db/schema.sql` est le même schéma en un seul script SQL, régénéré avec
    `alembic upgrade head --sql`.
  - `alembic check` vérifie que les migrations correspondent aux modèles.
  - Alembic ne lit que les réglages de la base (`DatabaseSettings`) : une
    migration ne demande ni la clé OpenAI ni la clé JWT.
  - **La CI vérifie les migrations sur un vrai PostgreSQL 17** (service jetable
    du job `backend`, identifiants propres à la CI) : `upgrade head`, `check`,
    `downgrade base` puis de nouveau `upgrade head` (chaque descente est
    jouée), et `db/schema.sql` comparé à un script régénéré. `DATABASE_URL`
    n'est posé que pour ces étapes.
  - **Les tests tournent deux fois en CI** : sur SQLite, comme en local, puis
    sur ce PostgreSQL, avec `TEST_POSTGRES_URL`. Cette variable n'est lue que
    par `tests/conftest.py`, qui exige un hôte local. Le schéma est alors créé
    par `alembic upgrade head`, comme en production, et non par
    `create_all`. Les tables sont vidées (`TRUNCATE … RESTART IDENTITY`) avant
    chaque test, et une attente de verrou de plus de 10 s fait échouer le test
    au lieu de bloquer la CI. Les tests marqués `postgres` (`test_postgres.py`)
    ne tournent que là.
  - **Les listes ont un ordre stable** (`ORDER BY` jusqu'à l'identifiant).
    SQLite rend les lignes dans l'ordre d'insertion, PostgreSQL non, et
    `now()` donne la même heure à toutes les lignes d'une transaction.
- **Les modèles** (`models/`) sont en SQLModel : chaque table est à la fois un
  modèle SQLAlchemy et un modèle Pydantic. `models/base.py` fixe :
  - une **convention de nommage** des contraintes, pour que les migrations
    puissent les retrouver par leur nom ;
  - le type JSON (JSONB sous PostgreSQL) ;
  - les dates en `TIMESTAMP WITH TIME ZONE`, remplies par la base ;
  - les énumérations, stockées en texte avec une contrainte `CHECK` plutôt qu'en
    type `ENUM` natif : ajouter un membre ne demande pas d'`ALTER TYPE`. On
    stocke la **valeur**, en minuscules (`needs_review`) :
    `enum_type(…, store_values=True)`. Seul `dd_sessions.status` stocke encore
    le nom ;
  - les colonnes obligatoires avec une valeur par défaut (`defaulted_field`) :
    NOT NULL, et la valeur par défaut est posée **par la base** aussi, pour
    qu'une insertion en SQL direct la reçoive.
- **La base tient elle-même ses règles** : le code ne suppose rien qu'elle ne
  garantisse.
  - Une exécution par session et type de DD ; au plus une réponse courante par
    exécution et question (index unique partiel `WHERE is_current`) ; une
    synthèse par session, type de DD et section ; une assignation de vector
    store par session, type de DD (ou toute la session) et vector store, vers un
    type de DD qui existe ; des codes de section uniques dans un type de DD, et
    de question dans une section.
  - Deux NULL sont différents pour SQL. La synthèse globale (`section_id`
    NULL) et l'assignation à toute la session (`dd_type_id` NULL) ont donc
    chacune un index unique partiel (`… WHERE section_id IS NULL`), plutôt
    qu'un `NULLS NOT DISTINCT` propre à PostgreSQL : SQLite le connaît aussi,
    et les tests voient la règle.
  - Aucun booléen, statut, compteur ou date de création n'est NULL ; chaque
    statut a sa contrainte `CHECK`, et `users.role` aussi. Seul
    `dd_summary_batches.status` reste libre : il porte les statuts d'OpenAI,
    qui peuvent changer.
  - Une violation n'est jamais une erreur 500. Le code rattrape
    l'`IntegrityError` et répond comme si sa propre vérification avait vu le
    conflit : un code déjà pris donne un 409, une assignation ou une synthèse
    déjà là est reprise. Une synthèse s'insère dans un savepoint, pour que
    son échec laisse en place le reste de la transaction.
- **Index** : PostgreSQL n'indexe pas les clés étrangères automatiquement,
  contrairement à MySQL. Les colonnes de jointure sont donc indexées
  explicitement dans les modèles.
- **Requêtes typées** : SQLModel type les colonnes comme des valeurs Python. Pour
  que mypy accepte un filtre, entourer la colonne de `col()` :
  `.filter(col(User.id) == user_id)`.
- **Transactions réelles** : rien n'est écrit avant `commit()`, et `rollback()`
  annule tout depuis le dernier commit. La base MySQL d'origine forçait
  l'autocommit au niveau du pilote, si bien que les rollbacks n'avaient aucun
  effet.
- **Adresses e-mail** : enregistrées et comparées en minuscules
  (`models/user.py`, type `Email`). PostgreSQL compare le texte en tenant
  compte de la casse.

## Modèle de données

- `DDType` (`models/dd_types.py`) → `DDSection` → `DDQuestion`
  (`models/questions.py`). Un type de DD est un questionnaire.
- `Company` (`models/company.py`) porte deux entités : le **fonds** sous revue
  (`name`, `website_url`) et sa **société de gestion**
  (`management_company_name`, `management_company_website`, facultatifs). Les
  distinguer permet au moteur de savoir de laquelle une question parle.
- `DDSession` (`models/session.py`) : une DD sur un fonds (`company_id`,
  `created_by`, `assigned_to`, `dd_types_json`).
- `DDExecution` (`models/execution.py`) : l'exécution d'**un** type de DD dans une
  session, une seule par couple. Statuts (`ExecutionStatus`) : `not_started`,
  `in_progress`, `generated`, `failed`, `paused`, etc. Elle porte le
  `conversation_id`.
- `DDAnswer` (`models/answer.py`) : une réponse, versionnée par `version` et
  `is_current`, avec `status`, `response_id` et `sources` (JSON). L'historique va
  dans `DDAnswerHistory`.
- `DDResponse` et `DDMessage` : les réponses et messages bruts d'OpenAI, chaînés
  par `previous_response_id`.
- `VectorStore` et `SessionVectorStore` (`models/vector_store.py`) : les vector
  stores OpenAI et leur assignation aux sessions et aux types de DD.
- `DDSummary` (`models/summary.py`) : les résumés générés, par section ou pour un
  type de DD entier.
- `DDSummaryBatch` : le suivi des synthèses envoyées à la Batch API.

### Règles de cycle de vie

- **Inactif veut dire « non proposable », pas « invisible ».** Seul l'écran de
  création de session (`SessionCreate.jsx`) filtre sur `is_active`. Les écrans qui
  affichent l'existant chargent aussi les types inactifs, sinon désactiver un type
  ferait disparaître en silence les réponses produites sous lui. Le lancement est
  bloqué par `canStartDD` (`SessionDetail.jsx`), et `DDCard` affiche un badge
  « Inactive ».
- **La validation d'un type de DD est à sens unique.** Un type en brouillon est
  parfaitement utilisable : `is_validated` n'intervient ni dans le moteur ni dans
  `/processing`. La validation gèle seulement la **structure**
  (`check_*_immutability`, `api/routes/questions.py`), et aucun endpoint ne permet de
  dévalider.
- `PUT /company/{id}` attend un `CompanyCreate` **complet**, pas un patch : un
  envoi partiel efface les autres champs.

## Le moteur de réponses

`engine/processor.py` (`DDProcessor`) orchestre un traitement : `start_processing`,
`resume_processing` et `_process_single_question`. `engine/openai_client.py`
(`OpenAIProcessor.process_question`) fait l'appel à OpenAI.

### Un appel, deux outils

Chaque question donne lieu à **un seul appel**, avec deux outils : `file_search`
sur les vector stores rattachés, et `web_search`.

- **`tool_choice`** (`TOOL_CHOICE`, `web_search` par défaut) impose l'outil du
  premier appel :
  - `web_search` force une recherche web sur chaque question ;
  - `auto` laisse le modèle choisir ;
  - `none` n'envoie rien.

  Une valeur inconnue retombe sur `web_search`, avec un avertissement. Un
  appelant qui passe une valeur explicite garde la main.
- **Pourquoi `web_search` par défaut.** Une comparaison sur le même
  questionnaire et les mêmes documents a montré que `auto` n'économise presque
  rien en tokens d'entrée, puisque c'est la conversation chaînée qui domine. En
  revanche, le modèle saute alors le web sur la plupart des questions : les
  citations web s'effondrent, davantage de réponses reviennent sans source, et ce
  sont les questions sur la société de gestion qui en souffrent le plus. Les
  documents décrivent le fonds, alors que l'empreinte publique du gérant n'existe
  que sur le web. Forcer le web n'empêche pas le modèle de consulter ensuite les
  documents.
- **La règle de recherche du prompt système.** Forcer un outil ne décide que du
  **premier** appel : le modèle reste libre de sauter l'autre.
  `_build_system_prompt` exige donc d'utiliser **les deux** outils sur chaque
  question, en disant à quoi sert chacun. Sans vector store rattaché
  (`has_documents=False`), la règle devient : « web seul, et dire ce qui ne
  pourrait venir que des documents ». Le modèle ne doit jamais laisser croire
  qu'il a lu des documents. Cette règle coûte environ 30 % de durée en plus,
  pour des réponses nettement mieux sourcées.
- `regenerate_single_answer` envoie `"auto"` quand la régénération est guidée par
  une consigne de l'analyste.
- L'API renvoie parfois en écho `tool_choice: {"type": "web_search_preview"}`
  alors qu'on a envoyé `web_search`. La liste `tools` de la réponse fait foi : ce
  n'est pas un repli sur l'ancien outil.
- Écarté : deux appels par question, un par outil. C'est la seule garantie
  absolue que les deux outils servent, mais elle double le coût et la durée,
  puisque chaque appel renvoie toute la conversation chaînée.

### Fonds et société de gestion

Le prompt système (`_build_system_prompt`) nomme séparément `FUND UNDER REVIEW`
et `MANAGEMENT COMPANY`. Il pose ensuite une **règle de périmètre** fondée sur le
marqueur `Level: Fund` ou `Level: Management Company` que porte chaque question
des questionnaires de référence.

Ce contexte est construit par `core/utils.py` `build_company_info()`, seule source
pour les trois appelants : démarrage, reprise et régénération. Sans société de
gestion renseignée, le bloc est omis. Le comportement est alors dégradé, mais pas
cassé.

### Ce que le modèle reçoit

`DDProcessor.compose_question_text()` assemble :
1. le titre de la section ;
2. la `description` de la section, si elle est renseignée ;
3. le texte de la question ;
4. son `context_prompt`, sous l'étiquette **`Where to look:`**.

- Le **`context_prompt`** porte les sources à consulter. Il est éditable dans
  `QuestionEditor.jsx` (« Sources potentielles / Où chercher ») et arrive au modèle
  sous la même étiquette, quelle que soit la colonne du classeur d'origine.
- La **`description` de section** sert de contexte au thème. Comme tout champ
  envoyé au modèle, elle est visible dans l'interface (`SectionCard.jsx`).
- La **référence** (`A.01`) ne figure pas dans le texte envoyé. Elle ne vit que
  dans `question_code`, qui n'est pas transmis.

### Citations et sources

- **Pas de marqueurs de citation de documents dans le texte.** Sous
  `gpt-5.6-luna`, OpenAI renvoie un `output_text` troué : chaque trou tombe sur
  un `file_citation.index`, et le décalage grandit de citation en citation. Les
  `url_citation.start/end_index` dérivent aussi. Le défaut vient d'OpenAI : leur
  copie relue par `responses.retrieve` porte les mêmes trous, et le streaming ne
  change rien. `gpt-4o` n'a pas le problème.
  - **La parade** : quand des documents sont rattachés, `_build_system_prompt`
    interdit ces marqueurs. Le modèle nomme alors les documents en clair et
    termine sa réponse par une ligne `Documents consulted:` (`CONSULTED_LABEL`),
    visible dans l'interface et dans le PDF.
  - **Les sources documents** : `documents_consulted()` les reconstruit à partir
    de cette ligne. Il ne garde que les fichiers réellement renvoyés par
    `file_search_call.results`, et ignore la casse, l'extension et le numéro de
    tête (« 1. PRIVATE… »).
  - **Le filet de sécurité** : si le modèle cite quand même, `process_question`
    relance **une fois**. Les tokens de l'appel jeté sont comptés.
- **Marqueurs orphelins.** `strip_citation_markers` retire les marqueurs que le
  modèle laisse parfois sans annotation. Il s'applique à la finalisation de la
  réponse, avant le contrôle de réponse vide. Trois formes, toutes d'OpenAI :
  - `【】` vide ;
  - `【4:0†fichier.pdf】`, reconnaissable au `†` ;
  - le jeton `turn7file6`. Celui-ci est précédé de `【`, ou bien du caractère
    privé U+E200 suivi d'un libellé et de U+E202. Plusieurs jetons peuvent être
    chaînés par U+E202, et le tout est fermé par U+E201.

  Tout autre texte entre `【】` est conservé. ⚠️ Les caractères privés sont
  construits avec `chr(0xE200)` dans le code : écrits tels quels, ils seraient
  invisibles dans un éditeur.
- Tests : `tests/test_citation_format.py`.

### Mémoire, compaction et limites

- **Mémoire.** Les questions d'une exécution forment une conversation chaînée par
  `previous_response_id`, dans l'ordre `order_index`. `truncation="auto"` est
  envoyé à OpenAI.
- **Compaction.** Le chaînage fait croître l'entrée d'environ 4 000 tokens par
  question. Un questionnaire de près de 300 questions dépasserait ainsi la
  fenêtre de contexte du modèle. Au-delà de `COMPACT_THRESHOLD` (200 000 par
  défaut, voir `openai_client._apply_compaction`), l'historique est compressé
  au lieu d'être tronqué en silence. Le paramètre `context_management` passe par
  `extra_body`, car le SDK ne le connaît pas encore.
- **Paramètres des modèles à raisonnement** (`_apply_model_params`) :
  - pas de `temperature` ;
  - `max_output_tokens` d'au moins 25 000 (la constante
    `REASONING_MIN_OUTPUT_TOKENS` de `openai_client.py`), car les tokens de
    raisonnement s'y imputent ;
  - `reasoning.effort` réglé par `REASONING_EFFORT` (`low`).
- **Limitation de débit** (`engine/rate_limiter.py`) : toutes les pauses sont
  désactivées par défaut. Les quotas d'un compte OpenAI courant sont très
  au-dessus de ce qu'un traitement consomme, et les erreurs 429 sont couvertes
  par le backoff exponentiel et le disjoncteur de `DDProcessor`. Les variables
  `INTER_QUESTION_DELAY_SECONDS`, `BATCH_SLEEP_MINUTES` et
  `HIGH_TOKEN_SLEEP_SECONDS` restent comme soupape.
- **Durée.** Compter environ 15 secondes par question.

### Pause, reprise et tâches de fond

- **Pause** : passe `execution.status` à `paused`. La boucle le vérifie **entre
  deux questions**, l'arrêt n'est donc pas instantané.
- **Reprise** : conserve le `conversation_id`, saute les réponses déjà faites et
  retente celles qui ont échoué.
- **Un changement de statut est un seul `UPDATE` conditionnel**
  (`services/processing._switch`) : `… WHERE id = … AND status IN (…)`, et le
  nombre de lignes touchées dit qui l'a emporté. Deux clics, ou deux onglets,
  ne lancent donc jamais deux traitements. Deux premiers démarrages
  simultanés se heurtent à l'unicité de l'exécution : le second relit celle du
  premier.
- Les traitements tournent dans des `BackgroundTasks`, dans le processus web.
  Un redémarrage du serveur en plein traitement laisse l'exécution en
  `in_progress` : il faut alors la relancer avec « Resume ».
- **Un traitement est bloqué** quand il est `in_progress` mais que ni son
  exécution ni ses réponses n'ont bougé depuis 10 minutes (`STUCK_AFTER`).
  « Resume » le reprend alors, une seule fois. La date de l'exécution seule ne
  suffit pas : le moteur ne la touche qu'au début et à la fin d'un traitement,
  qui peut durer plus d'une heure.

## Authentification et sécurité

- **Réglages obligatoires** :
  - `DATABASE_URL`, `OPENAI_API_KEY` et `JWT_SECRET_KEY` (32 caractères au moins)
    n'ont pas de valeur par défaut. Il s'agit de `SecretStr`, qui ne
    s'affichent ni dans les journaux ni dans les représentations ;
  - s'il en manque un, `core/config.py` arrête le démarrage avec la liste des
    variables à renseigner ;
  - `backend/.env` est trouvé quel que soit le dossier de lancement, et les
    variables d'environnement priment sur lui.
- **Rôles** : `Literal["admin", "analyst"]` (`models/user.py`).
  - **Pas d'inscription libre.** Un administrateur crée les comptes
    (`POST /admin/users`, `UserCreate`) : rôle choisi, mot de passe provisoire
    que l'utilisateur change dans son profil. `UserCreate` refuse tout champ
    inconnu.
  - Le premier administrateur se crée avec `python -m app.cli create-admin`
    (`app/cli.py`), qui demande le mot de passe au clavier.
  - **Supprimer un compte** (`services/users.py`) n'est possible que s'il ne
    possède rien : ni session (créée ou assignée), ni société, type de DD,
    vector store, réponse modifiée ou synthèse. Sinon, on le désactive. La
    suppression vidait ces liens, et une société sans créateur est partagée
    avec tout le monde.
- **Une seule dépendance d'authentification** : `api/deps.py`
  (`get_current_active_user`, alias `get_current_user`, et
  `get_current_admin_user`). C'est le seul endroit où un jeton est décodé, et
  où un compte inactif est refusé.
- **Jetons** (`core/security.py`) :
  - chaque jeton porte un `jti` aléatoire. Sans lui, deux jetons émis dans la
    même seconde étaient identiques ;
  - `user_sessions` ne stocke que leur SHA-256 ;
  - le jeton de rafraîchissement passe dans le corps de `POST /auth/refresh`,
    jamais dans l'URL, et il est remplacé à chaque usage ;
  - le jeton de réinitialisation du mot de passe porte une empreinte du mot de
    passe en cours : il cesse de fonctionner dès que le mot de passe change.
    Il ne sert donc qu'une fois, sans être stocké. Le lien de l'e-mail mène à
    `/reset-password?token=…` (page publique), qui l'envoie à
    `POST /auth/reset-password-confirm` ;
  - la demande de lien répond pareil, et aussi vite, que l'adresse existe ou
    non : l'e-mail part dans une tâche de fond, après la réponse.
- **Connexion limitée** (`core/login_throttle.py`) : après `LOGIN_MAX_ATTEMPTS`
  échecs en `LOGIN_WINDOW_SECONDS`, le compte reçoit un 429 avec `Retry-After`.
  Une même adresse a droit à quatre fois plus d'échecs. Le compteur vit en
  mémoire, ce qui suffit à un seul processus backend.
- **Mots de passe** : 8 caractères au moins, avec majuscule, minuscule et
  chiffre, et 72 octets au plus, la limite que lit bcrypt.
- **Fichiers envoyés** : `api/uploads.read_upload` applique `MAX_UPLOAD_SIZE`
  (413) et `ALLOWED_EXTENSIONS` (400). L'import de questionnaires a sa propre
  liste d'extensions.
- **Erreurs** :
  - les erreurs attendues sont des exceptions de `core/exceptions.py`, sans
    FastAPI, que `main.py` traduit en code HTTP. Leur message est écrit pour
    l'utilisateur ;
  - toute autre exception est journalisée avec sa trace et reçoit
    « Internal server error ». Ni le message d'un pilote ni une réponse
    d'OpenAI ne partent vers le navigateur ;
  - le dernier filet (`UnhandledErrorMiddleware`) est placé sous le middleware
    CORS, si bien que même une 500 porte les en-têtes CORS.
- **Documentation de l'API** : `/docs`, `/redoc` et `/openapi.json` ne sont
  servis que si `DOCS_ENABLED=true`.
- **Journaux** (`core/logging_setup.py`) : l'application écrit à partir de
  `LOG_LEVEL` (INFO par défaut), les bibliothèques tierces à partir de WARNING.
  Un utilisateur y est désigné par son identifiant, jamais par son adresse
  e-mail ou son nom.

## Cloisonnement par utilisateur

Règle : **l'administrateur voit tout**, les autres ne voient que leurs données.
Les fonctions communes sont dans **`services/authz.py`** : `user_is_admin`,
`filter_*_for_user` et `assert_*_access/ownership`.

- **Sessions** : visibles par leur créateur (`created_by`) ou la personne
  assignée (`assigned_to`).
- **Réponses et exécutions** : cloisonnées par la session qui les porte.
- **Types de DD** : privés (`created_by`). Ceux qui sont `is_system` ou sans
  créateur (`created_by IS NULL`) sont **partagés**. Tout utilisateur peut en
  créer. Seuls le propriétaire ou un administrateur peuvent les valider.
- **Vector stores** : la liste est filtrée par `created_by`, et l'accès aux
  fichiers est réservé au propriétaire.
  - **Stores disparus chez OpenAI** : une lecture ne supprime rien. Un store
    expiré ou introuvable apparaît avec le statut `expired` ou `missing`, et
    `POST /vector-stores/refresh` (le bouton Rafraîchir) le retire de la base
    avec ses assignations.
  - Le frontend (`entities/vector-store/lib/storeState.js`) marque ces stores
    (« Expired », « Gone ») sans chiffres, ne demande pas leurs fichiers, ne les
    propose plus à l'assignation, et signale sur la carte d'un type de DD un
    store assigné qui a disparu.
  - Les **assignations**, elles, se partagent : le store d'un collègue peut servir
    une session. La carte de la session lit donc le nom du store dans
    l'assignation (`vector_store_name`), et non dans la liste filtrée. Toute
    personne qui a accès à la session gère ses assignations.
  - **Portée d'une assignation** : `session_vector_stores.dd_type_id` désigne un
    type de DD précis, `NULL` toute la session.
    `processing.vector_store_ids_for` donne la priorité à l'assignation propre
    au type.
  - **Cache** : la liste des stores et les fichiers de chaque store sont gardés
    cinq minutes (ils interrogent OpenAI). Toute modification vide l'ensemble.
- **Sociétés** : filtrées par `created_by`. Celles sans créateur sont partagées.
- **`/processing`** (`start`, `pause`, `resume`, `progress`) : la session et le
  type de DD passent par les dépendances communes. Un type de DD privé d'un
  autre utilisateur ne peut pas être lancé (404).
- **Création d'une session** : seuls les types de DD que l'utilisateur voit
  sont retenus.
- Frontend : l'intercepteur de `shared/api/client.js` gère les réponses 403. Les pages
  `/dd-types` et `/questions` sont ouvertes à tous les rôles.

## Fonctionnalités

### Régénérer une réponse

`POST /answers/{id}/regenerate` (`api/routes/answers.py`,
`DDProcessor.regenerate_single_answer`) crée une nouvelle version au statut
`needs_review`. Le contexte envoyé au modèle comprend les réponses précédentes.
Le bouton se trouve sur chaque réponse (`AnswerCard`).

### Synthèses

`engine/summarizer.py` rédige d'abord un résumé par section, en parallèle, puis
une synthèse par type de DD (3 à 4 pages) à partir de ces résumés. Ce sont des
appels de rédaction pure, sans outils. Le stockage est dans `dd_summaries` et
l'API dans `api/routes/summaries.py` :
- `POST /summaries/session/{id}/dd/{ddType}/generate` ;
- `GET /summaries/session/{id}` ;
- `PUT /summaries/{id}`.

Une synthèse peut se générer sur des réponses partielles. La relancer écrase la
précédente.

**Via la Batch API.** `/v1/responses` est éligible au Batch, avec une remise de
50 %, mais sa seule fenêtre est de 24 heures. Or les synthèses se font en deux
étages : batcher les deux enchaînerait deux fenêtres. Seul l'étage des résumés
de section passe donc en Batch, et la synthèse finale reste un appel synchrone,
fait à la collecte.
- `openai_client` :
  - `build_summary_request_params` construit un corps de requête commun aux deux
    chemins, pour qu'ils ne divergent pas ;
  - `submit_summary_batch`, `get_batch`, `fetch_batch_texts` et
    `extract_output_text` gèrent le batch.

  ⚠️ L'ordre des lignes de sortie ne suit pas celui de l'entrée : le
  rapprochement passe par le `custom_id` (`section-{id}`).
- Endpoints :
  - `POST /summaries/.../generate/batch` lance le batch ;
  - `GET /summaries/.../batch` suit son état et fait la collecte ;
  - `POST /summaries/.../batch/cancel` l'annule.
- **La collecte se fait dans le GET**, que le frontend
  (`features/summaries/model/useSynthesis.js`) appelle toutes les 15 secondes. Une tâche de fond ne survivrait pas à un
  redémarrage, alors qu'un batch peut vivre 24 heures.
- Les fonctions de synthèse du moteur sont des coroutines qui appellent aussi
  la base et OpenAI de façon synchrone. Les routes sont donc des `def` : chacune
  lance sa coroutine dans sa propre boucle (`asyncio.run`), sur son thread du
  pool. En `async def`, elles bloquaient tout le serveur pendant l'appel à
  OpenAI, à chaque suivi.
- L'état est suivi dans `dd_summary_batches`, une ligne par session et par type
  de DD. Relancer remplace la ligne.
- **L'annulation** relit d'abord l'état chez OpenAI. Le statut stocké ne bouge
  qu'au suivi, et peut encore dire `in_progress` pour un batch terminé entre-temps :
  l'annuler jetterait des résultats déjà payés. Seul un batch qu'OpenAI déclare
  en cours est donc annulé, et les requêtes déjà terminées restent facturées.
- Le Batch n'a aucun délai garanti : un lot peut rester longtemps en file. Le
  chemin synchrone reste donc le bouton par défaut.
- Le moteur de questions, lui, ne peut pas passer en Batch : `web_search` y est
  refusé.

### Effort de raisonnement

`REASONING_EFFORT` (questions, `low`) et `SUMMARY_REASONING_EFFORT` (synthèses,
`medium`) sont deux réglages distincts :
- répondre, c'est extraire depuis des documents déjà retrouvés ;
- résumer, c'est de la pure rédaction, là où le raisonnement paie.

La remise Batch compense à peu près le surcoût de `medium`. Les tokens de
raisonnement sont facturés en sortie et s'imputent sur le plafond
`REASONING_MIN_OUTPUT_TOKENS`. Si une synthèse revient `incomplete`, c'est ce
plafond qu'il faut relever.

### Export PDF

`exports/pdf.py` produit un rapport à deux niveaux (le rendu du markdown est dans
`exports/markdown.py`, la lecture des sources dans `exports/sources.py`) :
- le corps : la synthèse de chaque type de DD ;
- les annexes : pour chaque section, son résumé, puis les questions, les réponses
  et les sources.

Sans synthèse, le rapport ne contient que le détail.
- La référence de la question (`A.01`) est remise devant son texte, à partir du
  `question_code`.
- **Charte** : la bannière, facultative, est lue dans `BRAND_BANNER_PATH` ; si le
  fichier manque, le rapport sort sans elle et un avertissement est journalisé.
  Les couleurs (`PDF_PRIMARY_COLOR`, `PDF_TEXT_COLOR`, `PDF_RULE_COLOR`) et la
  mention de pied de page (`PDF_FOOTER_NOTICE`) viennent aussi de la
  configuration.
- La fonction renvoie des octets ; la route construit la réponse HTTP.
- **Tableaux markdown larges** : chaque colonne reçoit d'abord un minimum
  (`_COL_MIN_POINTS`). Si le tableau ne tient pas, la marge intérieure est
  réduite. Au-delà d'environ 40 colonnes, il est écrit en lignes de texte.
- La règle horizontale markdown (`---`) ressort encore en clair.

Il n'y a pas d'export Excel. L'export CSV de la page de revue est fabriqué dans
le navigateur.

### Tableau de bord

`GET /api/dashboard/sessions` (`api/routes/dashboard.py`) renvoie en un appel tout ce
qu'affiche le tableau de bord, en environ huit requêtes groupées quel que soit
le nombre de sessions.
- Il est **en lecture seule** : l'état des batchs est lu dans
  `dd_summary_batches`, jamais via le GET batch, qui appelle OpenAI.
- La mise en forme est faite par la fonction pure `build_dashboard_rows`, testée
  par `tests/test_dashboard.py`.
- Le tableau se rafraîchit toutes les 15 secondes, **seulement** si un traitement
  ou un batch est en cours.
- Signal « bloqué ? » : une exécution `in_progress` sans nouvelle réponse depuis
  10 minutes.
- **« À relire »** compte les réponses actuelles non approuvées, hors échec
  (`completed`, `needs_review`, `draft`, `rejected`). Une réponse neuve du
  modèle est `completed`, pas `needs_review`.

## Format d'import des questionnaires

Le parser est `services/file_parser.py`, et un exemple fictif se trouve dans
[`examples/example_questionnaire.json`](../examples/example_questionnaire.json).
Les vrais questionnaires restent dans `questionnaires/`, ignoré par git.

```json
[
  {
    "section": "Titre de la section",
    "description": "Facultatif : le thème, transmis au modèle avec le titre",
    "questions": [
      "Une question en texte simple",
      {"ref": "A.01", "text": "Texte de la question", "context_prompt": "Où chercher"}
    ]
  }
]
```

- Une question est soit une **chaîne**, soit un **objet**. La forme objet garde
  la référence et les sources dans leurs propres champs.
- Le fichier Excel ou CSV a deux colonnes, section puis question, avec une ligne
  d'en-tête ; la section n'est écrite que sur sa première ligne.
- `POST /dd-types/import` crée **toujours** un nouveau type de DD.

### Codes des sections et des questions

`services/question_codes.py` :
- une section prend la **lettre de sa position** : A, B… Z, puis AA, AB… ;
- une question prend **la lettre de sa section et son rang** : `A.01`, `A.02` ;
- si le fichier JSON donne une **référence** (`ref`, la numérotation du
  fournisseur du questionnaire), elle devient le code. Une référence qui
  apparaît deux fois dans le fichier est ignorée : ces questions prennent un
  code de rang, et aucun code ne se répète dans un questionnaire ;
- une section ou une question créée à l'écran prend la lettre ou le rang
  suivant ;
- les codes ne sont uniques **qu'au sein d'un questionnaire** : chacun a son
  `A.01`. Rien ne retrouve une question par son code (tout passe par son
  identifiant), mais filtrer des réponses par section demande aussi le type de
  DD, et l'export suit l'ordre du questionnaire, pas celui des codes ;
- la base garantit cette unicité (une section par code dans son type de DD,
  une question par code dans sa section) : un code déjà pris donne un 409 ;
- le code est la référence affichée : par le badge de l'écran
  (`entities/dd-type/lib/questionCode.js`), devant la question dans l'export PDF, et par
  `scripts/update_questionnaire.py` pour l'alignement. Les trois lisent aussi
  l'ancienne forme, `A.01-_96323997` (référence, horodatage et nombre
  aléatoire).

### Scripts

La commande d'administration se lance depuis `backend/` :
`uv run python -m app.cli --help`. Elle ne compte pour l'instant que
`create-admin`.

Les scripts se lancent aussi depuis `backend/` : `uv run python scripts/<script>.py`.

- `xlsx_to_questionnaire.py` : convertit un classeur de questionnaire en JSON
  d'import.
  - Les colonnes sont lues **par nom d'en-tête**, car deux classeurs n'ont pas
    forcément les mêmes. La référence va dans `ref`, et les documents à consulter
    dans `context_prompt`.
  - Le script ajoute aussi une ligne `Level:` par question, dérivée du thème par
    la table `MANAGEMENT_COMPANY_THEMES`, en tête du fichier.
- `import_questionnaire.py <fichier.json> <CODE> <nom> [id_propriétaire]` : crée
  un type de DD sans passer par HTTP. Il utilise le même parser que l'import de
  l'API. Sans propriétaire, le type est partagé.
- `update_questionnaire.py <fichier.json> <CODE> [--apply]` : c'est la voie de
  ré-import.
  - Il réécrit les textes en place, en gardant les identifiants et les codes. Il
    est en lecture seule sans `--apply`.
  - Il refuse d'écrire si la structure diverge (sections, titres, effectifs,
    références), ou si des réponses existent, sauf avec `--answered`.
  - Il remplit `context_prompt` quand il est vide, mais ne l'écrase jamais : la
    saisie d'un analyste prime sur un fichier.
- `audit_integrity.py [--all]` : liste, en lecture seule, les lignes qui
  violent les règles de la migration `0002`, avec leurs identifiants, et dit
  ce que la migration en fait : elle corrige les unes et s'arrête devant les
  autres, qui demandent une décision (code de sortie 1). À lancer avant de
  migrer une base qui a des données.

## Frontend

### Design system

- **Thème** : `data-theme="light|dark"` sur `<html>`, posé avant le premier
  affichage par un script en ligne dans `index.html`. La préférence est stockée
  dans `DD_THEME` (`light`, `dark` ou `system`). `shared/lib/theme/ThemeContext.jsx`
  expose `mode`, `resolvedTheme`, `setMode`, `darkMode` et `toggleDarkMode`.
- **Les couleurs sont des variables CSS**, déclarées dans `src/app/styles/index.css` (un bloc
  par thème) et exposées en classes par le bloc `@theme inline` du même
  fichier (Tailwind 4, sans fichier de configuration JavaScript). `inline` :
  chaque classe porte sa valeur, si bien qu'une classe et une variable de même
  nom ne se masquent pas (`bg-bleu` est le bleu fixe de la marque,
  `var(--color-bleu)` suit le thème). L'opacité fonctionne
  (`bg-accent-blue/10`). Les classes maison sont des `@utility`.
  - Les tokens : `bg-surface`, `bg-surface-bg`, `bg-surface-hover`,
    `text-content(-secondary|-muted|-inverse)`, `border-border`,
    `theme-success|warning|error` (avec `-bg` et `-border`),
    `accent-blue|green|deep|gold`, `primary-dark` et `bleu-atlantis`.
  - **Règle : aucune couleur de la palette Tailwind (gray, blue…) et aucune
    variante `dark:`.** Un token suit les deux thèmes tout seul.
- **Classes maison** (`src/app/styles/index.css`, dans `@layer components`, donc
  surchargeables par les utilitaires) : `eyebrow`, `form-input`, `form-surface`,
  `pill-action`, `alert-*`, `live-indicator`, `hairline-gradient`, `rail-accent`,
  `side-gradient(-2)`, `gradient-grey-border-hover`, `analysis-link`,
  `modal-backdrop`, `navbar-spacing` et `bg-auth`.
  - `input-gradient-border` ne se combine jamais avec une classe
    `border-<couleur>`, car il lui faut sa bordure transparente.
- **Recettes partagées** : `shared/ui/styles.js` (`pageHeader`,
  `sectionHeader`, `panel`, `tableStyles`, `modalStyles`, `field`, `tabs`, `menu`,
  `emptyState`). Ce sont des chaînes de classes, pas des composants.
- **Statuts** :
  - `shared/lib/status/statusStyles.js` est la **seule** correspondance entre un statut et son
    ton (neutral, info, warning, success, error, brand). `Badge` s'y branche.
  - Les libellés sont dans `shared/lib/status/statusLabels.js`.
  - Le statut d'une session est calculé dans `entities/execution/lib/executionStatus.js`
    (`getSessionStatus`, `getSessionProgress`), partagé par le tableau de bord et
    la page de session.
  - `under_review`, `validated` et `finalized` sont des états **terminaux**
    (`FINISHED_STATUSES`).
- **Composants** :
  - `Button` : primary (bleu nuit plein), secondary (contour), ghost, danger et
    success ; sans enfant, c'est un bouton-icône. Ne pas lui ajouter de classes
    de couleur : l'ordre des feuilles de style déciderait alors du gagnant. Il
    répond à l'appui (pointeur enfoncé, pas relâché) par une légère réduction
    (`motion-safe:active:scale-[0.97]`) ; `pill-action` et les tuiles
    cliquables aussi.
  - Menus : ils naissent du bouton qui les ouvre (`origin-top-right
    animate-scale-in`).
  - `LoadingSpinner` : en tailles lg et xl, le logo traversé par un reflet.
  - `Modal` : se ferme avec Échap, la croix ou un clic à côté. C'est la seule
    fenêtre de l'application : il n'y a plus de fenêtre faite à la main.
  - Confirmations : `const confirm = useConfirm()` (`shared/lib/confirm`),
    puis `await confirm({ title, message, confirmLabel, danger })`, qui rend
    `true` ou `false`. Jamais `window.confirm`.
  - `Input` (libellé, icône, aide, erreur reliées au champ) et `PasswordInput`
    (le même, avec un bouton pour afficher le mot de passe).
  - Dans `shared/ui/` : `PageHeader`, `StatTile`, `EmptyState`,
    `SearchInput`, `StatusBadge` et `MiniProgressBar`.
- **Tranches** : une page assemble des widgets et des features, et garde au plus
  l'état de la page (l'onglet, l'élément ouvert). Les features : `auth`,
  `session-create`, `session-actions`, `dd-run-control`, `answer-review`,
  `summaries`, `questionnaire-edit`, `dd-type-admin`, `vector-store-manage`,
  `vector-store-assign`, `user-admin` et `theme-toggle`. Les widgets :
  `app-layout`, `sessions-overview` (tableau de bord), `dd-run-card`,
  `session-progress`, `answers-board`, `questionnaire-tree` et
  `vector-store-browser`.
- **Gabarit** : toutes les pages utilisent `pageLayout.container` (`max-w-7xl`) et
  l'en-tête `PageHeader` (fil d'Ariane, titre, actions à droite). Les détails
  techniques (codes, identifiants, tokens) n'apparaissent qu'au survol (`title`).
- **Logo** : `public/logo-white.svg` et l'icône `public/icon.svg`.
- **Charte** (skill `apple-design`, 4.4) :
  - **police du système** (`system-ui` : Segoe UI sous Windows), rien à
    télécharger ;
  - **interlettrage selon la taille** : négatif sur les grands textes (titres,
    chiffres des tuiles : `tracking-tight`), léger sur les petits libellés en
    capitales (0,06 à 0,08 em, jamais plus) ;
  - **barre de navigation** en matière translucide (`nav-bg` : surface à 72 %,
    flou et saturation), la page défile dessous ;
  - **confirmation** pour ce qui ne se défait pas seulement (supprimer, valider
    un type de DD) : revenir à une version n'en demande plus, car l'ancienne
    reste dans l'historique.
- **Accessibilité** (section 12 de `index.css`, hors couches) : l'application
  suit les réglages du système.
  - **Réduire les animations** : rien ne bouge (fenêtres et menus en fondu,
    transitions instantanées, ni appui animé, ni reflet, ni pulsation).
  - **Réduire la transparence** : surfaces pleines, sans flou.
  - **Contraste élevé** : bordures et textes secondaires renforcés (tokens
    redéfinis par thème).
  - Un **changement de thème** s'adoucit sur un quart de seconde
    (`.theme-changing`, posée par `shared/lib/theme` le temps du changement),
    sauf animations réduites.
- ⚠️ Ne jamais poser `filter`, `transform`, `backdrop-filter` ou `isolation` sur un
  conteneur de page. `Modal` (`fixed z-50`) passerait alors sous la barre de
  navigation.

### Affichage

- **Ne jamais afficher une valeur dont la source n'existe plus, et ne jamais
  couper du contenu en silence.**
- `AnswerCard` anime `grid-rows-[0fr]→[1fr]` plutôt qu'un `max-h` plafonné, qui
  coupait les longues réponses. Les tableaux markdown sont enveloppés dans un
  conteneur `overflow-x-auto` (`MARKDOWN_COMPONENTS`).
- La page des réponses demande `limit=1000` (le plafond du serveur) : sans
  cela, le serveur n'en renvoie que 100.
- Les tuiles d'une carte de DD (`widgets/dd-run-card/ui/RunStatus.jsx`) :
  - le temps écoulé se mesure sur les horodatages des réponses ;
  - les tokens ne comptent que les versions `is_current` ;
  - la troisième tuile compte les réponses appuyées sur les documents.

## Dépannage

- **« Internal server error »** : le message est volontairement générique. La
  trace complète est dans la console d'uvicorn.
- **Le démarrage échoue sur « Invalid configuration »** : le message liste les
  variables manquantes ou invalides. Voir `.env.template`.
- **Un traitement reste en `in_progress` après un redémarrage** : le relancer avec
  « Reprendre ».
- **Une synthèse revient `incomplete`** : relever la constante
  `REASONING_MIN_OUTPUT_TOKENS` de `engine/openai_client.py`.

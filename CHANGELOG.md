# Journal des changements

## Non publié

### Déploiement sur Azure ou AWS (Terraform)

- **`infra/azure/`** déploie l'application sur Azure, en services managés :
  Container Apps pour les trois conteneurs (seul le proxy est public, en
  HTTPS), PostgreSQL Flexible Server privé, Key Vault, Container Registry,
  identité managée, réseau virtuel, Log Analytics.
- **`infra/aws/`** fait de même sur AWS : ECS Fargate dans des sous-réseaux
  privés, un load balancer en HTTPS (avec un domaine et son certificat), RDS
  PostgreSQL, Secrets Manager, ECR, Cloud Map, CloudWatch.
- Chaque dossier a son README : les commandes dans l'ordre, de la création du
  stockage de l'état jusqu'au premier administrateur, puis les mises à jour.
  La clé OpenAI se dépose à la main et ne passe jamais par Terraform. Rien
  n'est déployé sans `terraform apply`.
- La CI vérifie le code Terraform des deux dossiers à chaque pull request.
- **Le proxy** devient un modèle rendu au démarrage, pour servir dans Docker
  comme dans les deux clouds :
  - **il retrouve les services à chaque requête.** Avant, il gardait leur
    adresse de départ : après une mise à jour qui recréait le backend, il
    répondait en erreur 502 jusqu'à son propre redémarrage ;
  - **il lit l'adresse du client derrière l'entrée d'un cloud**, sans
    qu'un client puisse la choisir ;
  - **il a son propre contrôle de santé** (`/healthz`).

### README et ménage

- Le README commence par un guide de lancement pas à pas : ce qu'il faut,
  la configuration (avec la génération des secrets sous Linux, macOS et
  Windows), le démarrage, le premier administrateur, une première due
  diligence et les problèmes courants.
- Les scripts n'ajoutent plus `backend/` au chemin de Python avant d'importer
  l'application : uv l'installe comme paquet. Leurs 9 marqueurs `# noqa: E402`
  disparaissent, avec l'exception correspondante de ruff.
- `.git-blame-ignore-revs` pointe vers les commits de formatage actuels (backend
  et frontend). Il nommait un commit disparu au nettoyage de l'historique.

### Docker Compose

- **L'application se lance avec Docker** : `cp .env.template .env`, remplir
  trois valeurs, puis `docker compose up -d --build`. Il ne faut plus installer
  ni Python, ni Node, ni PostgreSQL.
- Quatre services : un **proxy** nginx, seul point d'entrée (port 8080), devant
  le **frontend** (fichiers statiques), le **backend** (qui applique les
  migrations à chaque démarrage) et **PostgreSQL 17**. La base et le backend
  ne sont pas joignables depuis la machine.
- Le proxy porte les règles du trafic : 110 Mo par envoi, 10 minutes pour les
  appels qui attendent OpenAI, en-têtes de sécurité. L'adresse du client qu'il
  transmet ne peut pas être choisie par le client : les limites de connexion
  par adresse IP tiennent.
- Le README décrit le premier démarrage, la création du premier
  administrateur, les journaux, la mise à jour, la sauvegarde et la
  restauration de la base, l'accès à la base depuis la machine et la bannière
  des PDF.
- Les versions des images sont figées (`VERSION.md`).
- La CI démarre toute l'application à chaque pull request et s'en sert à
  travers le proxy, jusqu'à créer un administrateur et se connecter.

### Moteur de réponses repris

- **Une question en échec affiche un message écrit pour l'utilisateur**, au
  lieu du texte brut d'OpenAI. Par exemple : « OpenAI rate limit reached. Use
  Resume in a few minutes. » Le détail reste dans les journaux du serveur.
- **Une question coûte au plus 3 appels à OpenAI**, contre 9 auparavant : le
  SDK ne relance plus de lui-même, seul le moteur le fait. Il attend le délai
  qu'OpenAI demande en cas de limite de débit, et ne relance pas ce qu'un
  nouvel essai ne réglerait pas (requête refusée, clé refusée). `retry_count`
  compte les vraies relances.
- **Les erreurs sont classées par leur type**, et non plus en cherchant des
  mots dans leur texte. Un message contenant « invalid » n'arrête plus les
  relances, et un dépassement de contexte n'est plus relancé pour rien.
- **Une clé ou un quota refusé arrête le traitement dès la première
  question**, au lieu d'échouer sur chacune.
- **Une question s'écrit en une seule transaction** : la réponse brute, ses
  messages, l'ancienne réponse mise de côté, la nouvelle et son historique.
  Une panne au milieu ne laisse plus de question sans réponse courante.
- **Démarrage et reprise passent par la même boucle**, et le statut final se
  décide à un seul endroit. Une erreur fatale termine toujours le traitement
  `failed` (un démarrage le remettait à `not_started`). Une pause cliquée
  juste après « Start » n'est plus écrasée par le démarrage du traitement.
- **Une régénération qui échoue côté OpenAI** répond par un message lisible
  (502) au lieu d'une erreur 500.
- **Les synthèses** : le module est synchrone (les routes lançaient des
  coroutines qui appelaient la base de façon synchrone). Seuls les appels des
  résumés de section partent en parallèle, dans des threads, et la base reste
  dans le thread de la requête.
- La date d'expiration d'un vector store porte son fuseau (UTC).
- Le moteur est vérifié par mypy, et ses journaux passent leurs valeurs en
  arguments. Un test fige les paramètres envoyés à OpenAI pour une question.

### Colonnes mortes et copies (migration 0003)

- **On ne peut plus supprimer une session pendant un traitement**, ni une
  fois terminée. La garde existait, mais elle lisait un statut de session qui
  restait à « created » pour toujours : elle ne se déclenchait jamais, et la
  tâche de fond continuait d'écrire sur des lignes supprimées. Le statut
  d'une session se lit désormais sur ses exécutions, côté serveur comme dans
  l'interface. Si le serveur refuse, son message s'affiche.
- La colonne `dd_sessions.status` disparaît, avec le champ `status` des
  réponses `/session/…` et le filtre `status` de la liste des sessions.
- Les types de DD d'une session passent dans une table de liaison
  (`session_dd_types`). L'API renvoie `dd_types: [{id, code, name}]`, dans
  l'ordre choisi à la création, au lieu de `dd_types_json`. Un type renommé
  apparaît sous son nouveau nom, et un type qu'une session a choisi ne peut
  plus être supprimé (409).
- Supprimer une question ou une section qui a des réponses renvoie un 409,
  au lieu d'une erreur 500 sur la clé étrangère.
- Le score de confiance disparaît : la colonne, son champ dans l'API et
  `average_confidence` dans les statistiques de la page de revue. Il ne
  mesurait rien (une valeur fixe de 0,8, puis plus rien) et valait toujours 0
  en moyenne.
- `is_verified` disparaît des comptes et `validator_id` des exécutions : rien
  ne les remplissait.

### CI : les tests aussi sur PostgreSQL

- La CI relance toute la suite de tests sur son PostgreSQL jetable, avec un
  schéma créé par les migrations, comme en production. Les tests
  restaient jusqu'ici sur SQLite, qui ne vérifie ni les index partiels, ni
  les fuseaux horaires, ni JSONB. En local, rien ne change.
- Des tests propres à PostgreSQL vérifient que les index uniques sont bien
  partiels, que les contraintes `CHECK` refusent un statut inconnu et que les
  dates portent leur fuseau.
- Un test en échec apparaît en annotation de la pull request.
- Les sociétés, les synthèses et les assignations de vector stores sont
  listées dans un ordre stable, et les réponses créées au même instant aussi :
  PostgreSQL ne garantit aucun ordre sans `ORDER BY`.

### Intégrité de la base (migration 0002)

- **La base garantit elle-même ce que le code supposait** : une seule
  exécution par session et type de DD, au plus une réponse courante par
  question, une synthèse par section et une seule synthèse globale, une
  assignation de vector store par portée (et le type de DD assigné existe),
  des codes de section et de question uniques. Jusqu'ici, deux clics ou deux
  requêtes simultanées pouvaient créer des doublons.
- **Deux clics ne lancent plus deux traitements.** « Resume » sur un
  traitement déjà en cours le relançait une seconde fois en parallèle ; c'est
  désormais refusé (« already in progress »). Démarrer, mettre en pause et
  reprendre changent le statut d'un seul coup, sous condition.
- Un traitement long qui répond toujours n'est plus pris pour « bloqué » au
  bout de 10 minutes : il ne l'est que si aucune réponse n'a été écrite
  depuis 10 minutes. « Resume » reprend un traitement bloqué, une seule fois.
- Un code de section ou de question déjà pris renvoie un **409** (au lieu
  d'un 400), même quand une autre requête l'a pris au même moment.
- Aucun booléen, statut, compteur ou date de création ne peut plus être NULL,
  et la base pose elle-même les valeurs par défaut. Chaque statut est vérifié
  par une contrainte `CHECK`, le rôle d'un utilisateur aussi.
- Les statuts des réponses sont stockés par leur valeur, en minuscules
  (`needs_review`), comme les autres. L'API ne change pas : elle renvoyait
  déjà les valeurs.
- Envoyer `null` pour `is_active` ou `order_index` d'un type de DD laisse le
  champ tel quel, au lieu de le vider.
- **Avant de migrer une base qui a des données** :
  `uv run python scripts/audit_integrity.py` (depuis `backend/`, en lecture
  seule) liste les lignes en cause. La migration corrige les doublons et les
  NULL. Elle s'arrête, sans rien changer, devant ce qui demande une décision :
  exécutions en double, réponses sans exécution ou sans question, codes en
  double, statut ou rôle inconnu.

### CI : migrations vérifiées sur PostgreSQL

- La CI joue les migrations sur un PostgreSQL 17 jetable : `alembic upgrade
  head`, `alembic check` (les migrations correspondent aux modèles), une
  descente complète puis une remontée, et la comparaison de `db/schema.sql`
  avec un script régénéré. Jusqu'ici, rien ne les exécutait : les tests créent
  leurs tables sur SQLite.

### Simplifications

- **Plus d'inscription libre.** La page `/register` et la route
  `POST /auth/register` disparaissent : n'importe qui pouvait se créer un
  compte sur un outil interne. Un administrateur crée désormais les comptes
  depuis User Management (« Create user ») : nom, identifiant, e-mail, rôle,
  et un mot de passe provisoire qu'il transmet, que l'utilisateur change dans
  son profil (`POST /admin/users`).
- L'entrée « Questions » du menu disparaît : un questionnaire s'ouvre depuis
  son type de DD (bouton « Questions »), et l'entrée « DD Types » reste
  allumée sur sa page.
- Le tableau « User Analytics » du tableau de bord disparaît.
- Les anciennes adresses `/dashboard`, `/sessions` et `/answers` ne
  redirigent plus : elles mènent à la page « introuvable ».

### Interface tout en anglais

- Ce qui restait en français passe en anglais, comme le reste de
  l'interface : l'onglet et les messages de la synthèse, la fenêtre de
  régénération d'une réponse, les éditeurs de question et de section, les
  onglets « Answers » et « Synthesis ».
- La raison enregistrée sur une version régénérée est en anglais
  (« Regenerated by the AI… ») ; les versions déjà enregistrées gardent la
  leur.
- Restent en français, volontairement, car ce sont des contenus et non de
  l'interface : les consignes données au modèle (et donc la langue des
  synthèses) et le rapport PDF.
- Les libellés de la fenêtre de régénération sont reliés à leurs champs.

### Frontend : charte apple-design

- La police est celle du système (Segoe UI sous Windows) : Roboto n'est plus
  téléchargé avec l'application.
- L'interlettrage suit la taille : titres et grands chiffres plus serrés,
  libellés en capitales bien moins espacés (0,06 à 0,08 em au lieu de 0,1 à
  0,22 em).
- Boutons, pastilles et tuiles cliquables répondent dès l'appui. Les menus
  (compte, export) naissent du bouton qui les ouvre.
- La barre de navigation est une matière translucide, floutée, sous laquelle
  la page défile ; elle porte le nom « Easy Diligence » (au lieu de
  « DD Automation »).
- L'application suit les réglages d'accessibilité du système : animations
  réduites (plus rien ne bouge), transparence réduite (surfaces pleines),
  contraste élevé (bordures et textes secondaires renforcés). Un changement de
  thème s'adoucit au lieu de basculer d'un coup.
- Revenir à une version d'une réponse ne demande plus de confirmation : rien
  n'est perdu, l'ancienne version reste dans l'historique.
- Le menu du compte affiche le nom de l'utilisateur : il lisait des champs
  (`first_name`, `last_name`) qu'un compte n'a pas, et restait vide.
- La configuration de Tailwind passe dans le CSS (`@theme`) :
  `tailwind.config.js` disparaît. Vérifié : les 36 captures étaient identiques
  avant que la charte ne change quoi que ce soit.

### Frontend : Tailwind 4

- Tailwind 3 → 4, par l'outil officiel de migration. Les pages sont restées
  identiques au pixel près : 36 captures comparées avant et après, en thème
  clair et sombre.
- Une seule différence visible, voulue : le pied des fenêtres (création d'un
  type de DD, d'une question, d'une section, d'un vector store) touche enfin
  le bas de la fenêtre. Tailwind 3 annulait sa marge et laissait une bande
  blanche sous les boutons.
- `npm audit` : 0 faille, outils de build compris. Les 2 alertes venaient de
  `@tailwindcss/typography`, qui fige une ancienne version de
  `postcss-selector-parser` ; un `overrides` de `package.json`, limité à ce
  paquet, la remplace par la 6.1.6, corrigée (même version majeure).
- `autoprefixer` n'est plus nécessaire et disparaît.

### Mot de passe oublié, vector stores disparus, serveur non bloqué

- Le lien de l'e-mail « mot de passe oublié » mène à une page qui existe
  (`/reset-password`) : on y choisit son nouveau mot de passe, puis on se
  connecte avec. Un lien expiré ou déjà utilisé le dit, et explique comment en
  redemander un. Le lien menait auparavant à une page 404.
- La demande de lien répond aussi vite que l'adresse existe ou non : l'e-mail
  part après la réponse, et le temps de réponse ne trahit plus les comptes.
- Un vector store expiré ou supprimé chez OpenAI est marqué « Expired » ou
  « Gone », sans les « 0 fichier » qui le faisaient passer pour un store vide.
  Sa page explique que ses documents sont perdus et n'essaie plus d'en lister
  les fichiers (ce qui finissait en erreur). Il n'est plus proposé à
  l'affectation, et la carte d'un type de DD qui l'utilise le signale.
- Le bouton « Refresh » des vector stores dit qu'il retire les stores disparus
  chez OpenAI, et combien il en a retiré.
- Le serveur ne se bloque plus pendant le suivi d'un batch de synthèse (appelé
  toutes les 15 secondes) ni pendant une génération de synthèse : ces routes
  appelaient OpenAI depuis la boucle de l'application, et toutes les autres
  requêtes attendaient.

### Frontend : pages découpées (2/2)

- La gestion des utilisateurs pagine et cherche côté serveur. Elle chargeait
  les 100 premiers comptes et cherchait parmi eux : le 101e n'apparaissait
  jamais. La recherche du serveur couvre aussi la société.
- Une seule sorte de fenêtre, `Modal` : les six fenêtres faites à la main
  (mot de passe oublié, changement de mot de passe, fiche et suppression d'un
  utilisateur, type de DD, question) se ferment maintenant toutes avec Échap.
  La suppression d'un utilisateur passe par la confirmation commune.
- Les formulaires d'inscription et de changement de mot de passe disent la
  règle du mot de passe d'avance, et signalent chaque champ fautif à côté du
  champ. Le profil n'envoie plus le rôle (le serveur l'ignorait).
- On peut déposer des fichiers dans la fenêtre d'envoi d'un vector store, comme
  elle l'annonçait. Les fichiers en échec restent affichés, et la fenêtre reste
  ouverte pour les renvoyer ou les retirer ; elle annonçait aussi une limite de
  10 Mo que le serveur n'applique pas (100 Mo par défaut).
- Retirés : la case « Remember me » et la case « Terms and Conditions » (lien
  vide), qui n'avaient aucun effet, et le bouton « Edit user », qui affichait
  « coming soon ».
- Le choix d'une catégorie de type de DD ne range plus « Credit » ou
  « Equity » parmi les types techniques (le mot « it » était cherché dans tout
  le nom).
- Tableau de bord, création de session, types de DD, utilisateurs, profil,
  connexion, inscription et vector stores sont découpés en widgets et en
  features ; aucun fichier du frontend ne dépasse 250 lignes (neuf dépassaient
  400 lignes).
- `npm run lint` passe sans aucun avertissement, et la CI le lance.

### Questionnaire d'exemple

- Le questionnaire d'exemple est remplacé par un questionnaire fictif,
  `examples/example_questionnaire.json` (code `EXAMPLE`) : 18 questions en 6
  sections (identité du fonds, équipe, stratégie, risques, opérations, frais et
  durabilité). Chaque section a une description et chaque
  question une consigne « où chercher ». Un test vérifie qu'il s'importe.
- Les commentaires du code et les tests ne nomment plus de questionnaire réel.
  Le mot « snapshot » ne sert plus à choisir l'icône d'un type de DD : un type
  ainsi nommé prend l'icône par défaut.

### Frontend : pages découpées (1/2)

- Les confirmations s'ouvrent dans une fenêtre de l'application, et non plus
  dans le `confirm()` du navigateur. Le message nomme ce qui va disparaître ;
  Échap, la croix ou un clic à côté valent « Annuler ».
- La page des réponses charge toutes les réponses d'un type de DD. Elle n'en
  recevait que 100 (la taille de page par défaut du serveur) : au-delà, les
  suivantes manquaient sans aucun message.
- Choisir une section dans les filtres ne recharge plus la page : la requête
  envoyait un paramètre que le serveur ignorait. Après une régénération ou un
  retour à une version, les sections et les réponses ouvertes le restent.
- L'export CSV garde ses accents dans Excel (marque UTF-8 en tête de fichier).
- Le bouton « Sources » d'une réponse ne compte plus les sources qui n'ont
  rien à afficher (recherche de fichiers sans nom de fichier, recherche web
  sans lien), et l'éditeur ne les montre plus comme des lignes vides.
- La page d'une session, la carte d'un type de DD, la page des réponses et la
  synthèse sont découpées en widgets (`dd-run-card`, `session-progress`,
  `answers-board`) et en features (`dd-run-control`, `vector-store-assign`,
  `session-actions`, `answer-review`, `summaries`). La page d'une session passe
  de 648 à 198 lignes.

### Frontend : couches

- Le code est rangé en Feature-Sliced Design (`app`, `pages`, `widgets`,
  `features`, `entities`, `shared`), et le lint refuse un import qui remonte
  les couches ou passe d'une tranche à sa voisine.
- Une seule mise en page pour toutes les pages, une page 404, et `/login`
  renvoie au tableau de bord quand on est déjà connecté.
- Une session expirée renvoie à la page de connexion sans recharger
  l'application.
- Les types de DD sont chargés une fois et partagés : la page d'une session en
  demandait la structure complète une fois par carte.

### Frontend : socle

- Le frontend appelle l'API en relatif, sur `/api` : plus d'URL propre à une
  machine. En développement, le serveur de Vite transmet ces appels au backend
  (`VITE_API_PROXY`, `http://localhost:8000` par défaut) ; `VITE_API_URL`
  disparaît.
- Vite 8, react-router 7 et ESLint 9 ; plus aucune faille connue dans le code
  livré au navigateur (18 avant, dont 14 « high »).
- L'authentification passe par le client HTTP commun. Un mot de passe erroné
  affiche le message de l'API au lieu de recharger la page.
- Supprimés : la modification des « attributs » d'un fichier de vector store
  (l'endpoint n'existait pas), les fichiers et appels d'API morts, et les
  dépendances inutilisées (`rehype-mermaid`, `react-dropzone`,
  `tailwind-scrollbar`).
- L'alias `@/` désigne `frontend/src`.

### Base de données

- PostgreSQL 17 remplace MySQL, via psycopg 3. La connexion se configure par
  `POSTGRES_*` ou `DATABASE_URL`.
- Les modèles passent en SQLModel.
- Alembic gère le schéma : la migration initiale crée toute la base, et
  `db/schema.sql` en donne le script SQL complet. Les anciens correctifs SQL
  appliqués à la main sont supprimés, et l'application ne crée plus ses tables
  au démarrage.
- Les transactions sont réelles : un `rollback()` annule désormais vraiment.
- Les clés étrangères sont indexées, et les statuts stockés en texte avec une
  contrainte de contrôle.
- Les adresses e-mail sont enregistrées et comparées en minuscules.
- Il n'y a pas de reprise des données de l'ancienne base MySQL.

### Outillage

- Le code du frontend est formaté par Prettier (`npm run format`), et la CI le
  vérifie (`npm run format:check`). Le formatage n'a rien changé au code livré
  au navigateur : le build est identique, octet pour octet.
- Le projet backend s'appelle `easy-diligence`, en version 0.1.0, et passe à
  Python 3.12.
- Les outils de développement sont dans le groupe `dev` de `pyproject.toml` :
  `uv sync` les installe, `uv sync --no-dev` les laisse de côté. Les extras
  inutilisés (monitoring, documentation) et les dépendances sans usage (celery,
  aiofiles, python-dateutil…) sont retirés.
- Ruff vérifie et formate le code (black est retiré) ; mypy vérifie les types,
  en mode permissif pour commencer.
- pytest 9 et pytest-asyncio 1.x.
- `.pre-commit-config.yaml` et une intégration continue GitHub Actions.
- `.gitattributes` fixe les fins de ligne (LF).
- `pip-audit` ne trouve plus aucune faille connue, outils de développement
  compris.

### Tests

- La suite est réécrite : chaque test a sa propre base SQLite en mémoire, et
  `conftest.py` fournit les utilisateurs, les données de départ et de faux
  clients OpenAI. Les tests vides, en double ou devenus inutiles sont supprimés.
- Nouveaux tests : cloisonnement entre utilisateurs, sociétés, vector stores,
  moteur de réponses (démarrage, pause, reprise, question en échec), modèles,
  sécurité des jetons, connexion.
- La CI lance toute la suite.

### Corrections

- L'export Excel plantait pour toute réponse qui avait des sources.
- La modification d'un vector store échouait toujours.
- Après la modification d'un vector store, la liste montrait l'ancienne version
  pendant cinq minutes (cache).
- La page d'administration ne pouvait changer ni le rôle ni le statut d'un
  utilisateur (méthode HTTP erronée).
- L'export reprenait toutes les versions d'une réponse : une question
  régénérée apparaissait deux fois dans le rapport. Il ne garde plus que la
  version courante.
- Un administrateur ou la personne assignée à une session ne pouvaient pas en
  gérer les vector stores.
- Une nouvelle session pouvait inclure les types de DD privés d'un autre
  utilisateur. Un type de DD privé d'un autre ne peut plus être lancé.

- Supprimer un compte vidait le créateur de ses sessions et de ses sociétés :
  ses sociétés devenaient visibles de tous. Un compte qui possède des données
  ne se supprime plus, il se désactive.
- La recherche de la page d'administration ne cherchait que dans la page
  affichée, avec un total faux.
- Une section ajoutée après une première section prenait la même position
  qu'elle.
- Les sections et les questions arrivent dans l'ordre du questionnaire.

### Export

- Un seul export côté serveur : le rapport PDF. L'export Excel est supprimé ;
  l'export CSV de la page de revue reste.
- Les couleurs du rapport et sa mention de pied de page se règlent dans la
  configuration (`PDF_PRIMARY_COLOR`, `PDF_TEXT_COLOR`, `PDF_RULE_COLOR`,
  `PDF_FOOTER_NOTICE`).
- Le code de l'export est découpé : `exports/pdf.py`, `markdown.py`,
  `sources.py`.

### Modèles

- `schemas/` disparaît : chaque fichier de `models/` porte sa table et ce que
  l'API en lit et en renvoie. Les champs et leurs limites ne sont écrits
  qu'une fois, et l'API refuse maintenant ce que la base refuserait (longueur,
  position négative). Le schéma de la base ne change pas.
- La durée d'expiration choisie à la création d'un vector store est respectée
  (elle valait toujours 30 jours).

### Codes des questions

- Les sections sont lettrées par leur position (A, B…) et les questions
  numérotées dans leur section (A.01, A.02…), à l'import comme à la création à
  l'écran. La référence du fichier, quand il en donne une, reste le code. Les
  anciens codes (`A.01-_96323997`) sont toujours lus.
- Filtrer les réponses par section demande aussi le type de DD, et l'export
  suit l'ordre du questionnaire.

### Services

- La logique et les accès à la base passent dans `services/`, pour toutes les
  routes. Les routes ne font plus que lire la requête, appeler un service et
  répondre.
- Les routes sont des fonctions simples : une route asynchrone qui appelait la
  base ou OpenAI bloquait tout le serveur pendant l'appel.
- La session et le type de DD lus dans l'URL passent par deux dépendances
  communes, qui vérifient les droits.
- Lire la liste des vector stores ne supprime plus rien : un store disparu
  chez OpenAI apparaît comme `expired` ou `missing`, et le bouton Rafraîchir le
  retire.
- Supprimés, car en double : six variantes de l'historique d'une réponse
  (`with-history`, `versions/{v}`, `original`, `history/{v}/raw`,
  `by-execution`, `POST validate`) et `/dd-types/code/{code}`.

### Nettoyage

- Supprimés, car aucun écran ne les appelait et plusieurs plantaient : les
  endpoints `/executions` et `/documents`, la recherche dans un vector store et
  `/company/auth-test`, avec leurs schémas.
- Supprimés aussi : les méthodes sans appelant du client OpenAI et des
  utilitaires, et les invalidations de cache qui ne visaient aucune donnée
  mise en cache.
- Code Pydantic v2 partout (`ConfigDict`, `model_validate`, `model_dump`), et
  `datetime.utcnow()` remplacé.
- Les journaux de l'application sont configurés (`LOG_LEVEL`) : sous uvicorn,
  ses messages d'information étaient perdus.

### Structure du backend

Les fichiers sont rangés en `api/routes`, `core`, `engine`, `services` et
`exports`, sans changement de logique.

### Sécurité

- L'inscription ne peut plus choisir son rôle : un nouveau compte est toujours
  analyste. Le premier administrateur se crée avec
  `python -m app.cli create-admin`.
- `DATABASE_URL`, `OPENAI_API_KEY` et `JWT_SECRET_KEY` sont obligatoires, et
  l'application refuse de démarrer sans eux.
- Les jetons sont stockés hachés et rendus uniques, le jeton de rafraîchissement
  passe dans le corps de la requête, et le jeton de réinitialisation du mot de
  passe ne sert qu'une fois.
- La connexion est limitée après des échecs répétés.
- La taille et le type des fichiers envoyés sont vérifiés.
- Une erreur imprévue renvoie un message générique ; sa trace part dans les
  journaux.
- `/docs` est fermé par défaut (`DOCS_ENABLED`).
- Les deux WebSockets inutilisés sont supprimés.
- PyJWT et bcrypt remplacent python-jose et passlib ; FastAPI, Starlette,
  python-multipart, jinja2, cryptography et les dépendances qu'elles entraînent
  sont montés.

## 0.1.0 — 18/11/2026

Premier commit d'Easy-Diligence, sur un historique neuf.

- La documentation est réécrite : `README.md`, `docs/ARCHITECTURE.md` et
  `VERSION.md`. Les revues et analyses périmées sont supprimées, ainsi que les
  restes Docker et les scripts de mesure ponctuels.
- Toute la configuration est listée et commentée dans `.env.template`.
  `DATABASE_URL` devient obligatoire, et une `JWT_SECRET_KEY` vide est refusée.
- Les éléments de charte sont retirés : un logo neutre les remplace, et la
  bannière du rapport PDF devient facultative (`BRAND_BANNER_PATH`).
- Un questionnaire d'exemple est fourni dans `examples/`.

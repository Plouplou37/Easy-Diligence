# Déployer Easy Diligence sur AWS

Le code Terraform de ce dossier crée tout ce qu'il faut pour faire tourner
l'application sur AWS, en services managés. C'est l'équivalent d'`infra/azure/`,
au choix.

```
Internet ─HTTPS─► load balancer ─► proxy (ECS) ──/api──► backend (ECS) ──► RDS PostgreSQL
                                     └──── / ────► frontend (ECS)
```

| Ressource | Rôle |
| --- | --- |
| ECS sur Fargate | les trois conteneurs de `docker-compose.yml`, dans des sous-réseaux privés |
| Application Load Balancer | la seule entrée publique : il termine le HTTPS (certificat ACM) et transmet au proxy |
| RDS PostgreSQL 17 | la base, chiffrée, privée, sauvegardée automatiquement (7 jours par défaut) |
| ECR | les images, une par service |
| Secrets Manager | les secrets : l'URL de la base, la clé JWT, la clé OpenAI |
| Cloud Map | les noms internes (`backend.<…>.internal`), par lesquels le proxy joint les deux autres |
| VPC | deux zones ; sous-réseaux publics (load balancer, passerelle NAT) et privés (conteneurs, base) |
| CloudWatch Logs | les journaux des conteneurs |

Rien n'est déployé tant qu'on ne lance pas `terraform apply`. Les ressources
sont payantes : aux tailles par défaut, compter une centaine de dollars par
mois. La passerelle NAT, le load balancer et la base en font l'essentiel.

**Différence avec Azure : le HTTPS demande un nom de domaine.** AWS ne fournit
pas d'adresse HTTPS toute prête : il faut un domaine (par exemple
`dd.example.com`) et son certificat ACM. Sans eux, l'application répond en HTTP
sur l'adresse du load balancer, ce qui ne convient qu'à un essai : les mots de
passe y circuleraient en clair.

## Ce qu'il faut

- un compte AWS, et un utilisateur ou un rôle autorisé à créer ces ressources
  (IAM compris) ;
- **AWS CLI** v2, configurée (`aws configure` ou `aws sso login`), et le
  **Session Manager plugin** pour `aws ecs execute-command` ;
- **Terraform** 1.11 ou plus récent (version testée dans `VERSION.md`) ;
- **Docker**, sur la machine qui construit les images ;
- pour le HTTPS, un nom de domaine dont on peut modifier le DNS.

Toutes les commandes se lancent depuis ce dossier, `infra/aws/`. Les exemples
utilisent la région `eu-west-3` (Paris).

## Premier déploiement

### 1. Le bucket de l'état (une fois)

L'état de Terraform vit dans un bucket S3, à créer une fois. Son nom est
unique dans tout AWS : y mettre par exemple le numéro du compte.

```bash
BUCKET=easydiligence-tfstate-$(aws sts get-caller-identity --query Account --output text)
aws s3api create-bucket --bucket "$BUCKET" --region eu-west-3 \
  --create-bucket-configuration LocationConstraint=eu-west-3
aws s3api put-bucket-versioning --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

L'état contient des secrets (le mot de passe de la base, la clé JWT) : seuls
ceux qui déploient doivent avoir accès à ce bucket.

### 2. Le certificat (pour le HTTPS)

```bash
aws acm request-certificate --region eu-west-3 \
  --domain-name dd.example.com --validation-method DNS
```

ACM donne un enregistrement CNAME à créer dans le DNS du domaine
(`aws acm describe-certificate --certificate-arn <arn>`) ; le certificat est
validé quelques minutes après. Son ARN va dans `terraform.tfvars`.

### 3. Configurer

```bash
cp backend.hcl.example backend.hcl            # le bucket de l'étape 1
cp terraform.tfvars.example terraform.tfvars  # le tag des images, le domaine
terraform init -backend-config=backend.hcl
```

`backend.hcl` et `terraform.tfvars` sont ignorés par git.

### 4. Créer les dépôts d'images, puis y pousser les images

Les services ont besoin de leurs images dès leur création : les dépôts
viennent donc d'abord, seuls.

```bash
terraform apply -target=aws_ecr_repository.this
```

Puis les trois images, construites pour Linux x86-64 (même sur un Mac à puce
Apple), avec le tag de `terraform.tfvars` (`image_tag`) :

```bash
TAG=2026-11-20   # le image_tag de terraform.tfvars
REGISTRY=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.eu-west-3.amazonaws.com
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin "$REGISTRY"
for service in backend frontend proxy; do
  docker build --platform linux/amd64 -t "$REGISTRY/easy-diligence/$service:$TAG" ../../$service
  docker push "$REGISTRY/easy-diligence/$service:$TAG"
done
```

### 5. Tout créer

```bash
terraform apply
```

Compter une quinzaine de minutes : la base est la plus longue à créer. Au
démarrage, le backend applique les migrations.

### 6. Pointer le domaine

Dans le DNS du domaine, un enregistrement CNAME de `dd.example.com` vers
l'adresse du load balancer : `terraform output load_balancer_dns_name`.

### 7. Déposer la clé OpenAI

Terraform crée le secret avec une valeur d'attente, et ne voit jamais la vraie
clé :

```bash
aws secretsmanager put-secret-value \
  --secret-id "$(terraform output -raw openai_secret)" \
  --secret-string "<la clé OpenAI>"
```

Puis redémarrer le backend, qui relit ses secrets à son démarrage :

```bash
aws ecs update-service --cluster "$(terraform output -raw cluster)" \
  --service backend --force-new-deployment
```

### 8. Créer le premier administrateur

Un shell dans le conteneur du backend (ECS Exec), puis la commande de
création :

```bash
CLUSTER=$(terraform output -raw cluster)
TASK=$(aws ecs list-tasks --cluster "$CLUSTER" --service-name backend --query 'taskArns[0]' --output text)
aws ecs execute-command --cluster "$CLUSTER" --task "$TASK" \
  --container backend --interactive --command sh
# dans le conteneur :
python -m app.cli create-admin <adresse e-mail> "<Prénom Nom>"
```

La commande demande le mot de passe. L'application est à l'adresse donnée par
`terraform output url`.

## Mettre à jour

À chaque nouvelle version : pousser les images sous un nouveau tag (étape 4,
sans le `terraform apply -target`), mettre ce tag dans `terraform.tfvars`,
puis `terraform apply`. L'ancien backend s'arrête avant que le nouveau
démarre et applique les migrations : quelques instants d'indisponibilité de
l'API.

## Bon à savoir

- **Délai des requêtes** : le load balancer et le proxy laissent 600 secondes
  aux requêtes longues (régénération, synthèse rédigée en direct).
- **Un seul backend** : il reste à une tâche, toujours allumée. Un traitement
  en cours vit dans son processus : le partager entre tâches le couperait.
- **Une seule passerelle NAT**, dans la première zone : si cette zone tombe,
  les conteneurs ne joignent plus OpenAI. Une passerelle par zone coûte plus
  cher.
- **Bannière des PDF** : elle n'est pas montée ici. Il faudrait un volume EFS
  monté dans le backend, et `BRAND_BANNER_PATH` dans `backend_env`.
- **Les réglages du backend** (`.env.template`) passent par `backend_env` dans
  `terraform.tfvars`, jamais un secret : ceux-là vont dans Secrets Manager.
- **Tout supprimer** : la base est protégée contre la suppression. Mettre
  d'abord `deletion_protection = false` dans `database.tf` et faire un
  `terraform apply`, puis `terraform destroy`, qui garde un dernier
  instantané de la base (`<nom>-db-final`). Les secrets restent récupérables
  7 jours.

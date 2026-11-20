# Déployer Easy Diligence sur Azure

Le code Terraform de ce dossier crée tout ce qu'il faut pour faire tourner
l'application sur Azure, en services managés :

```
Internet ─HTTPS─► proxy (Container App, publique)
                    ├── /     ► frontend (Container App, interne)
                    └── /api  ► backend  (Container App, interne) ──► PostgreSQL (privé)
                                    └── secrets lus dans Key Vault
```

| Ressource | Rôle |
| --- | --- |
| Azure Container Apps | les trois conteneurs de `docker-compose.yml`. Seul le proxy est public, en HTTPS, sur une adresse `*.azurecontainerapps.io` |
| Azure Database for PostgreSQL Flexible Server 17 | la base, sans adresse publique, sauvegardée automatiquement (7 jours par défaut) |
| Azure Container Registry | les images, construites dans Azure (`az acr build`) : pas besoin de Docker sur le poste |
| Key Vault | les secrets : l'URL de la base, la clé JWT, la clé OpenAI |
| Identité managée | une identité pour les trois applications, qui tire les images et lit les secrets, sans mot de passe |
| Réseau virtuel | les applications et la base, la base n'étant joignable que depuis lui |
| Log Analytics | les journaux des conteneurs |

Rien n'est déployé tant qu'on ne lance pas `terraform apply`. Les ressources
sont payantes : aux tailles par défaut (la plus petite base, trois petits
conteneurs toujours allumés), compter quelques dizaines d'euros par mois, la
base en tête.

## Ce qu'il faut

- un abonnement Azure, avec le rôle **Owner** (ou **Contributor** et **User
  Access Administrator**) : Terraform y crée des attributions de rôles ;
- **Azure CLI** (`az`), connecté : `az login`, puis
  `az account set --subscription <id>` ;
- **Terraform** 1.11 ou plus récent (version testée dans `VERSION.md`).

Toutes les commandes se lancent depuis ce dossier, `infra/azure/`.

## Premier déploiement

### 1. Préparer l'abonnement (une fois)

Les fournisseurs de ressources utilisés doivent être enregistrés :

```bash
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.DBforPostgreSQL
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.OperationalInsights
```

L'état de Terraform vit dans un compte de stockage, à créer une fois. Son nom
est unique dans tout Azure : le changer au besoin (3 à 24 minuscules et
chiffres).

```bash
az group create --name rg-easydiligence-tfstate --location francecentral
az storage account create --name easydiligencetfstate \
  --resource-group rg-easydiligence-tfstate --location francecentral \
  --sku Standard_LRS --min-tls-version TLS1_2 \
  --allow-blob-public-access false --allow-shared-key-access false
az storage container create --name tfstate \
  --account-name easydiligencetfstate --auth-mode login
# Le droit d'y écrire, avec son propre compte :
az role assignment create --role "Storage Blob Data Contributor" \
  --assignee "$(az ad signed-in-user show --query id -o tsv)" \
  --scope "$(az storage account show --name easydiligencetfstate --query id -o tsv)"
```

L'état contient des secrets (le mot de passe de la base, la clé JWT) : seuls
ceux qui déploient doivent avoir accès à ce compte de stockage.

### 2. Configurer

```bash
cp backend.hcl.example backend.hcl            # les noms de l'étape 1
cp terraform.tfvars.example terraform.tfvars  # l'abonnement, le tag des images
terraform init -backend-config=backend.hcl
```

`backend.hcl` et `terraform.tfvars` sont ignorés par git.

### 3. Créer le registre, puis y construire les images

Les applications ont besoin de leurs images dès leur création : le registre
vient donc d'abord, seul.

```bash
terraform apply -target=azurerm_container_registry.this
```

Puis les trois images, construites par Azure à partir du dépôt, avec le tag de
`terraform.tfvars` (`image_tag`) :

```bash
REGISTRY=$(terraform output -raw registry)
TAG=2026-11-20   # le image_tag de terraform.tfvars
az acr build --registry "$REGISTRY" --image easy-diligence/backend:$TAG  ../../backend
az acr build --registry "$REGISTRY" --image easy-diligence/frontend:$TAG ../../frontend
az acr build --registry "$REGISTRY" --image easy-diligence/proxy:$TAG    ../../proxy
```

### 4. Tout créer

```bash
terraform apply
```

Compter une quinzaine de minutes : la base est la plus longue à créer. Au
démarrage, le backend applique les migrations.

### 5. Déposer la clé OpenAI

Terraform crée le secret avec une valeur d'attente, et ne voit jamais la vraie
clé :

```bash
az keyvault secret set --vault-name "$(terraform output -raw key_vault)" \
  --name openai-api-key --value "<la clé OpenAI>"
```

Puis redémarrer le backend, qui relit ses secrets :

```bash
BACKEND=$(terraform output -raw backend_app)
GROUP=$(terraform output -raw resource_group)
az containerapp revision restart --name "$BACKEND" --resource-group "$GROUP" \
  --revision "$(az containerapp show --name "$BACKEND" --resource-group "$GROUP" \
    --query properties.latestRevisionName -o tsv)"
```

### 6. Créer le premier administrateur

Un shell dans le conteneur du backend, puis la commande de création :

```bash
az containerapp exec --name "$BACKEND" --resource-group "$GROUP" --command sh
# dans le conteneur :
python -m app.cli create-admin <adresse e-mail> "<Prénom Nom>"
```

La commande demande le mot de passe. L'application est à l'adresse donnée par
`terraform output url`.

## Mettre à jour

À chaque nouvelle version : construire les images sous un nouveau tag (étape
3, sans le `terraform apply -target`), mettre ce tag dans `terraform.tfvars`,
puis `terraform apply`. Le backend applique les migrations en redémarrant.

## Bon à savoir

- **Délai des requêtes** : l'entrée d'Azure Container Apps coupe une requête
  après 240 secondes. Une synthèse rédigée en direct sur un très gros
  questionnaire peut dépasser ce délai : la rédiger alors en différé (Batch).
- **Un seul backend** : il reste à une instance, toujours allumée. Un
  traitement en cours vit dans son processus : une mise en veille ou un
  partage entre instances le couperait.
- **Nom de domaine** : l'application répond sur `*.azurecontainerapps.io`. Un
  domaine à soi, avec son certificat, s'ajoute à la Container App du proxy.
- **Bannière des PDF** : elle n'est pas montée ici. Il faudrait un partage
  Azure Files monté dans le backend, et `BRAND_BANNER_PATH` dans `backend_env`.
- **Les réglages du backend** (`.env.template`) passent par `backend_env` dans
  `terraform.tfvars`, jamais un secret : ceux-là vont dans Key Vault.
- **Tout supprimer** : `terraform destroy`. Le Key Vault reste récupérable
  7 jours (suppression douce), puis disparaît.

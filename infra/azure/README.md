# Deploy Easy Diligence on Azure

The Terraform code in this folder creates everything needed to run the
application on Azure, using managed services:

```
Internet ─HTTPS─► proxy (Container App, public)
                    ├── /     ► frontend (Container App, internal)
                    └── /api  ► backend  (Container App, internal) ──► PostgreSQL (private)
                                    └── secrets read from Key Vault
```

| Resource | Role |
| --- | --- |
| Azure Container Apps | the three containers from `docker-compose.yml`. Only the proxy is public, over HTTPS, on a `*.azurecontainerapps.io` address |
| Azure Database for PostgreSQL Flexible Server 17 | the database, with no public address, backed up automatically (7 days by default) |
| Azure Container Registry | the images, built in Azure (`az acr build`): no need for Docker on your computer |
| Key Vault | the secrets: the database URL, the JWT key, the OpenAI key |
| Managed identity | one identity for the three applications, which pulls the images and reads the secrets, with no password |
| Virtual network | the applications and the database; the database can only be reached from inside it |
| Log Analytics | the container logs |

Nothing is deployed until you run `terraform apply`. The resources cost
money: at the default sizes (the smallest database, three small containers
that are always on), expect a few tens of euros per month, most of it for the
database.

## What you need

- an Azure subscription, with the **Owner** role (or **Contributor** and **User
  Access Administrator**): Terraform creates role assignments in it;
- **Azure CLI** (`az`), signed in: `az login`, then
  `az account set --subscription <id>`;
- **Terraform** 1.11 or later (tested version in `VERSION.md`).

All commands are run from this folder, `infra/azure/`.

## First deployment

### 1. Prepare the subscription (once)

The resource providers used here must be registered:

```bash
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.DBforPostgreSQL
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.OperationalInsights
```

The Terraform state lives in a storage account, created once. Its name is
unique across all of Azure: change it if needed (3 to 24 lowercase letters and
digits).

```bash
az group create --name rg-easydiligence-tfstate --location francecentral
az storage account create --name easydiligencetfstate \
  --resource-group rg-easydiligence-tfstate --location francecentral \
  --sku Standard_LRS --min-tls-version TLS1_2 \
  --allow-blob-public-access false --allow-shared-key-access false
az storage container create --name tfstate \
  --account-name easydiligencetfstate --auth-mode login
# The right to write to it, for your own account:
az role assignment create --role "Storage Blob Data Contributor" \
  --assignee "$(az ad signed-in-user show --query id -o tsv)" \
  --scope "$(az storage account show --name easydiligencetfstate --query id -o tsv)"
```

The state contains secrets (the database password, the JWT key): only the
people who deploy should have access to this storage account.

### 2. Configure

```bash
cp backend.hcl.example backend.hcl            # the names from step 1
cp terraform.tfvars.example terraform.tfvars  # the subscription, the image tag
terraform init -backend-config=backend.hcl
```

`backend.hcl` and `terraform.tfvars` are ignored by git.

### 3. Create the registry, then build the images in it

The applications need their images as soon as they are created: so the
registry comes first, on its own.

```bash
terraform apply -target=azurerm_container_registry.this
```

Then the three images, built by Azure from the repository, with the tag from
`terraform.tfvars` (`image_tag`):

```bash
REGISTRY=$(terraform output -raw registry)
TAG=2026-11-20   # the image_tag from terraform.tfvars
az acr build --registry "$REGISTRY" --image easy-diligence/backend:$TAG  ../../backend
az acr build --registry "$REGISTRY" --image easy-diligence/frontend:$TAG ../../frontend
az acr build --registry "$REGISTRY" --image easy-diligence/proxy:$TAG    ../../proxy
```

### 4. Create everything

```bash
terraform apply
```

Allow about fifteen minutes: the database takes the longest to create. At
startup, the backend applies the migrations.

### 5. Set the OpenAI key

Terraform creates the secret with a placeholder value, and never sees the real
key:

```bash
az keyvault secret set --vault-name "$(terraform output -raw key_vault)" \
  --name openai-api-key --value "<the OpenAI key>"
```

Then restart the backend, which reads its secrets again:

```bash
BACKEND=$(terraform output -raw backend_app)
GROUP=$(terraform output -raw resource_group)
az containerapp revision restart --name "$BACKEND" --resource-group "$GROUP" \
  --revision "$(az containerapp show --name "$BACKEND" --resource-group "$GROUP" \
    --query properties.latestRevisionName -o tsv)"
```

### 6. Create the first administrator

Open a shell in the backend container, then run the creation command:

```bash
az containerapp exec --name "$BACKEND" --resource-group "$GROUP" --command sh
# in the container:
python -m app.cli create-admin <email address> "<Full Name>"
```

The command asks for the password. The application is at the address given by
`terraform output url`.

## Updating

For each new version: build the images under a new tag (step 3, without the
`terraform apply -target`), put this tag in `terraform.tfvars`, then run
`terraform apply`. The backend applies the migrations when it restarts.

## Good to know

- **Request timeout**: the Azure Container Apps ingress cuts off a request
  after 240 seconds. A summary written live on a very large questionnaire can
  take longer than that: in that case, write it in deferred mode (Batch).
- **A single backend**: it stays at one instance, always on. A run in progress
  lives in its process: putting the backend to sleep or splitting it across
  instances would cut the run off.
- **Domain name**: the application answers on `*.azurecontainerapps.io`. A
  domain of your own, with its certificate, can be added to the proxy's
  Container App.
- **PDF banner**: it is not mounted here. It would take an Azure Files share
  mounted in the backend, and `BRAND_BANNER_PATH` in `backend_env`.
- **Backend settings** (`.env.template`) go through `backend_env` in
  `terraform.tfvars`, never a secret: secrets go in Key Vault.
- **Delete everything**: `terraform destroy`. The Key Vault can still be
  recovered for 7 days (soft delete), then it is gone.

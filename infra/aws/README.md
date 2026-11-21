# Deploy Easy Diligence on AWS

The Terraform code in this folder creates everything needed to run the
application on AWS, using managed services. It is the equivalent of
`infra/azure/`: use one or the other.

```
Internet ─HTTPS─► load balancer ─► proxy (ECS) ──/api──► backend (ECS) ──► RDS PostgreSQL
                                     └──── / ────► frontend (ECS)
```

| Resource | Role |
| --- | --- |
| ECS on Fargate | the three containers from `docker-compose.yml`, in private subnets |
| Application Load Balancer | the only public entry point: it terminates HTTPS (ACM certificate) and forwards to the proxy |
| RDS PostgreSQL 17 | the database, encrypted, private, backed up automatically (7 days by default) |
| ECR | the images, one per service |
| Secrets Manager | the secrets: the database URL, the JWT key, the OpenAI key |
| Cloud Map | the internal names (`backend.<…>.internal`) the proxy uses to reach the other two |
| VPC | two zones; public subnets (load balancer, NAT gateway) and private subnets (containers, database) |
| CloudWatch Logs | the container logs |

Nothing is deployed until you run `terraform apply`. The resources cost
money: at the default sizes, expect about a hundred dollars per month. The NAT
gateway, the load balancer and the database make up most of it.

**Difference from Azure: HTTPS needs a domain name.** AWS does not provide a
ready-made HTTPS address: you need a domain (for example `dd.example.com`) and
its ACM certificate. Without them, the application answers over HTTP on the
load balancer's address, which is only fit for a test: passwords would travel
in clear text.

## What you need

- an AWS account, and a user or a role allowed to create these resources
  (IAM included);
- **AWS CLI** v2, configured (`aws configure` or `aws sso login`), and the
  **Session Manager plugin** for `aws ecs execute-command`;
- **Terraform** 1.11 or later (tested version in `VERSION.md`);
- **Docker**, on the machine that builds the images;
- for HTTPS, a domain name whose DNS you can edit.

All commands are run from this folder, `infra/aws/`. The examples use the
`eu-west-3` region (Paris).

## First deployment

### 1. The state bucket (once)

The Terraform state lives in an S3 bucket, created once. Its name is unique
across all of AWS: put the account number in it, for example.

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

The state contains secrets (the database password, the JWT key): only the
people who deploy should have access to this bucket.

### 2. The certificate (for HTTPS)

```bash
aws acm request-certificate --region eu-west-3 \
  --domain-name dd.example.com --validation-method DNS
```

ACM gives a CNAME record to create in the domain's DNS
(`aws acm describe-certificate --certificate-arn <arn>`); the certificate is
validated a few minutes later. Its ARN goes in `terraform.tfvars`.

### 3. Configure

```bash
cp backend.hcl.example backend.hcl            # the bucket from step 1
cp terraform.tfvars.example terraform.tfvars  # the image tag, the domain
terraform init -backend-config=backend.hcl
```

`backend.hcl` and `terraform.tfvars` are ignored by git.

### 4. Create the image repositories, then push the images to them

The services need their images as soon as they are created: so the
repositories come first, on their own.

```bash
terraform apply -target=aws_ecr_repository.this
```

Then the three images, built for Linux x86-64 (even on a Mac with Apple
silicon), with the tag from `terraform.tfvars` (`image_tag`):

```bash
TAG=2026-11-20   # the image_tag from terraform.tfvars
REGISTRY=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.eu-west-3.amazonaws.com
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin "$REGISTRY"
for service in backend frontend proxy; do
  docker build --platform linux/amd64 -t "$REGISTRY/easy-diligence/$service:$TAG" ../../$service
  docker push "$REGISTRY/easy-diligence/$service:$TAG"
done
```

### 5. Create everything

```bash
terraform apply
```

Allow about fifteen minutes: the database takes the longest to create. At
startup, the backend applies the migrations.

### 6. Point the domain

In the domain's DNS, add a CNAME record from `dd.example.com` to the load
balancer's address: `terraform output load_balancer_dns_name`.

### 7. Set the OpenAI key

Terraform creates the secret with a placeholder value, and never sees the real
key:

```bash
aws secretsmanager put-secret-value \
  --secret-id "$(terraform output -raw openai_secret)" \
  --secret-string "<the OpenAI key>"
```

Then restart the backend, which reads its secrets again when it starts:

```bash
aws ecs update-service --cluster "$(terraform output -raw cluster)" \
  --service backend --force-new-deployment
```

### 8. Create the first administrator

Open a shell in the backend container (ECS Exec), then run the creation
command:

```bash
CLUSTER=$(terraform output -raw cluster)
TASK=$(aws ecs list-tasks --cluster "$CLUSTER" --service-name backend --query 'taskArns[0]' --output text)
aws ecs execute-command --cluster "$CLUSTER" --task "$TASK" \
  --container backend --interactive --command sh
# in the container:
python -m app.cli create-admin <email address> "<Full Name>"
```

The command asks for the password. The application is at the address given by
`terraform output url`.

## Updating

For each new version: push the images under a new tag (step 4, without the
`terraform apply -target`), put this tag in `terraform.tfvars`, then run
`terraform apply`. The old backend stops before the new one starts and applies
the migrations: the API is unavailable for a few moments.

## Good to know

- **Request timeout**: the load balancer and the proxy give long requests
  600 seconds (regeneration, a summary written live).
- **A single backend**: it stays at one task, always on. A run in progress
  lives in its process: splitting it across tasks would cut the run off.
- **A single NAT gateway**, in the first zone: if this zone goes down, the
  containers can no longer reach OpenAI. One gateway per zone costs more.
- **PDF banner**: it is not mounted here. It would take an EFS volume mounted
  in the backend, and `BRAND_BANNER_PATH` in `backend_env`.
- **Backend settings** (`.env.template`) go through `backend_env` in
  `terraform.tfvars`, never a secret: secrets go in Secrets Manager.
- **Delete everything**: the database is protected against deletion. First set
  `deletion_protection = false` in `database.tf` and run `terraform apply`,
  then `terraform destroy`, which keeps a final snapshot of the database
  (`<name>-db-final`). The secrets can still be recovered for 7 days.

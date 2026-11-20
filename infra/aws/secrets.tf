# The secrets, in Secrets Manager. ECS hands them to the backend at start; the
# task definition only names them.
#
# - database-url and jwt-secret-key: generated here. They are in the Terraform
#   state too, which is why the state lives in a bucket only the deployers
#   reach (README).
# - openai-api-key: created with a placeholder, then set by hand (README).
#   Terraform never sees the real key, and leaves it alone afterwards.

resource "random_password" "jwt" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "database_url" {
  name                    = "${local.prefix}/database-url"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  # RDS for PostgreSQL 17 only accepts encrypted connections.
  secret_string = format(
    "postgresql+psycopg://%s:%s@%s:%d/%s?sslmode=require",
    local.postgres_login,
    random_password.postgres.result,
    aws_db_instance.this.address,
    aws_db_instance.this.port,
    local.postgres_database,
  )
}

resource "aws_secretsmanager_secret" "jwt_secret_key" {
  name                    = "${local.prefix}/jwt-secret-key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "jwt_secret_key" {
  secret_id     = aws_secretsmanager_secret.jwt_secret_key.id
  secret_string = random_password.jwt.result
}

resource "aws_secretsmanager_secret" "openai_api_key" {
  name                    = "${local.prefix}/openai-api-key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "openai_api_key" {
  secret_id = aws_secretsmanager_secret.openai_api_key.id
  # Replaced by the real key with aws secretsmanager put-secret-value (README).
  # Until then, the backend starts, and its calls to OpenAI are refused.
  secret_string = "set-me-with-aws-secretsmanager-put-secret-value"

  lifecycle {
    ignore_changes = [secret_string]
  }
}

locals {
  backend_secrets = {
    DATABASE_URL   = aws_secretsmanager_secret.database_url.arn
    JWT_SECRET_KEY = aws_secretsmanager_secret.jwt_secret_key.arn
    OPENAI_API_KEY = aws_secretsmanager_secret.openai_api_key.arn
  }
}

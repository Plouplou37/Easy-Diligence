# The secrets, in Key Vault. The applications read them with their identity;
# Container Apps fetches them by reference, never as a copy.
#
# - database-url and jwt-secret-key: generated here. They are in the Terraform
#   state too, which is why the state lives in a storage account only the
#   deployers reach (README).
# - openai-api-key: created with a placeholder, then set by hand (README).
#   Terraform never sees the real key, and leaves it alone afterwards.

resource "azurerm_key_vault" "this" {
  name                       = "kv-${substr(local.compact, 0, 13)}-${local.suffix}"
  location                   = azurerm_resource_group.this.location
  resource_group_name        = azurerm_resource_group.this.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  tags                       = local.tags
}

# Whoever runs Terraform writes the secrets.
resource "azurerm_role_assignment" "deployer_secrets" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# The applications only read them.
resource "azurerm_role_assignment" "apps_secrets" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.apps.principal_id
  principal_type       = "ServicePrincipal"
}

resource "random_password" "jwt" {
  length  = 64
  special = false
}

resource "azurerm_key_vault_secret" "database_url" {
  name         = "database-url"
  key_vault_id = azurerm_key_vault.this.id
  # Azure's PostgreSQL only accepts encrypted connections.
  value = format(
    "postgresql+psycopg://%s:%s@%s:5432/%s?sslmode=require",
    local.postgres_login,
    random_password.postgres.result,
    azurerm_postgresql_flexible_server.this.fqdn,
    local.postgres_database,
  )

  depends_on = [time_sleep.role_propagation]
}

resource "azurerm_key_vault_secret" "jwt_secret_key" {
  name         = "jwt-secret-key"
  key_vault_id = azurerm_key_vault.this.id
  value        = random_password.jwt.result

  depends_on = [time_sleep.role_propagation]
}

resource "azurerm_key_vault_secret" "openai_api_key" {
  name         = "openai-api-key"
  key_vault_id = azurerm_key_vault.this.id
  # Replaced by the real key with az keyvault secret set (README). Until then,
  # the backend starts, and its calls to OpenAI are refused.
  value = "set-me-with-az-keyvault-secret-set"

  depends_on = [time_sleep.role_propagation]

  lifecycle {
    ignore_changes = [value]
  }
}

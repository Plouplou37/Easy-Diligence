output "url" {
  description = "The address of the application."
  value       = local.public_url
}

output "resource_group" {
  description = "The resource group of everything here."
  value       = azurerm_resource_group.this.name
}

output "registry" {
  description = "The registry name, for az acr build (README)."
  value       = azurerm_container_registry.this.name
}

output "key_vault" {
  description = "The Key Vault name, for az keyvault secret set (README)."
  value       = azurerm_key_vault.this.name
}

output "backend_app" {
  description = "The backend's Container App, for az containerapp exec (README)."
  value       = azurerm_container_app.backend.name
}

output "postgres_server" {
  description = "The PostgreSQL server (reachable from the virtual network only)."
  value       = azurerm_postgresql_flexible_server.this.fqdn
}

# The registry of the three images. They are built in Azure itself
# (az acr build, README): no Docker needed on the machine that deploys.

locals {
  images = {
    for service in ["proxy", "frontend", "backend"] :
    service => "${azurerm_container_registry.this.login_server}/easy-diligence/${service}:${var.image_tag}"
  }
}

resource "azurerm_container_registry" "this" {
  name                = "${local.compact}${local.suffix}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "Basic"
  # Pulled with the applications' identity, never with a password.
  admin_enabled = false
  tags          = local.tags
}

resource "azurerm_role_assignment" "apps_pull" {
  scope                = azurerm_container_registry.this.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.apps.principal_id
  principal_type       = "ServicePrincipal"
}

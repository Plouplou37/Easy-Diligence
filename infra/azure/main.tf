# Easy Diligence on Azure: the shared pieces. The database (database.tf),
# the secrets (secrets.tf), the registry (registry.tf) and the applications
# (apps.tf) build on them. README.md gives the commands, in order.

locals {
  prefix  = "${var.name}-${var.environment}"
  compact = replace(local.prefix, "-", "")
  # Key Vault, registry and database names are global: a random suffix keeps
  # them free.
  suffix = random_string.suffix.result

  tags = merge(
    {
      application = "easy-diligence"
      environment = var.environment
      managed-by  = "terraform"
    },
    var.tags,
  )
}

data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.prefix}"
  location = var.location
  tags     = local.tags
}

# The logs of the containers (Container Apps writes there).
resource "azurerm_log_analytics_workspace" "this" {
  name                = "${local.prefix}-logs"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

# --- Network: the applications and the database, the database private -----------

resource "azurerm_virtual_network" "this" {
  name                = "${local.prefix}-vnet"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  address_space       = [var.vnet_address_space]
  tags                = local.tags
}

resource "azurerm_subnet" "apps" {
  name                 = "apps"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.apps_subnet]

  delegation {
    name = "container-apps"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "postgres" {
  name                 = "postgres"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.postgres_subnet]

  delegation {
    name = "postgres"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# --- The identity of the applications --------------------------------------------
# One identity for the three: it pulls the images and reads the secrets. No
# password anywhere (role assignments in registry.tf and secrets.tf).

resource "azurerm_user_assigned_identity" "apps" {
  name                = "${local.prefix}-apps"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}

# Azure takes a moment to honour a new role assignment: without this pause, the
# first secret write or image pull may be refused.
resource "time_sleep" "role_propagation" {
  create_duration = "60s"

  depends_on = [
    azurerm_role_assignment.deployer_secrets,
    azurerm_role_assignment.apps_secrets,
    azurerm_role_assignment.apps_pull,
  ]
}

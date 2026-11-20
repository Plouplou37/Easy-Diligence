# The three containers of docker-compose.yml, as Azure Container Apps:
#
#   Internet ─HTTPS─► proxy ──/api──► backend ──► PostgreSQL
#                       └──── / ────► frontend
#
# Only the proxy is public; Azure gives it HTTPS, on an address in
# *.azurecontainerapps.io. The frontend and the backend only have an internal
# ingress, which the proxy reaches by the application's name.

locals {
  apps = {
    proxy    = "${local.prefix}-proxy"
    frontend = "${local.prefix}-frontend"
    backend  = "${local.prefix}-backend"
  }
  # The public address, known before the proxy exists (no dependency cycle):
  # an application's FQDN is its name in the environment's domain.
  public_url = "https://${local.apps.proxy}.${azurerm_container_app_environment.this.default_domain}"
}

resource "azurerm_container_app_environment" "this" {
  name                           = "${local.prefix}-env"
  location                       = azurerm_resource_group.this.location
  resource_group_name            = azurerm_resource_group.this.name
  log_analytics_workspace_id     = azurerm_log_analytics_workspace.this.id
  infrastructure_subnet_id       = azurerm_subnet.apps.id
  internal_load_balancer_enabled = false
  tags                           = local.tags

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

# --- Backend --------------------------------------------------------------------
# One replica, always on: a run goes on in its process (BackgroundTasks), and
# scaling it down would stop it halfway. At start, the migrations, then the API
# (backend/Dockerfile).

resource "azurerm_container_app" "backend" {
  name                         = local.apps.backend
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps.id]
  }

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.apps.id
  }

  secret {
    name                = "database-url"
    key_vault_secret_id = azurerm_key_vault_secret.database_url.versionless_id
    identity            = azurerm_user_assigned_identity.apps.id
  }
  secret {
    name                = "jwt-secret-key"
    key_vault_secret_id = azurerm_key_vault_secret.jwt_secret_key.versionless_id
    identity            = azurerm_user_assigned_identity.apps.id
  }
  secret {
    name                = "openai-api-key"
    key_vault_secret_id = azurerm_key_vault_secret.openai_api_key.versionless_id
    identity            = azurerm_user_assigned_identity.apps.id
  }

  ingress {
    external_enabled = false
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "backend"
      image  = local.images.backend
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name        = "JWT_SECRET_KEY"
        secret_name = "jwt-secret-key"
      }
      env {
        name        = "OPENAI_API_KEY"
        secret_name = "openai-api-key"
      }
      env {
        name  = "OPENAI_MODEL"
        value = var.openai_model
      }
      # The address put in the password reset e-mails.
      env {
        name  = "FRONTEND_URL"
        value = local.public_url
      }
      dynamic "env" {
        for_each = var.backend_env
        content {
          name  = env.key
          value = env.value
        }
      }

      # The migrations run before the API answers: room for them.
      startup_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/health"
        interval_seconds        = 10
        failure_count_threshold = 30
      }
      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }
    }
  }

  depends_on = [time_sleep.role_propagation]
}

# --- Frontend -------------------------------------------------------------------

resource "azurerm_container_app" "frontend" {
  name                         = local.apps.frontend
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps.id]
  }

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.apps.id
  }

  ingress {
    external_enabled = false
    target_port      = 80
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 2

    container {
      name   = "frontend"
      image  = local.images.frontend
      cpu    = 0.25
      memory = "0.5Gi"

      liveness_probe {
        transport = "HTTP"
        port      = 80
        path      = "/"
      }
    }
  }

  depends_on = [time_sleep.role_propagation]
}

# --- Proxy ----------------------------------------------------------------------
# The only public application. It reaches the two others by their name on the
# environment's internal ingress (port 80), and trusts the X-Forwarded-For of
# Azure's ingress, which runs in the apps subnet.

resource "azurerm_container_app" "proxy" {
  name                         = local.apps.proxy
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps.id]
  }

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.apps.id
  }

  ingress {
    external_enabled = true
    target_port      = 80
    transport        = "auto"
    # HTTP is redirected to HTTPS.
    allow_insecure_connections = false

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 2

    container {
      name   = "proxy"
      image  = local.images.proxy
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "BACKEND_UPSTREAM"
        value = "http://${local.apps.backend}"
      }
      env {
        name  = "FRONTEND_UPSTREAM"
        value = "http://${local.apps.frontend}"
      }
      env {
        name  = "TRUSTED_PROXIES"
        value = var.apps_subnet
      }

      liveness_probe {
        transport = "HTTP"
        port      = 80
        path      = "/healthz"
      }
    }
  }

  # nginx resolves the names of the two others when it starts.
  depends_on = [azurerm_container_app.backend, azurerm_container_app.frontend]
}

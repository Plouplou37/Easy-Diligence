variable "subscription_id" {
  description = "The Azure subscription that receives the resources."
  type        = string
}

variable "location" {
  description = "The Azure region of every resource."
  type        = string
  default     = "francecentral"
}

variable "name" {
  description = "Short name of the application, in the name of every resource."
  type        = string
  default     = "easydiligence"

  validation {
    condition     = can(regex("^[a-z]{3,13}$", var.name))
    error_message = "3 to 13 lowercase letters: it goes into names that allow nothing else."
  }
}

variable "environment" {
  description = "The environment (prod, staging...), in the name of every resource."
  type        = string
  default     = "prod"

  validation {
    condition     = can(regex("^[a-z0-9]{2,6}$", var.environment))
    error_message = "2 to 6 lowercase letters or digits."
  }
}

variable "tags" {
  description = "Tags added to every resource."
  type        = map(string)
  default     = {}
}

# --- The images ----------------------------------------------------------------

variable "image_tag" {
  description = "Tag of the three images in the registry (az acr build, README): a version or a commit, never latest."
  type        = string

  validation {
    condition     = var.image_tag != "latest"
    error_message = "A fixed tag: with latest, nothing tells which code is running."
  }
}

# --- The application -----------------------------------------------------------

variable "openai_model" {
  description = "OPENAI_MODEL of the backend (.env.template)."
  type        = string
  default     = "gpt-5.6-luna"
}

variable "backend_env" {
  description = "Other settings of the backend (.env.template), as NAME = value. Never a secret: those go to Key Vault."
  type        = map(string)
  default     = {}
}

# --- Sizes ---------------------------------------------------------------------

variable "postgres_sku" {
  description = "Size of the PostgreSQL server. B_Standard_B1ms is the smallest (burstable)."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "postgres_storage_mb" {
  description = "Storage of the PostgreSQL server, in MB."
  type        = number
  default     = 32768
}

variable "postgres_backup_retention_days" {
  description = "Days of automatic backups of the database (7 to 35)."
  type        = number
  default     = 7
}

# --- Network -------------------------------------------------------------------

variable "vnet_address_space" {
  description = "Address space of the virtual network."
  type        = string
  default     = "10.20.0.0/16"
}

variable "apps_subnet" {
  description = "Subnet of the Container Apps environment (a /27 at least). Its ingress is the proxy the nginx proxy trusts."
  type        = string
  default     = "10.20.0.0/23"
}

variable "postgres_subnet" {
  description = "Subnet delegated to the PostgreSQL server."
  type        = string
  default     = "10.20.2.0/24"
}

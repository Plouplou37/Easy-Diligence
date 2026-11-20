variable "region" {
  description = "The AWS region of every resource."
  type        = string
  default     = "eu-west-3"
}

variable "name" {
  description = "Short name of the application, in the name of every resource."
  type        = string
  default     = "easydiligence"

  validation {
    condition     = can(regex("^[a-z]{3,13}$", var.name))
    error_message = "3 to 13 lowercase letters."
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

# --- HTTPS -----------------------------------------------------------------------

variable "domain_name" {
  description = "The domain the application answers on (app.example.com), pointed at the load balancer. Null: the load balancer's own address, in HTTP only."
  type        = string
  default     = null
}

variable "certificate_arn" {
  description = "The ACM certificate of domain_name, in the same region (README). Null: HTTP only, for a test, never with real accounts."
  type        = string
  default     = null
}

# --- The images ----------------------------------------------------------------

variable "image_tag" {
  description = "Tag of the three images pushed to ECR (README): a version or a commit, never latest."
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
  description = "Other settings of the backend (.env.template), as NAME = value. Never a secret: those go to Secrets Manager."
  type        = map(string)
  default     = {}
}

# --- Sizes ---------------------------------------------------------------------

variable "db_instance_class" {
  description = "Size of the PostgreSQL instance. db.t4g.micro is the smallest."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "Storage of the PostgreSQL instance, in GB."
  type        = number
  default     = 20
}

variable "db_backup_retention_days" {
  description = "Days of automatic backups of the database (1 to 35)."
  type        = number
  default     = 7
}

# --- Network -------------------------------------------------------------------

variable "vpc_cidr" {
  description = "Address space of the VPC: two public subnets (the load balancer, the NAT gateway) and two private ones (the containers, the database) are cut from it."
  type        = string
  default     = "10.30.0.0/16"
}

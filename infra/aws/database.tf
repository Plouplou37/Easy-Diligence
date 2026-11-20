# PostgreSQL 17 on RDS: encrypted, backed up automatically, in the private
# subnets. Only the backend's security group reaches it.

locals {
  postgres_login    = "easydiligence"
  postgres_database = "easy_diligence"
}

resource "aws_db_subnet_group" "this" {
  name       = "${local.prefix}-db"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_security_group" "db" {
  name        = "${local.prefix}-db"
  description = "PostgreSQL: from the backend only"
  vpc_id      = aws_vpc.this.id
}

resource "aws_vpc_security_group_ingress_rule" "db_from_backend" {
  security_group_id            = aws_security_group.db.id
  referenced_security_group_id = aws_security_group.backend.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

# Letters and digits only: the password goes into DATABASE_URL as it is.
resource "random_password" "postgres" {
  length  = 32
  special = false
}

resource "aws_db_instance" "this" {
  identifier     = "${local.prefix}-db"
  engine         = "postgres"
  engine_version = "17"
  instance_class = var.db_instance_class

  allocated_storage = var.db_allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = local.postgres_database
  username = local.postgres_login
  password = random_password.postgres.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  backup_retention_period    = var.db_backup_retention_days
  auto_minor_version_upgrade = true

  # A deletion goes through a final snapshot, and must first be allowed by
  # setting deletion_protection to false (README).
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.prefix}-db-final"
}

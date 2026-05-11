# ── DB Password ───────────────────────────────────────────────────────────────

resource "random_password" "db" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}?"
}

resource "aws_secretsmanager_secret" "db_password" {
  name                    = "${local.name}/db-password"
  recovery_window_in_days = 0  # allow immediate deletion during dev; increase for prod
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db.result
}

# ── Subnet Group ──────────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
}

# ── RDS PostgreSQL ────────────────────────────────────────────────────────────

resource "aws_db_instance" "main" {
  identifier = local.name

  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  allocated_storage     = 20
  storage_type          = "gp3"
  storage_encrypted     = true

  backup_retention_period = 7
  skip_final_snapshot     = false
  final_snapshot_identifier = "${local.name}-final"

  # Maintenance and upgrades
  auto_minor_version_upgrade  = true
  maintenance_window          = "sun:04:00-sun:05:00"
  backup_window               = "03:00-04:00"

  # Keep out of public subnets — ECS reaches it via private networking
  publicly_accessible = false

  deletion_protection = true
}

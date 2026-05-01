variable "name" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "kms_key_arn" { type = string }
variable "db_password_secret_arn" { type = string }
variable "instance_class" {
  type    = string
  default = "db.t4g.medium"
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-db"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "db" {
  name        = "${var.name}-db"
  description = "Postgres access from app subnets"
  vpc_id      = var.vpc_id

  ingress {
    from_port = 5432
    to_port   = 5432
    protocol  = "tcp"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = var.db_password_secret_arn
}

resource "aws_db_instance" "this" {
  identifier                  = "${var.name}-postgres"
  engine                      = "postgres"
  engine_version              = "15"
  instance_class              = var.instance_class
  allocated_storage           = 100
  max_allocated_storage       = 1000
  storage_type                = "gp3"
  storage_encrypted           = true
  kms_key_id                  = var.kms_key_arn
  username                    = "woundscan"
  password                    = data.aws_secretsmanager_secret_version.db_password.secret_string
  db_name                     = "woundscan"
  backup_retention_period     = 7
  multi_az                    = true
  deletion_protection         = true
  performance_insights_enabled = true
  enabled_cloudwatch_logs_exports = ["postgresql"]
  db_subnet_group_name        = aws_db_subnet_group.this.name
  vpc_security_group_ids      = [aws_security_group.db.id]
  apply_immediately           = false
  auto_minor_version_upgrade  = true
  copy_tags_to_snapshot       = true
  parameter_group_name        = aws_db_parameter_group.this.name

  tags = { HIPAA = "yes" }
}

resource "aws_db_parameter_group" "this" {
  name   = "${var.name}-postgres15"
  family = "postgres15"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements,pgaudit"
  }

  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }
}

output "endpoint" { value = aws_db_instance.this.endpoint }

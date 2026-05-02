variable "name" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "kms_key_arn" { type = string }
variable "db_password_secret_arn" { type = string }
variable "instance_class" {
  type    = string
  default = "db.t4g.medium"
}
variable "allocated_storage" {
  type    = number
  default = 100
}
variable "max_allocated_storage" {
  type    = number
  default = 1000
}
variable "multi_az" {
  type    = bool
  default = true
}
variable "deletion_protection" {
  type    = bool
  default = true
}
variable "backup_retention_period" {
  type    = number
  default = 7
}
variable "app_security_group_ids" {
  type        = list(string)
  default     = []
  description = "Security groups whose members may connect to Postgres on 5432."
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-db"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "db" {
  name        = "${var.name}-db"
  description = "Postgres access from app subnets"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "db_ingress_from_app" {
  count                    = length(var.app_security_group_ids)
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db.id
  source_security_group_id = var.app_security_group_ids[count.index]
}

data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = var.db_password_secret_arn
}

resource "aws_db_instance" "this" {
  identifier                      = "${var.name}-postgres"
  engine                          = "postgres"
  engine_version                  = "15"
  instance_class                  = var.instance_class
  allocated_storage               = var.allocated_storage
  max_allocated_storage           = var.max_allocated_storage
  storage_type                    = "gp3"
  storage_encrypted               = true
  kms_key_id                      = var.kms_key_arn
  username                        = "woundscan"
  password                        = data.aws_secretsmanager_secret_version.db_password.secret_string
  db_name                         = "woundscan"
  backup_retention_period         = var.backup_retention_period
  multi_az                        = var.multi_az
  deletion_protection             = var.deletion_protection
  performance_insights_enabled    = true
  enabled_cloudwatch_logs_exports = ["postgresql"]
  db_subnet_group_name            = aws_db_subnet_group.this.name
  vpc_security_group_ids          = [aws_security_group.db.id]
  apply_immediately               = false
  auto_minor_version_upgrade      = true
  copy_tags_to_snapshot           = true
  parameter_group_name            = aws_db_parameter_group.this.name
  skip_final_snapshot             = !var.deletion_protection

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
output "host"     { value = aws_db_instance.this.address }
output "port"     { value = aws_db_instance.this.port }

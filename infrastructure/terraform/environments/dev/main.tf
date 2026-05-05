terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "woundscan-tf-state-dev"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "woundscan-tf-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "image" { type = string }

resource "aws_kms_key" "data" {
  description             = "WoundScan dev KMS"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

module "vpc" {
  source     = "../../modules/vpc"
  name       = "woundscan-dev"
  cidr_block = "10.40.0.0/16"
  azs        = ["us-east-1a", "us-east-1b"]
}

module "s3" {
  source         = "../../modules/s3"
  name           = "woundscan-dev"
  kms_key_arn    = aws_kms_key.data.arn
  retention_days = 30
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "woundscan/dev/db-password"
}

data "aws_secretsmanager_secret" "jwt_signing" {
  name = "woundscan/dev/jwt-signing"
}

module "rds" {
  source                  = "../../modules/rds"
  name                    = "woundscan-dev"
  vpc_id                  = module.vpc.vpc_id
  subnet_ids              = module.vpc.private_subnet_ids
  kms_key_arn             = aws_kms_key.data.arn
  db_password_secret_arn  = aws_secretsmanager_secret.db_password.arn
  app_security_group_ids  = [module.ecs.task_security_group_id]
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  max_allocated_storage   = 100
  multi_az                = false
  deletion_protection     = false
  backup_retention_period = 1
}

module "alb" {
  source            = "../../modules/alb"
  name              = "woundscan-dev"
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  enable_https      = true
  certificate_arn   = aws_acm_certificate_validation.api.certificate_arn
}

resource "aws_acm_certificate" "api" {
  domain_name       = "woundscan.albacetemeddev.com"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn = aws_acm_certificate.api.arn
}

output "acm_validation_record" {
  description = "Add this CNAME at your DNS provider to validate the cert. Terraform will hang on aws_acm_certificate_validation until you do."
  value = {
    for d in aws_acm_certificate.api.domain_validation_options :
    d.domain_name => {
      name  = d.resource_record_name
      type  = d.resource_record_type
      value = d.resource_record_value
    }
  }
}

module "ecs" {
  source               = "../../modules/ecs"
  name                 = "woundscan-dev-api"
  vpc_id               = module.vpc.vpc_id
  subnet_ids           = module.vpc.private_subnet_ids
  image                = var.image
  desired_count        = 1
  min_capacity         = 1
  max_capacity         = 2
  target_group_arn     = module.alb.target_group_arn
  enable_lb            = true
  lb_security_group_id = module.alb.security_group_id
  secret_arns = {
    WS_DB_PASSWORD       = aws_secretsmanager_secret.db_password.arn
    WS_JWT_SIGNING_KEY   = data.aws_secretsmanager_secret.jwt_signing.arn
  }
  environment = {
    WS_DB_HOST           = module.rds.host
    WS_DB_PORT           = tostring(module.rds.port)
    WS_DB_DATABASE       = "woundscan"
    WS_DB_USER           = "woundscan"
    WS_S3_REGION         = "us-east-1"
    WS_S3_BUCKET         = "woundscan-dev-artifacts"
    WS_S3_RETENTION_DAYS = "30"
    WS_CELERY_EAGER      = "1"
  }
}

resource "aws_iam_role_policy" "task_s3" {
  name = "woundscan-dev-api-task-s3"
  role = module.ecs.task_role_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetObjectLegalHold",
          "s3:PutObjectLegalHold",
          "s3:GetObjectRetention",
          "s3:PutObjectRetention",
        ]
        Resource = [
          module.s3.bucket_arn,
          "${module.s3.bucket_arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey",
        ]
        Resource = aws_kms_key.data.arn
      },
    ]
  })
}

output "alb_dns_name" {
  value       = module.alb.dns_name
  description = "Public hostname for the dev API. Hit it with: curl http://<this>/healthz"
}

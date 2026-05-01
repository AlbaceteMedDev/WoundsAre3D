terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "woundscan-tf-state-prod"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "woundscan-tf-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "image" {
  description = "ECR image URI"
  type        = string
}

resource "aws_kms_key" "data" {
  description             = "WoundScan data encryption KMS"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

module "vpc" {
  source     = "../../modules/vpc"
  name       = "woundscan-prod"
  cidr_block = "10.50.0.0/16"
  azs        = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

module "s3" {
  source                           = "../../modules/s3"
  name                             = "woundscan-prod"
  kms_key_arn                      = aws_kms_key.data.arn
  transition_to_glacier_after_days = 30
}

resource "aws_secretsmanager_secret" "db_password" {
  name        = "woundscan/prod/db-password"
  description = "Postgres master password"
  kms_key_id  = aws_kms_key.data.arn
}

module "rds" {
  source                 = "../../modules/rds"
  name                   = "woundscan-prod"
  vpc_id                 = module.vpc.vpc_id
  subnet_ids             = module.vpc.private_subnet_ids
  kms_key_arn            = aws_kms_key.data.arn
  db_password_secret_arn = aws_secretsmanager_secret.db_password.arn
}

module "ecs" {
  source        = "../../modules/ecs"
  name          = "woundscan-prod-api"
  vpc_id        = module.vpc.vpc_id
  subnet_ids    = module.vpc.private_subnet_ids
  image         = var.image
  desired_count = 2
  max_capacity  = 10
  secret_arns = {
    WS_DB_PASSWORD = aws_secretsmanager_secret.db_password.arn
  }
}

resource "aws_guardduty_detector" "this" {
  enable = true
}

resource "aws_securityhub_account" "this" {}

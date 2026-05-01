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

module "ecs" {
  source        = "../../modules/ecs"
  name          = "woundscan-dev-api"
  vpc_id        = module.vpc.vpc_id
  subnet_ids    = module.vpc.private_subnet_ids
  image         = var.image
  desired_count = 1
  min_capacity  = 1
  max_capacity  = 2
  secret_arns = {
    WS_DB_PASSWORD = aws_secretsmanager_secret.db_password.arn
  }
}

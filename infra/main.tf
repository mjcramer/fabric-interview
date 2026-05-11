terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Bootstrap these manually once before first apply (see README):
  #   aws s3api create-bucket --bucket aeo-tf-state-<suffix> --region us-west-2 --create-bucket-configuration LocationConstraint=us-west-2
  #   aws s3api put-bucket-versioning --bucket aeo-tf-state-<suffix> --versioning-configuration Status=Enabled
  #   aws dynamodb create-table --table-name aeo-tf-locks --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST --region us-west-2
  backend "s3" {
    bucket         = "aeo-tf-state"
    key            = "prod/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "aeo-tf-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "aeo-platform"
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}

locals {
  name   = "aeo"
  domain = "aeo.alsotheseer.com"

  # Availability zones
  azs = ["${var.aws_region}a", "${var.aws_region}b"]

  # CIDR blocks
  vpc_cidr             = "10.0.0.0/16"
  public_subnet_cidrs  = ["10.0.0.0/24", "10.0.1.0/24"]
  private_subnet_cidrs = ["10.0.2.0/24", "10.0.3.0/24"]
}

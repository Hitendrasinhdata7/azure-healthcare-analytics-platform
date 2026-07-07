terraform {
  required_version = ">= 1.7"
  backend "s3" {
    bucket         = "gitops-platform-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = { Environment = "dev", ManagedBy = "terraform", Project = "gitops-platform" }
  }
}

module "networking" {
  source      = "../../modules/networking"
  environment = "dev"
  vpc_cidr    = var.vpc_cidr
  azs         = var.azs
}

module "eks" {
  source              = "../../modules/eks"
  environment         = "dev"
  private_subnet_ids  = module.networking.private_subnet_ids
  node_instance_type  = var.node_instance_type
  min_nodes           = var.min_nodes
  max_nodes           = var.max_nodes
  desired_nodes       = var.desired_nodes
}

module "storage" {
  source      = "../../modules/storage"
  environment = "dev"
}

module "security_groups" {
  source      = "../../modules/security-groups"
  environment = "dev"
  vpc_id      = module.networking.vpc_id
}

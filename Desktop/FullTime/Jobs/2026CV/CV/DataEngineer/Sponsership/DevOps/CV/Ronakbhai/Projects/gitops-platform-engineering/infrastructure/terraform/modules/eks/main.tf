# EKS module: managed control plane + managed node groups, one module reused
# across dev/staging/prod with different sizing via tfvars per environment.
variable "environment" {
  type = string
}
variable "cluster_version" {
  type    = string
  default = "1.30"
}
variable "private_subnet_ids" {
  type = list(string)
}
variable "node_instance_type" {
  type = string
}
variable "min_nodes" {
  type = number
}
variable "max_nodes" {
  type = number
}
variable "desired_nodes" {
  type = number
}

resource "aws_eks_cluster" "this" {
  name     = "${var.environment}-gitops-cluster"
  version  = var.cluster_version
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = var.environment != "prod"  # prod: private endpoint only
  }

  encryption_config {
    resources = ["secrets"]
    provider { key_arn = aws_kms_key.eks.arn }
  }
}

resource "aws_kms_key" "eks" {
  description         = "EKS secret encryption for ${var.environment}"
  enable_key_rotation = true
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.environment}-workers"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids
  instance_types  = [var.node_instance_type]

  scaling_config {
    min_size     = var.min_nodes
    max_size     = var.max_nodes
    desired_size = var.desired_nodes
  }

  update_config { max_unavailable = 1 }
}

resource "aws_iam_role" "cluster" {
  name               = "${var.environment}-eks-cluster-role"
  assume_role_policy = data.aws_iam_policy_document.eks_assume.json
}

resource "aws_iam_role" "node" {
  name               = "${var.environment}-eks-node-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

data "aws_iam_policy_document" "eks_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals { type = "Service", identifiers = ["eks.amazonaws.com"] }
  }
}
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals { type = "Service", identifiers = ["ec2.amazonaws.com"] }
  }
}

output "cluster_endpoint" { value = aws_eks_cluster.this.endpoint }
output "cluster_name"     { value = aws_eks_cluster.this.name }

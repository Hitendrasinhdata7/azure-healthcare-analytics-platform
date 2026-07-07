variable "environment" { type = string }
variable "vpc_id"      { type = string }

resource "aws_security_group" "cluster" {
  name_prefix = "${var.environment}-eks-cluster-"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "node_to_cluster" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.cluster.id
  source_security_group_id = aws_security_group.nodes.id
}

resource "aws_security_group" "nodes" {
  name_prefix = "${var.environment}-eks-nodes-"
  vpc_id      = var.vpc_id
}

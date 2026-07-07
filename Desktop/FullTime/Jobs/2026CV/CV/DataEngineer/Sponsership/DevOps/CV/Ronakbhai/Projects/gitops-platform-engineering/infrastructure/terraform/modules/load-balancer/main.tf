# ALB provisioned by the AWS Load Balancer Controller (installed as a
# platform service) - this module only provisions the target-group-less
# base ALB used for ACM cert attachment and Route53 alias records.
variable "environment"      { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "vpc_id"           { type = string }

resource "aws_lb" "ingress" {
  name               = "${var.environment}-ingress-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.alb.id]
}

resource "aws_security_group" "alb" {
  name_prefix = "${var.environment}-alb-"
  vpc_id      = var.vpc_id
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

output "alb_dns_name" { value = aws_lb.ingress.dns_name }
output "alb_zone_id"  { value = aws_lb.ingress.zone_id }

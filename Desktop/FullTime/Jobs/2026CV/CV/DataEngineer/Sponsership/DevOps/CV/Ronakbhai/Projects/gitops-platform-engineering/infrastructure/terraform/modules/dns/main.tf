variable "environment"  { type = string }
variable "domain_name"  { type = string }

resource "aws_route53_zone" "env" {
  name = "${var.environment}.${var.domain_name}"
}

resource "aws_route53_record" "wildcard" {
  zone_id = aws_route53_zone.env.zone_id
  name    = "*.${var.environment}.${var.domain_name}"
  type    = "A"
  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}

variable "alb_dns_name" { type = string }
variable "alb_zone_id"  { type = string }

# VPC module: 3-tier network (public/private/data subnets) across 3 AZs for HA
variable "environment" { type = string }
variable "vpc_cidr"    { type = string }
variable "azs"         { type = list(string) }

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "${var.environment}-vpc", Environment = var.environment }
}

resource "aws_subnet" "public" {
  for_each                = toset(var.azs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, index(var.azs, each.value))
  availability_zone       = each.value
  map_public_ip_on_launch = true
  tags = { Name = "${var.environment}-public-${each.value}", "kubernetes.io/role/elb" = "1" }
}

resource "aws_subnet" "private" {
  for_each          = toset(var.azs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, index(var.azs, each.value) + 8)
  availability_zone = each.value
  tags = { Name = "${var.environment}-private-${each.value}", "kubernetes.io/role/internal-elb" = "1" }
}

resource "aws_nat_gateway" "main" {
  for_each      = toset(var.azs)
  allocation_id = aws_eip.nat[each.value].id
  subnet_id     = aws_subnet.public[each.value].id
}

resource "aws_eip" "nat" {
  for_each = toset(var.azs)
  domain   = "vpc"
}

output "vpc_id"             { value = aws_vpc.main.id }
output "private_subnet_ids" { value = [for s in aws_subnet.private : s.id] }
output "public_subnet_ids"  { value = [for s in aws_subnet.public : s.id] }

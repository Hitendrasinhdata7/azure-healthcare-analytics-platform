# IRSA (IAM Roles for Service Accounts): lets K8s ServiceAccounts assume
# scoped AWS IAM roles directly - no static AWS keys inside the cluster.
variable "environment"     { type = string }
variable "oidc_provider_arn" { type = string }
variable "oidc_provider_url" { type = string }

resource "aws_iam_role" "external_secrets" {
  name = "${var.environment}-external-secrets-irsa"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Federated = var.oidc_provider_arn }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${var.oidc_provider_url}:sub" = "system:serviceaccount:external-secrets:external-secrets"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "external_secrets_vault_kms" {
  name   = "vault-unseal-kms-access"
  role   = aws_iam_role.external_secrets.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["kms:Decrypt", "kms:Encrypt", "kms:DescribeKey"]
      Resource = "*"
    }]
  })
}

output "external_secrets_role_arn" { value = aws_iam_role.external_secrets.arn }

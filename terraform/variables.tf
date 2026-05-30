variable "subscription_id" {
  description = "Azure Subscription ID"
  type        = string
  sensitive   = true
}

variable "tenant_id" {
  description = "Azure AD Tenant ID"
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Project identifier used in resource naming"
  type        = string
  default     = "healthcare"
}

variable "environment" {
  description = "Deployment environment: dev | test | prod"
  type        = string
  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be dev, test, or prod."
  }
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "uksouth"
}

variable "owner" {
  description = "Team or individual responsible for the resources"
  type        = string
  default     = "data-engineering-team"
}

variable "cost_centre" {
  description = "Cost centre tag for billing allocation"
  type        = string
  default     = "NHS-DIGITAL-001"
}

variable "databricks_sku" {
  description = "Databricks workspace SKU: standard | premium"
  type        = string
  default     = "premium"
}

variable "synapse_sql_admin" {
  description = "Synapse SQL pool administrator login"
  type        = string
  default     = "sqladmin"
  sensitive   = true
}

variable "synapse_sql_password" {
  description = "Synapse SQL pool administrator password"
  type        = string
  sensitive   = true
}

variable "allowed_ip_ranges" {
  description = "CIDR ranges permitted to access Key Vault and Synapse"
  type        = list(string)
  default     = []
}

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                       = "kv-${var.project_name}-${var.environment}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 30
  purge_protection_enabled   = true
  enable_rbac_authorization  = true

  network_acls {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }

  tags = var.tags
}

# Allow Terraform deployer to manage secrets
resource "azurerm_role_assignment" "deployer_kv" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

output "keyvault_id"  { value = azurerm_key_vault.main.id }
output "keyvault_uri" { value = azurerm_key_vault.main.vault_uri }

variable "resource_group_name" {}
variable "location" {}
variable "project_name" {}
variable "environment" {}
variable "tenant_id" {}
variable "tags" { default = {} }

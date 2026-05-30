resource "azurerm_synapse_workspace" "main" {
  name                                 = "synw-${var.project_name}-${var.environment}"
  resource_group_name                  = var.resource_group_name
  location                             = var.location
  storage_data_lake_gen2_filesystem_id = var.data_lake_filesystem
  sql_administrator_login              = var.sql_admin_login
  sql_administrator_login_password     = var.sql_admin_password

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_synapse_sql_pool" "main" {
  name                 = "sqlpool${var.environment}"
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  sku_name             = var.environment == "prod" ? "DW200c" : "DW100c"
  create_mode          = "Default"
  tags                 = var.tags
}

resource "azurerm_synapse_firewall_rule" "azure_services" {
  name                 = "AllowAzureServices"
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  start_ip_address     = "0.0.0.0"
  end_ip_address       = "0.0.0.0"
}

output "workspace_name"   { value = azurerm_synapse_workspace.main.name }
output "workspace_id"     { value = azurerm_synapse_workspace.main.id }
output "sql_pool_name"    { value = azurerm_synapse_sql_pool.main.name }
output "managed_identity" { value = azurerm_synapse_workspace.main.identity[0].principal_id }

variable "resource_group_name" {}
variable "location"            {}
variable "project_name"        {}
variable "environment"         {}
variable "storage_account_id"  {}
variable "data_lake_filesystem"{}
variable "keyvault_id"         {}
variable "sql_admin_login"     { default = "sqladmin" }
variable "sql_admin_password"  { sensitive = true; default = "ChangeMe123!" }
variable "tags"                { default = {} }

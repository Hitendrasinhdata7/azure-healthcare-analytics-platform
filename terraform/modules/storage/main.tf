resource "azurerm_storage_account" "adls" {
  name                     = "adls${var.project_name}${var.environment}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true   # ADLS Gen2

  blob_properties {
    delete_retention_policy { days = 30 }
    versioning_enabled = true
  }

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
    ip_rules       = var.allowed_ip_ranges
  }

  tags = var.tags
}

locals {
  containers = ["bronze", "silver", "gold", "checkpoints", "monitoring", "raw"]
}

resource "azurerm_storage_data_lake_gen2_filesystem" "layers" {
  for_each           = toset(local.containers)
  name               = each.key
  storage_account_id = azurerm_storage_account.adls.id
}

output "storage_account_name" { value = azurerm_storage_account.adls.name }
output "storage_account_id"   { value = azurerm_storage_account.adls.id }
output "gold_filesystem_id"   { value = azurerm_storage_data_lake_gen2_filesystem.layers["gold"].id }

variable "resource_group_name" {}
variable "location" {}
variable "project_name" {}
variable "environment" {}
variable "allowed_ip_ranges" { default = [] }
variable "tags" { default = {} }

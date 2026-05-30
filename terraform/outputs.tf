output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "storage_account_name" {
  value = module.storage.storage_account_name
}

output "databricks_workspace_url" {
  value = module.databricks.workspace_url
}

output "synapse_workspace_name" {
  value = module.synapse.workspace_name
}

output "keyvault_uri" {
  value     = module.keyvault.keyvault_uri
  sensitive = true
}

output "log_analytics_workspace_id" {
  value = module.monitoring.log_analytics_workspace_id
}

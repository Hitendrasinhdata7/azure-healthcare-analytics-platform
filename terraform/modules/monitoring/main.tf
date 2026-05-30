resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "prod" ? 90 : 30
  tags                = var.tags
}

resource "azurerm_application_insights" "main" {
  name                = "appi-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "other"
  tags                = var.tags
}

resource "azurerm_monitor_action_group" "alerts" {
  name                = "ag-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  short_name          = "healthcare"

  email_receiver {
    name          = "DataEngineering"
    email_address = var.alert_email
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "pipeline_failure" {
  name                = "alert-pipeline-failure-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location

  evaluation_frequency = "PT15M"
  window_duration      = "PT1H"
  scopes               = [azurerm_log_analytics_workspace.main.id]
  severity             = 1

  criteria {
    query                   = <<-QUERY
      AzureActivity
      | where OperationNameValue contains "databricks"
      | where ActivityStatusValue == "Failed"
      | summarize count() by bin(TimeGenerated, 15m)
      | where count_ > 0
    QUERY
    time_aggregation_method = "Count"
    threshold               = 1
    operator                = "GreaterThanOrEqual"
  }

  action {
    action_groups = [azurerm_monitor_action_group.alerts.id]
  }

  tags = var.tags
}

output "log_analytics_workspace_id" { value = azurerm_log_analytics_workspace.main.id }
output "app_insights_key"           { value = azurerm_application_insights.main.instrumentation_key
                                      sensitive = true }

variable "resource_group_name" {}
variable "location" {}
variable "project_name" {}
variable "environment" {}
variable "alert_email" { default = "data-engineering@nhs.net" }
variable "tags" { default = {} }
